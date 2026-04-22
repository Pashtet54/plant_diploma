import requests

API_KEY = "2b10OlG70XzplADmk91bvyq6O"
URL = "https://my-api.plantnet.org/v2/identify/all"

def identify_plant_by_image(image_bytes):
    try:
        files = {
            "images": ("plant.jpg", image_bytes, "image/jpeg")
        }

        data = {
            "organs": "leaf"
        }

        params = {
            "api-key": API_KEY
        }

        response = requests.post(
            URL,
            params=params,
            data=data,
            files=files,
            timeout=15
        )
        print("STATUS:", response.status_code)
        print("HEADERS:", response.headers)
        print("TEXT:", response.text)
        print("STATUS:", response.status_code)
        print("TEXT:", response.text)

        response.raise_for_status()
        data_json = response.json()

        results = data_json.get("results", [])
        output = []

        for r in results[:3]:
            species = r.get("species", {})
            score = r.get("score", 0)

            common_names = species.get("commonNames", [])
            name = common_names[0] if common_names else "Неизвестно"
            scientific = species.get("scientificNameWithoutAuthor", "Нет данных")

            output.append({
                "name": name,
                "scientific": scientific,
                "confidence": score
            })

        return output

    except Exception as e:
        print("Ошибка PlantNet:", e)
        return []