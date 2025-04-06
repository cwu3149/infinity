import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

DATA_FILE_PATH = "user_topic_map.json"

def load_data() -> Dict[str, Any]:
    try:
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "username_tags" not in data:
                data["username_tags"] = {}
            for user_id, user_data in data["user_mappings"].items():
                if "tags" not in user_data:
                    user_data["tags"] = []
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading data file: {e}")
        return {"support_group_id": 0, "user_mappings": {}, "username_tags": {}}

def save_data(data: Dict[str, Any]) -> bool:
    try:
        with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving data file: {e}")
        return False