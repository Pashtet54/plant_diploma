PLANTS_DB = [
    {
        "name": "Алоэ",
        "light": "high",
        "watering": "rare",
        "humidity": "low",
        "pets_safe": False,
        "difficulty": "easy"
    },
    {
        "name": "Фикус",
        "light": "medium",
        "watering": "moderate",
        "humidity": "medium",
        "pets_safe": False,
        "difficulty": "medium"
    },
    {
        "name": "Сансеверия",
        "light": "low",
        "watering": "rare",
        "humidity": "low",
        "pets_safe": False,
        "difficulty": "easy"
    },
    {
        "name": "Спатифиллум",
        "light": "low",
        "watering": "frequent",
        "humidity": "high",
        "pets_safe": False,
        "difficulty": "medium"
    },
    {
        "name": "Замиокулькас",
        "light": "low",
        "watering": "rare",
        "humidity": "low",
        "pets_safe": False,
        "difficulty": "easy"
    },
    {
        "name": "Папоротник",
        "light": "low",
        "watering": "frequent",
        "humidity": "high",
        "pets_safe": True,
        "difficulty": "hard"
    },
    {
        "name": "Орхидея",
        "light": "medium",
        "watering": "moderate",
        "humidity": "high",
        "pets_safe": True,
        "difficulty": "hard"
    },
    {
        "name": "Плющ",
        "light": "medium",
        "watering": "moderate",
        "humidity": "medium",
        "pets_safe": False,
        "difficulty": "medium"
    },
    {
        "name": "Монстера",
        "light": "medium",
        "watering": "moderate",
        "humidity": "high",
        "pets_safe": False,
        "difficulty": "medium"
    },
    {
        "name": "Диффенбахия",
        "light": "medium",
        "watering": "moderate",
        "humidity": "high",
        "pets_safe": False,
        "difficulty": "medium"
    },
    {
        "name": "Калатея",
        "light": "low",
        "watering": "frequent",
        "humidity": "high",
        "pets_safe": True,
        "difficulty": "hard"
    },
    {
        "name": "Маранта",
        "light": "low",
        "watering": "frequent",
        "humidity": "high",
        "pets_safe": True,
        "difficulty": "medium"
    },
    {
        "name": "Арековая пальма",
        "light": "medium",
        "watering": "moderate",
        "humidity": "high",
        "pets_safe": True,
        "difficulty": "medium"
    },
    {
        "name": "Бегония",
        "light": "medium",
        "watering": "moderate",
        "humidity": "medium",
        "pets_safe": False,
        "difficulty": "medium"
    }
]


def calculate_score(plant, user_data):
    score = 0

    if plant["light"] == user_data["light"]:
        score += 3

    if plant["watering"] == user_data["watering"]:
        score += 3

    if plant["humidity"] == user_data["humidity"]:
        score += 2

    if user_data["pets"] and plant["pets_safe"]:
        score += 2
    elif not user_data["pets"]:
        score += 1

    if plant["difficulty"] == user_data["difficulty"]:
        score += 2

    return score


def select_plants(user_data, top_n=5):
    scored_plants = []

    for plant in PLANTS_DB:
        score = calculate_score(plant, user_data)
        scored_plants.append({
            "name": plant["name"],
            "score": score,
            "light": plant["light"],
            "watering": plant["watering"],
            "humidity": plant["humidity"],
            "pets_safe": plant["pets_safe"],
            "difficulty": plant["difficulty"]
        })

    scored_plants.sort(key=lambda x: x["score"], reverse=True)
    return scored_plants[:top_n]


def get_plant_by_name(plant_name: str):
    for plant in PLANTS_DB:
        if plant["name"].strip().lower() == plant_name.strip().lower():
            return plant
    return None


def calculate_similarity_score(base_plant, candidate_plant):
    score = 0

    if base_plant["light"] == candidate_plant["light"]:
        score += 3

    if base_plant["watering"] == candidate_plant["watering"]:
        score += 3

    if base_plant["humidity"] == candidate_plant["humidity"]:
        score += 2

    if base_plant["difficulty"] == candidate_plant["difficulty"]:
        score += 2

    if base_plant["pets_safe"] == candidate_plant["pets_safe"]:
        score += 1

    return score


def find_similar_plants(plant_name: str, top_n=3):
    base_plant = get_plant_by_name(plant_name)

    if not base_plant:
        return []

    similar = []

    for plant in PLANTS_DB:
        if plant["name"].strip().lower() == plant_name.strip().lower():
            continue

        score = calculate_similarity_score(base_plant, plant)

        similar.append({
            "name": plant["name"],
            "score": score,
            "light": plant["light"],
            "watering": plant["watering"],
            "humidity": plant["humidity"],
            "pets_safe": plant["pets_safe"],
            "difficulty": plant["difficulty"]
        })

    similar.sort(key=lambda x: x["score"], reverse=True)
    return similar[:top_n]