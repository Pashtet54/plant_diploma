import os
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)


def register_fonts():
    regular_candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    bold_candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]

    regular_font = None
    bold_font = None

    for path in regular_candidates:
        if os.path.exists(path):
            regular_font = path
            break

    for path in bold_candidates:
        if os.path.exists(path):
            bold_font = path
            break

    if regular_font:
        pdfmetrics.registerFont(TTFont("AppFont", regular_font))
    if bold_font:
        pdfmetrics.registerFont(TTFont("AppFontBold", bold_font))

    return "AppFont" if regular_font else "Helvetica", "AppFontBold" if bold_font else "Helvetica-Bold"


def bullet_list(items, style):
    return ListFlowable(
        [ListItem(Paragraph(str(item), style)) for item in items],
        bulletType="bullet",
        leftIndent=10,
    )


def build_pdf_report(output_path: str, analysis_item, recommendations=None, plant_card=None, external_results=None):
    font_name, bold_font_name = register_fonts()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName=bold_font_name,
        fontSize=16,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#166534"),
        spaceAfter=4,
    )

    section_style = ParagraphStyle(
        "SectionCustom",
        parent=styles["Heading2"],
        fontName=bold_font_name,
        fontSize=11,
        leading=13,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#166534"),
        spaceBefore=4,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8.7,
        leading=10.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=2,
    )

    small_style = ParagraphStyle(
        "SmallCustom",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8,
        leading=9.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=2,
    )

    story = []

    story.append(Paragraph("Отчёт по анализу растения", title_style))
    story.append(Paragraph("Сформировано автоматически на основе сохранённого анализа.", small_style))
    story.append(Spacer(1, 4))

    status_text = "Не определено уверенно" if analysis_item.is_unknown else "Определено"
    confidence_text = (
        f"{analysis_item.confidence * 100:.1f}%"
        if analysis_item.confidence is not None
        else "-"
    )
    date_text = (
        analysis_item.created_at.strftime("%Y-%m-%d %H:%M:%S")
        if analysis_item.created_at
        else "-"
    )

    if getattr(analysis_item, "image_path", None):
        original_image_path = analysis_item.image_path.replace("/uploads/", "uploads/")
        if os.path.exists(original_image_path):
            try:
                img = Image(original_image_path)
                img._restrictSize(60 * mm, 45 * mm)
                story.append(img)
                story.append(Spacer(1, 5))
            except Exception:
                pass

    info_data = [
        ["Результат анализа", analysis_item.predicted_name or "-"],
        ["Уверенность", confidence_text],
        ["Статус", status_text],
        ["Дата анализа", date_text],
    ]

    info_table = Table(info_data, colWidths=[48 * mm, 120 * mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2937")),
        ("FONTNAME", (0, 0), (0, -1), bold_font_name),
        ("FONTNAME", (1, 0), (1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5))

    story.append(Paragraph("Рекомендации по уходу", section_style))
    if recommendations:
        rec_data = [
            ["Полив", recommendations.get("watering", "-")],
            ["Освещение", recommendations.get("light", "-")],
            ["Влажность", recommendations.get("humidity", "-")],
            ["Температура", recommendations.get("temperature", "-")],
        ]

        rec_table = Table(rec_data, colWidths=[48 * mm, 120 * mm])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2937")),
            ("FONTNAME", (0, 0), (0, -1), bold_font_name),
            ("FONTNAME", (1, 0), (1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 8.3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(rec_table)

        tips = recommendations.get("tips", [])
        if tips:
            story.append(Spacer(1, 3))
            story.append(Paragraph("Советы:", body_style))
            story.append(bullet_list(tips[:3], body_style))
    else:
        story.append(Paragraph("Для данного анализа рекомендации недоступны.", body_style))

    story.append(Spacer(1, 5))

    story.append(Paragraph("Карточка растения", section_style))
    if plant_card:
        if plant_card.get("title"):
            story.append(Paragraph(f"<b>{plant_card['title']}</b>", body_style))

        if plant_card.get("description"):
            story.append(Paragraph(plant_card["description"], body_style))

        care_items = plant_card.get("care", [])
        if care_items:
            story.append(Paragraph("Особенности ухода:", body_style))
            story.append(bullet_list(care_items[:3], body_style))

        fact_items = plant_card.get("facts", [])
        if fact_items:
            story.append(Paragraph("Интересные факты:", body_style))
            story.append(bullet_list(fact_items[:3], body_style))
    else:
        story.append(Paragraph("Подробная карточка для этого растения недоступна.", body_style))

    if analysis_item.is_unknown:
        story.append(Spacer(1, 5))
        story.append(Paragraph("Возможные варианты из поиска в интернете", section_style))

        if external_results and len(external_results) > 0:
            for item in external_results[:3]:
                name = item.get("name", "Неизвестно")
                scientific = item.get("scientific", "Нет данных")
                confidence = item.get("confidence", 0)

                story.append(Paragraph(
                    f"<b>{name}</b> — уверенность {confidence * 100:.1f}%",
                    body_style
                ))
                story.append(Paragraph(
                    f"Научное название: {scientific}",
                    small_style
                ))
        else:
            story.append(Paragraph(
                "Варианты из Plant API для этого анализа недоступны.",
                body_style
            ))

    doc.build(story)