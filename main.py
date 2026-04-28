from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from PIL import Image
import io
import os
from uuid import uuid4
import json

from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import engine, Base, SessionLocal, get_db
from models import User, AnalysisHistory, FavoritePlant
from auth import hash_password, verify_password, validate_password, validate_username

from app.ml.predictor import predict_plant
from app.services.plantnet_service import identify_plant_by_image
from app.services.selector import select_plants
from app.services.recommendations import get_recommendations
from app.services.selector import find_similar_plants, get_all_plants_for_compare, get_plant_by_name
from app.data.plant_cards import get_plant_card, get_all_plant_cards
from app.services.pdf_report import build_pdf_report


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="plant_diploma_2026_super_secret_key_very_safe"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

templates = Jinja2Templates(directory="templates")

os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/reports", exist_ok=True)

def format_datetime(dt):
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user
    finally:
        db.close()
def get_user_favorite_names(user_id: int):
    db = SessionLocal()
    try:
        favorites = (
            db.query(FavoritePlant)
            .filter(FavoritePlant.user_id == user_id)
            .all()
        )
        return [favorite.plant_name for favorite in favorites]
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user
        }
    )


@app.get("/selection", response_class=HTMLResponse)
def selection_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(
        "selection.html",
        {
            "request": request,
            "user": user
        }
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/profile", status_code=303)

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "errors": [],
            "form_data": {
                "username": "",
                "email": ""
            }
        }
    )


@app.post("/register", response_class=HTMLResponse)
def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    db: Session = SessionLocal()

    username = username.strip()
    email = email.strip().lower()

    errors = []
    errors.extend(validate_username(username))
    errors.extend(validate_password(password))

    if password != confirm_password:
        errors.append("Пароли не совпадают")

    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        errors.append("Этот логин уже занят")

    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        errors.append("Этот email уже зарегистрирован")

    if errors:
        db.close()
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "errors": errors,
                "form_data": {
                    "username": username,
                    "email": email
                }
            }
        )

    try:
        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password)
        )

        db.add(new_user)
        db.commit()

        return RedirectResponse(url="/login", status_code=303)

    finally:
        db.close()


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/profile", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
            "form_data": {
                "login": ""
            }
        }
    )


@app.post("/login", response_class=HTMLResponse)
def login_user(
    request: Request,
    login: str = Form(...),
    password: str = Form(...)
):
    db: Session = SessionLocal()

    login = login.strip()

    try:
        user = db.query(User).filter(
            or_(User.email == login.lower(), User.username == login)
        ).first()

        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Неверный логин/email или пароль",
                    "form_data": {
                        "login": login
                    }
                }
            )

        request.session["user_id"] = user.id
        return RedirectResponse(url="/profile", status_code=303)

    finally:
        db.close()


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


from sqlalchemy import func

@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()

    try:
        analyses = db.query(AnalysisHistory).filter(
            AnalysisHistory.user_id == user.id
        ).all()

        total = len(analyses)

        successful = sum(1 for a in analyses if not a.is_unknown)
        success_percent = (successful / total * 100) if total > 0 else 0

        internet_used = sum(1 for a in analyses if a.is_unknown)

        
        top_plants_query = (
            db.query(
                AnalysisHistory.predicted_name,
                func.count(AnalysisHistory.predicted_name).label("count")
            )
            .filter(
                AnalysisHistory.user_id == user.id,
                AnalysisHistory.is_unknown == False
            )
            .group_by(AnalysisHistory.predicted_name)
            .order_by(func.count(AnalysisHistory.predicted_name).desc())
            .limit(3)
            .all()
        )

        top_plants = [
            {"name": row[0], "count": row[1]}
            for row in top_plants_query
        ]

    finally:
        db.close()

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "total": total,
            "success_percent": round(success_percent, 1),
            "internet_used": internet_used,
            "top_plants": top_plants
        }
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        history_items = (
            db.query(AnalysisHistory)
            .filter(AnalysisHistory.user_id == user.id)
            .order_by(AnalysisHistory.created_at.desc())
            .all()
        )
    finally:
        db.close()

    for item in history_items:
        item.formatted_date = format_datetime(item.created_at)

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "user": user,
            "history_items": history_items
        }
    )


