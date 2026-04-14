import json
import os
from datetime import datetime
from typing import List, Dict, Any


FAVORITES_PATH = os.path.join(os.path.expanduser("~"), ".owlloc", "favorites.json")


def _ensure_dir():
    os.makedirs(os.path.dirname(FAVORITES_PATH), exist_ok=True)


def load() -> List[Dict[str, Any]]:
    _ensure_dir()
    if not os.path.exists(FAVORITES_PATH):
        return []
    try:
        with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_all(favorites: List[Dict[str, Any]]):
    _ensure_dir()
    with open(FAVORITES_PATH, "w", encoding="utf-8") as f:
        json.dump(favorites, f, indent=2, ensure_ascii=False)


def add(name: str, lat: float, lng: float) -> Dict[str, Any]:
    favorites = load()
    entry = {
        "name": name,
        "lat": lat,
        "lng": lng,
        "created": datetime.now().isoformat(),
    }
    favorites.append(entry)
    save_all(favorites)
    return entry


def remove(index: int):
    favorites = load()
    if 0 <= index < len(favorites):
        favorites.pop(index)
        save_all(favorites)
