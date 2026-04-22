import re
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    password = password[:72]
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    password = password[:72]
    return pwd_context.verify(password, password_hash)


def validate_password(password: str):
    errors = []

    if len(password) < 8:
        errors.append("Пароль должен содержать минимум 8 символов")

    if len(password) > 72:
        errors.append("Пароль должен содержать не более 72 символов")

    if not re.search(r"[A-ZА-Я]", password):
        errors.append("Пароль должен содержать хотя бы одну заглавную букву")

    if not re.search(r"[a-zа-я]", password):
        errors.append("Пароль должен содержать хотя бы одну строчную букву")

    if not re.search(r"\d", password):
        errors.append("Пароль должен содержать хотя бы одну цифру")

    return errors


def validate_username(username: str):
    errors = []

    if len(username) < 3:
        errors.append("Логин должен содержать минимум 3 символа")

    if len(username) > 30:
        errors.append("Логин должен содержать не более 30 символов")

    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9_]+", username):
        errors.append("Логин может содержать только буквы, цифры и знак подчёркивания")

    return errors