@app.post("/delete-analysis/{analysis_id}")
def delete_analysis(analysis_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        item = db.query(AnalysisHistory).filter(
            AnalysisHistory.id == analysis_id,
            AnalysisHistory.user_id == user.id
        ).first()

        if item:
            if item.image_path:
                file_path = item.image_path.replace("/uploads/", "uploads/")
                if os.path.exists(file_path):
                    os.remove(file_path)

            db.delete(item)
            db.commit()

    finally:
        db.close()

    return RedirectResponse(url="/history", status_code=303)


@app.get("/download-report/{analysis_id}")
def download_report(analysis_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        item = db.query(AnalysisHistory).filter(
            AnalysisHistory.id == analysis_id,
            AnalysisHistory.user_id == user.id
        ).first()

        if not item:
            return RedirectResponse(url="/history", status_code=303)

        recommendations = None
        plant_card = None
        external_results = []

        if item.external_results_json:
            try:
                external_results = json.loads(item.external_results_json)
            except Exception:
                external_results = []

        if item.predicted_name and item.predicted_name != "Определено плохо":
            recommendations = get_recommendations(item.predicted_name)
            plant_card = get_plant_card(item.predicted_name)

        safe_name = item.predicted_name.replace(" ", "_") if item.predicted_name else "report"
        pdf_filename = f"report_{analysis_id}_{safe_name}.pdf"
        pdf_path = os.path.join("uploads", "reports", pdf_filename)

        build_pdf_report(
            output_path=pdf_path,
            analysis_item=item,
            recommendations=recommendations,
            plant_card=plant_card,
            external_results=external_results
        )

        return FileResponse(
            path=pdf_path,
            filename=pdf_filename,
            media_type="application/pdf"
        )

    finally:
        db.close()


@app.post("/analyze")
async def analyze(request: Request, file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")

    prediction = predict_plant(image)

    recommendations = None
    similar_plants = []
    external_results = []
    local_candidates = prediction.get("top_candidates", [])
    plant_card = None

    if prediction["is_unknown"]:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        external_results = identify_plant_by_image(buffer.read())
    else:
        recommendations = get_recommendations(prediction["display_name"])
        similar_plants = find_similar_plants(prediction["display_name"], top_n=3)
        plant_card = get_plant_card(prediction["display_name"])

    current_user = get_current_user(request)
    if current_user:
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        unique_filename = f"{uuid4()}.{file_extension}"
        file_path = os.path.join("uploads", unique_filename)

        with open(file_path, "wb") as buffer_file:
            buffer_file.write(contents)

        db = SessionLocal()
        try:
            history_item = AnalysisHistory(
            user_id=current_user.id,
            filename=file.filename,
            image_path=f"/uploads/{unique_filename}",
            predicted_name=prediction["display_name"] if prediction["display_name"] else "Не определено уверенно",
            confidence=prediction["confidence"],
            is_unknown=prediction["is_unknown"],
            external_results_json=json.dumps(external_results, ensure_ascii=False) if external_results else None
        )
            db.add(history_item)
            db.commit()
        finally:
            db.close()

    return {
        "filename": file.filename,
        "image_size": image.size,
        "analysis_result": prediction,
        "recommendations": recommendations,
        "similar_plants": similar_plants,
        "external_results": external_results,
        "local_candidates": local_candidates,
        "plant_card": plant_card
    }


@app.post("/select-plants")
async def select_plants_endpoint(request: Request):
    data = await request.json()

    user_data = {
        "light": data.get("light"),
        "watering": data.get("watering"),
        "humidity": data.get("humidity"),
        "pets": data.get("pets"),
        "difficulty": data.get("difficulty")
    }

    results = select_plants(user_data)

    return {
        "success": True,
        "results": results
    }
@app.get("/encyclopedia")
def encyclopedia_page(request: Request):
    user = get_current_user(request)

    plants = get_all_plant_cards()

    favorite_names = []
    if user:
        favorite_names = get_user_favorite_names(user.id)

    return templates.TemplateResponse(
        "encyclopedia.html",
        {
            "request": request,
            "user": user,
            "plants": plants,
            "favorite_names": favorite_names
        }
    )
@app.post("/favorites/add")
def add_favorite_plant(request: Request, plant_name: str = Form(...)):
    user = get_current_user(request)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()

    try:
        existing = (
            db.query(FavoritePlant)
            .filter(
                FavoritePlant.user_id == user.id,
                FavoritePlant.plant_name == plant_name
            )
            .first()
        )

        if not existing:
            favorite = FavoritePlant(
                user_id=user.id,
                plant_name=plant_name
            )
            db.add(favorite)
            db.commit()

    finally:
        db.close()

    return RedirectResponse(
        url=request.headers.get("referer", "/encyclopedia"),
        status_code=303
    )


@app.post("/favorites/remove")
def remove_favorite_plant(request: Request, plant_name: str = Form(...)):
    user = get_current_user(request)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()

    try:
        favorite = (
            db.query(FavoritePlant)
            .filter(
                FavoritePlant.user_id == user.id,
                FavoritePlant.plant_name == plant_name
            )
            .first()
        )

        if favorite:
            db.delete(favorite)
            db.commit()

    finally:
        db.close()

    return RedirectResponse(
        url=request.headers.get("referer", "/favorites"),
        status_code=303
    )


@app.get("/favorites")
def favorites_page(request: Request):
    user = get_current_user(request)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()

    try:
        favorites = (
            db.query(FavoritePlant)
            .filter(FavoritePlant.user_id == user.id)
            .order_by(FavoritePlant.created_at.desc())
            .all()
        )

        favorite_cards = []

        for favorite in favorites:
            card = get_plant_card(favorite.plant_name)

            if card:
                favorite_cards.append(card)

        return templates.TemplateResponse(
            "favorites.html",
            {
                "request": request,
                "user": user,
                "plants": favorite_cards
            }
        )

    finally:
        db.close()
@app.get("/compare")
def compare_page(request: Request, plant1: str = "", plant2: str = ""):
    user = get_current_user(request)

    plants = get_all_plants_for_compare()
    first_plant = get_plant_by_name(plant1) if plant1 else None
    second_plant = get_plant_by_name(plant2) if plant2 else None

    return templates.TemplateResponse(
        "compare.html",
        {
            "request": request,
            "user": user,
            "plants": plants,
            "plant1": plant1,
            "plant2": plant2,
            "first_plant": first_plant,
            "second_plant": second_plant,
        }
    )