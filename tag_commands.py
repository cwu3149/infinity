import logging
import json
from typing import List, Optional, Tuple, Dict, Any
from data_management import load_data, save_data

logger = logging.getLogger(__name__)

# Constants
DATA_FILE_PATH = "user_topic_map.json"

# Load data from file
def load_data() -> Dict[str, Any]:
    # Use the imported load_data function from data_management module
    from data_management import load_data as dm_load_data
    return dm_load_data()

# Save data to file
def save_data(data: Dict[str, Any]) -> bool:
    # Use the imported save_data function from data_management module
    from data_management import save_data as dm_save_data
    return dm_save_data(data)

# Get user ID from username
def get_user_id_from_username(data: Dict[str, Any], username: str) -> Optional[str]:
    # Check if username is in username_to_id mapping
    if "username_to_id" in data and username in data["username_to_id"]:
        return data["username_to_id"][username]
    
    # Otherwise search through user_mappings
    for user_id, user_data in data["user_mappings"].items():
        if user_data.get("username") == username:
            return user_id
    
    return None

# Add tag to user by username
def add_tag_by_username(username: str, tag: str) -> Tuple[bool, str]:
    if not username or not tag:
        return False, "Username and tag cannot be empty"
    
    # Remove @ from username if present
    if username.startswith("@"):
        username = username[1:]
    
    data = load_data()
    
    # Check if user exists in user_mappings
    user_id = get_user_id_from_username(data, username)
    
    if user_id:
        # User exists, add tag to their record
        if "tags" not in data["user_mappings"][user_id]:
            data["user_mappings"][user_id]["tags"] = []
        
        # Check if tag already exists
        if tag in data["user_mappings"][user_id]["tags"]:
            return False, f"Tag '{tag}' already exists for user @{username}"
        
        # Add tag
        data["user_mappings"][user_id]["tags"].append(tag)
        if save_data(data):
            return True, f"Added tag '{tag}' to user @{username}"
        else:
            return False, "Failed to save data"
    else:
        # User doesn't exist, store in username_tags
        if username not in data["username_tags"]:
            data["username_tags"][username] = []
        
        # Check if tag already exists
        if tag in data["username_tags"][username]:
            return False, f"Tag '{tag}' already exists for username @{username}"
        
        # Add tag
        data["username_tags"][username].append(tag)
        if save_data(data):
            return True, f"Added tag '{tag}' to username @{username} (user not yet in system)"
        else:
            return False, "Failed to save data"

# Remove tag from user by username
def remove_tag_by_username(username: str, tag: str) -> Tuple[bool, str]:
    if not username or not tag:
        return False, "Username and tag cannot be empty"
    
    # Remove @ from username if present
    if username.startswith("@"):
        username = username[1:]
    
    data = load_data()
    
    # Check if user exists in user_mappings
    user_id = get_user_id_from_username(data, username)
    
    if user_id and "tags" in data["user_mappings"][user_id]:
        # User exists, check if tag exists
        if tag in data["user_mappings"][user_id]["tags"]:
            # Remove tag
            data["user_mappings"][user_id]["tags"].remove(tag)
            if save_data(data):
                return True, f"Removed tag '{tag}' from user @{username}"
            else:
                return False, "Failed to save data"
        else:
            return False, f"Tag '{tag}' not found for user @{username}"
    elif username in data["username_tags"]:
        # Check username_tags
        if tag in data["username_tags"][username]:
            # Remove tag
            data["username_tags"][username].remove(tag)
            # If no tags left, remove username entry
            if not data["username_tags"][username]:
                del data["username_tags"][username]
            if save_data(data):
                return True, f"Removed tag '{tag}' from username @{username}"
            else:
                return False, "Failed to save data"
        else:
            return False, f"Tag '{tag}' not found for username @{username}"
    else:
        return False, f"No tags found for username @{username}"

# List tags for a user by username
def list_tags_by_username(username: str) -> Tuple[bool, str, List[str]]:
    if not username:
        return False, "Username cannot be empty", []
    
    # Remove @ from username if present
    if username.startswith("@"):
        username = username[1:]
    
    data = load_data()
    
    # Check if user exists in user_mappings
    user_id = get_user_id_from_username(data, username)
    
    if user_id and "tags" in data["user_mappings"][user_id]:
        # User exists, return tags
        tags = data["user_mappings"][user_id]["tags"]
        if tags:
            return True, f"Tags for user @{username}: {', '.join(tags)}", tags
        else:
            return False, f"No tags found for user @{username}", []
    elif username in data["username_tags"]:
        # Check username_tags
        tags = data["username_tags"][username]
        if tags:
            return True, f"Tags for username @{username} (user not yet in system): {', '.join(tags)}", tags
        else:
            return False, f"No tags found for username @{username}", []
    else:
        return False, f"No tags found for username @{username}", []

# Get tags for a user by user_id
def get_tags_by_user_id(user_id: int) -> List[str]:
    data = load_data()
    user_id_str = str(user_id)
    
    # Check if user exists in user_mappings
    if user_id_str in data["user_mappings"] and "tags" in data["user_mappings"][user_id_str]:
        return data["user_mappings"][user_id_str]["tags"]
    
    # Check if user has a username and if that username has tags in username_tags
    if user_id_str in data["user_mappings"] and "username" in data["user_mappings"][user_id_str]:
        username = data["user_mappings"][user_id_str]["username"]
        if username in data["username_tags"]:
            # If user has tags in username_tags, move them to user_mappings and return
            if "tags" not in data["user_mappings"][user_id_str]:
                data["user_mappings"][user_id_str]["tags"] = []
            
            # Merge tags, avoiding duplicates
            for tag in data["username_tags"][username]:
                if tag not in data["user_mappings"][user_id_str]["tags"]:
                    data["user_mappings"][user_id_str]["tags"].append(tag)
            
            # Remove from username_tags
            del data["username_tags"][username]
            save_data(data)
            
            return data["user_mappings"][user_id_str]["tags"]
    
    return []