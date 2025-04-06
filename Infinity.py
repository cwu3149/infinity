import logging
import json
import os
import asyncio
from typing import Dict, Optional, Any, List

# Telegram Imports
from telegram import (
    Update, ForumTopic, Message, User, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ApplicationBuilder,
    CallbackQueryHandler,
)
from telegram.constants import ChatAction, ParseMode, ChatType
from telegram.error import TelegramError, BadRequest

from google import genai
from data_management import load_data, save_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_FILE_PATH = "user_topic_map.json"
CONVERSATION_HISTORY_FILE_PATH = "conversation_history.json"

# --- Configuration ---
BOT_TOKEN = "Please Fill it with your bot token"
SUPPORT_GROUP_ID = -1234567890
GEMINI_API_KEY = "Please Fill it with your Gemini API key"
YOUR_NAME = "Please Fill it with your Name"

AI_MODEL_NAME = "gemini-2.0-flash-thinking-exp-01-21"

# Base prompt for the AI
# Please change it to your own base prompt
GEMINI_BASE_PROMPT = f"Act as {YOUR_NAME} and Chat with the User Through the Chat History(If Have) in a Short Sentance:"
_user_topic_map = {"support_group_id": SUPPORT_GROUP_ID, "user_mappings": {}}
_user_conversation_history = {}

logger.info(f"Gemini API key provided: {'Yes' if GEMINI_API_KEY else 'No'}")

def load_data() -> None:
    global _user_topic_map
    try:
        if os.path.exists(DATA_FILE_PATH):
            with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "user_mappings" in data and isinstance(data["user_mappings"], dict):
                    _user_topic_map = data
                    if _user_topic_map.get("support_group_id") != SUPPORT_GROUP_ID:
                        logger.warning(
                            f"Support group ID in {DATA_FILE_PATH} ({_user_topic_map.get('support_group_id')}) "
                            f"differs from config ({SUPPORT_GROUP_ID}). Using config value."
                        )
                        _user_topic_map["support_group_id"] = SUPPORT_GROUP_ID
                    needs_save = False
                    for user_id, user_data in _user_topic_map["user_mappings"].items():
                        if "ai_mode_enabled" not in user_data:
                            logger.info(f"Adding missing 'ai_mode_enabled' (defaulting to True) for user {user_id}")
                            user_data["ai_mode_enabled"] = True
                            needs_save = True
                    logger.info(f"Successfully loaded data from {DATA_FILE_PATH}")
                    if needs_save:
                        save_data()
                else:
                    logger.warning(f"Invalid format in {DATA_FILE_PATH}. Starting with empty map.")
                    _user_topic_map = {"support_group_id": SUPPORT_GROUP_ID, "user_mappings": {}}
        else:
            logger.info(f"{DATA_FILE_PATH} not found. Starting with empty map.")
            _user_topic_map = {"support_group_id": SUPPORT_GROUP_ID, "user_mappings": {}}
    except json.JSONDecodeError:
        logger.exception(f"Error decoding JSON from {DATA_FILE_PATH}. Starting with empty map.")
        _user_topic_map = {"support_group_id": SUPPORT_GROUP_ID, "user_mappings": {}}
    except Exception:
        logger.exception(f"Failed to load data from {DATA_FILE_PATH}. Starting with empty map.")
        _user_topic_map = {"support_group_id": SUPPORT_GROUP_ID, "user_mappings": {}}

    def initialize_conversation_history():
        load_conversation_history()

    initialize_conversation_history()


def save_data() -> None:
    global _user_topic_map
    try:
        parent_dir = os.path.dirname(DATA_FILE_PATH)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        temp_file_path = DATA_FILE_PATH + ".tmp"
        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(_user_topic_map, f, ensure_ascii=False, indent=4)
        os.replace(temp_file_path, DATA_FILE_PATH)
    except IOError:
        logger.exception(f"Error: Could not write data to {DATA_FILE_PATH}")
    except Exception:
        logger.exception(f"An unexpected error occurred while saving data to {DATA_FILE_PATH}")

def load_conversation_history() -> None:
    """Load conversation history from JSON file"""
    global _user_conversation_history
    try:
        if os.path.exists(CONVERSATION_HISTORY_FILE_PATH):
            with open(CONVERSATION_HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _user_conversation_history = data
                    logger.info(f"Successfully loaded conversation history from {CONVERSATION_HISTORY_FILE_PATH}")
                else:
                    logger.warning(f"Invalid format in {CONVERSATION_HISTORY_FILE_PATH}. Starting with empty history.")
                    _user_conversation_history = {}
        else:
            logger.info(f"{CONVERSATION_HISTORY_FILE_PATH} not found. Starting with empty history.")
            _user_conversation_history = {}
    except json.JSONDecodeError:
        logger.exception(f"Error decoding JSON from {CONVERSATION_HISTORY_FILE_PATH}. Starting with empty history.")
        _user_conversation_history = {}
    except Exception:
        logger.exception(f"Failed to load conversation history from {CONVERSATION_HISTORY_FILE_PATH}. Starting with empty history.")
        _user_conversation_history = {}

def save_conversation_history() -> None:
    """Save conversation history to JSON file"""
    global _user_conversation_history
    try:
        parent_dir = os.path.dirname(CONVERSATION_HISTORY_FILE_PATH)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        temp_file_path = CONVERSATION_HISTORY_FILE_PATH + ".tmp"
        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(_user_conversation_history, f, ensure_ascii=False, indent=4)
        os.replace(temp_file_path, CONVERSATION_HISTORY_FILE_PATH)
        logger.info(f"Successfully saved conversation history to {CONVERSATION_HISTORY_FILE_PATH}")
    except IOError:
        logger.exception(f"Error: Could not write conversation history to {CONVERSATION_HISTORY_FILE_PATH}")
    except Exception:
        logger.exception(f"An unexpected error occurred while saving conversation history to {CONVERSATION_HISTORY_FILE_PATH}")

def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
    return _user_topic_map["user_mappings"].get(str(user_id))

def get_user_topic_id(user_id: int) -> Optional[int]:
    user_data = get_user_data(user_id)
    return user_data.get("topic_id") if user_data else None

def get_user_id_from_topic(topic_id: int) -> Optional[int]:
    for user_id_str, data in _user_topic_map["user_mappings"].items():
        if data.get("topic_id") == topic_id:
            try:
                return int(user_id_str)
            except ValueError:
                logger.warning(f"Found non-integer user_id '{user_id_str}' in map for topic {topic_id}")
                return None
    return None

def create_topic_title(user: User) -> str:
    title = f"User: {user.first_name}"
    if user.last_name:
        title += f" {user.last_name}"
    if user.username:
        title += f" (@{user.username})"
    else:
        title += f" (ID:{user.id})"
    return title[:120]

def get_conversation_history(user_id: int, max_messages: int = 10) -> List[Dict[str, str]]:
    """Get the conversation history for a user, limited to the last N messages"""
    if str(user_id) not in _user_conversation_history:
        _user_conversation_history[str(user_id)] = []
    return _user_conversation_history[str(user_id)][-max_messages:]

def add_to_conversation_history(user_id: int, role: str, message: str) -> None:
    """Add a message to the user's conversation history and save to file"""
    if str(user_id) not in _user_conversation_history:
        _user_conversation_history[str(user_id)] = []
    
    if len(_user_conversation_history[str(user_id)]) >= 20:
        _user_conversation_history[str(user_id)].pop(0)
    
    _user_conversation_history[str(user_id)].append({"role": role, "message": message})
    
    save_conversation_history()

def is_ai_mode_enabled(user_id: int) -> bool:
    user_data = get_user_data(user_id)
    return user_data.get("ai_mode_enabled", True) if user_data else True

def set_ai_mode(user_id: int, enabled: bool) -> bool:
    user_id_str = str(user_id)
    if user_id_str in _user_topic_map["user_mappings"]:
        if _user_topic_map["user_mappings"][user_id_str].get("ai_mode_enabled") != enabled:
            _user_topic_map["user_mappings"][user_id_str]["ai_mode_enabled"] = enabled
            save_data()
            logger.info(f"AIMode for user {user_id} set to {enabled}")
            return True
        else:
            logger.info(f"AIMode for user {user_id} already set to {enabled}. No change.")
            return True
    else:
        logger.warning(f"Attempted to set AIMode for unknown user {user_id}")
        return False

def get_aimode_toggle_keyboard(user_id: int, current_state: bool) -> InlineKeyboardMarkup:
    button_text = "🔴 Disable AI Auto-Reply" if current_state else "🟢 Enable AI Auto-Reply"
    callback_action = "disable" if current_state else "enable"
    callback_data = f"aimode_toggle_{user_id}_{callback_action}"
    keyboard = [[InlineKeyboardButton(button_text, callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

def escape_markdown_v2(text: str) -> str:
    """Escape MarkdownV2 reserved characters: _ * [ ] ( ) ~ ` > # + - = | { } . !"""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text

def format_conversation_history(history: list) -> str:
    """Format conversation history for Gemini context"""
    formatted = "Previous conversation:\n"
    for entry in history:
        role_name = "User" if entry["role"] == "user" else YOUR_NAME
        formatted += f"{role_name}: {entry['message']}\n"
    return formatted

async def generate_ai_reply(user_message_text: str, user_id: int) -> Optional[str]:
    """Generate an AI reply using Gemini with conversation context"""
    if not GEMINI_API_KEY:
        logger.warning(f"Skipping AI reply for user {user_id}: Gemini API key not configured.")
        return None

    if not is_ai_mode_enabled(user_id):
        logger.info(f"Skipping AI reply for user {user_id}: AIMode is disabled.")
        return None

    if not user_message_text:
        logger.info(f"Skipping AI reply for user {user_id}: No text content in message.")
        return None

    logger.info(f"Attempting to generate AI reply for user {user_id} using {AI_MODEL_NAME}")
    
    history = get_conversation_history(user_id)
    
    add_to_conversation_history(user_id, "user", user_message_text)
    
    from tag_commands import get_tags_by_user_id
    user_data = get_user_data(user_id)
    user_tags = get_tags_by_user_id(user_id)
    
    user_info = ""
    if user_data:
        username = user_data.get("username", "")
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        
        display_name = first_name
        if last_name:
            display_name += f" {last_name}"
            
        user_info = f"User Information:\nUsername: @{username}\nDisplay Name: {display_name}"
        
        if user_tags:
            user_info += f"\nTags: {', '.join(user_tags)}"
    
    # Create prompt with context
    context = format_conversation_history(history) if history else ""
    full_prompt = f"{GEMINI_BASE_PROMPT}\n\n{user_info}\n\n{context}\n\nCurrent message: \"{user_message_text}\""

    try:
        loop = asyncio.get_running_loop()
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(model=AI_MODEL_NAME, contents=full_prompt)
        )
        if not response or not getattr(response, "text", None):
            logger.warning(f"LLM returned no text for user {user_id}. Prompt may have been blocked.")
            return "Infinity encountered an issue while processing your message. Please try again in a moment. CWWWW will be back online soon to reply you."
        
        ai_text = response.text
        logger.info(f"Successfully generated AI reply for user {user_id}")
        
        # Add AI response to conversation history
        add_to_conversation_history(user_id, YOUR_NAME, ai_text)
        
        return ai_text.strip()
    except Exception as e:
        logger.error(f"Error generating AI reply for user {user_id}: {e}", exc_info=True)
        return "Infinity encountered an issue while processing your message. Please try again in a moment. CWWWW will be back online soon to reply you."


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user and update.effective_user.id == context.bot.id:
        logger.debug("Ignoring message from bot itself in private chat.")
        return

    if not update.message or not update.effective_user or not update.effective_chat:
        logger.warning("Received update without message, user, or chat in private handler.")
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id_str = str(user.id)
    message = update.message
    message_text = message.text or message.caption or ""

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    topic_id = get_user_topic_id(user.id)
    is_new_user = False

    if not topic_id:
        logger.info(f"Received first message from new user {user.id} ({user.first_name} @{user.username}). Creating topic.")
        topic_title = create_topic_title(user)
        try:
            created_topic = await context.bot.create_forum_topic(
                chat_id=SUPPORT_GROUP_ID, name=topic_title
            )
            topic_id = created_topic.message_thread_id
            is_new_user = True
            logger.info(f"Created topic {topic_id} ('{topic_title}') for user {user.id}")

            _user_topic_map["user_mappings"][user_id_str] = {
                "topic_id": topic_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "ai_mode_enabled": True
            }
            save_data()

            await context.bot.forward_message(
                chat_id=SUPPORT_GROUP_ID,
                from_chat_id=chat_id,
                message_id=message.message_id,
                message_thread_id=topic_id,
            )
            logger.info(f"Forwarded first message from user {user.id} to new topic {topic_id}")

            if message_text == '/start':
                await update.message.reply_text("Hi @{user.username}! I\'m CW. This is my private messageing bot. It is based on AI. I will soon to check and reply your message.```\n\n✨ Infinity is Taking Over```\nHello! I'm Infinity.",
                parse_mode=ParseMode.MARKDOWN
            )

        except TelegramError as e:
            logger.error(f"Failed to create topic or forward first message for user {user.id}: {e}")
            try:
                await update.message.reply_text(
                    "Sorry, there was an error setting up your chat. Please try sending your message again."
                )
            except Exception as inner_e:
                logger.error(f"Failed to notify user {user.id} about topic creation error: {inner_e}")
            return
        except Exception as e:
            logger.exception(f"Unexpected error handling new user {user.id}")
            try:
                await update.message.reply_text("An unexpected error occurred. Please try sending your message again.")
            except Exception as inner_e:
                logger.error(f"Failed to notify user {user.id} about unexpected new user error: {inner_e}")
            return
    else:
        logger.info(f"Relaying message from known user {user.id} to topic {topic_id}")
        try:
            await context.bot.forward_message(
                chat_id=SUPPORT_GROUP_ID,
                from_chat_id=chat_id,
                message_id=message.message_id,
                message_thread_id=topic_id,
            )
        except TelegramError as e:
            logger.error(f"Failed to forward message from user {user.id} to topic {topic_id}: {e}")
            try:
                await update.message.reply_text(
                    "Sorry, there was an error processing your message. Please try again."
                )
            except Exception as inner_e:
                logger.error(f"Failed to notify user {user.id} about forwarding error: {inner_e}")
            return
        except Exception as e:
            logger.exception(f"Unexpected error forwarding message for user {user.id}")
            try:
                await update.message.reply_text("An unexpected error occurred. Please try again.")
            except Exception as inner_e:
                logger.error(f"Failed to notify user {user.id} about unexpected forwarding error: {inner_e}")
            return

    if topic_id and is_ai_mode_enabled(user.id):
        ai_reply_text = await generate_ai_reply(message_text, user.id)
        if ai_reply_text:
            try:
                ai_message_to_user = await context.bot.send_message(
                    chat_id=chat_id,
                    text="```\n✨ Infinity is Taking Over```\n" + ai_reply_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Sent AI reply to user {user.id}")

                current_ai_state = True
                keyboard = get_aimode_toggle_keyboard(user.id, current_ai_state)
                base_text = "🤖 *AI Response:*\n---\n" + ai_reply_text + "\n---"
                escaped_text = escape_markdown_v2(base_text)
                await context.bot.send_message(
                    chat_id=SUPPORT_GROUP_ID,
                    message_thread_id=topic_id,
                    text=escaped_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                logger.info(f"Sent AI reply copy and controls to topic {topic_id}")
            except TelegramError as e:
                logger.error(f"Error sending AI reply or copy for user {user.id} / topic {topic_id}: {e}")
                try:
                    escaped_error = escape_markdown_v2(str(e))
                    await context.bot.send_message(
                        chat_id=SUPPORT_GROUP_ID,
                        message_thread_id=topic_id,
                        text=f"⚠️ Error sending AI reply to user {user.id} or posting copy here.\n`{escaped_error}`",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.exception(f"Unexpected error sending AI reply/copy for user {user.id} / topic {topic_id}")
    elif topic_id and not is_ai_mode_enabled(user.id):
        logger.info(f"AI Mode is disabled for user {user.id}, not generating AI reply.")

async def handle_topic_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (not update.message or not update.message.is_topic_message or not update.message.message_thread_id
        or not update.effective_chat or update.effective_chat.id != SUPPORT_GROUP_ID
        or not update.effective_user):
        return

    if update.effective_user.id == context.bot.id:
        return

    if (update.message.reply_to_message and
        update.message.reply_to_message.from_user.id == context.bot.id and
        update.message.reply_to_message.reply_markup is not None and
        "AI Response" in update.message.reply_to_message.text):
        logger.info(f"Ignoring admin reply in topic {update.message.message_thread_id} as it's a reply to the bot's AI control message.")
        return

    topic_id = update.message.message_thread_id
    message = update.message
    admin_user = update.effective_user

    logger.info(f"Received manual reply in topic {topic_id} from admin {admin_user.id}")

    target_user_id = get_user_id_from_topic(topic_id)
    if target_user_id:
        logger.info(f"Relaying manual reply from topic {topic_id} to user {target_user_id}")
        
        message_text = message.text or message.caption or ""
        if message_text:
            add_to_conversation_history(target_user_id, YOUR_NAME, message_text)
            
        try:
            await context.bot.forward_message(
                chat_id=target_user_id,
                from_chat_id=SUPPORT_GROUP_ID,
                message_id=message.message_id,
            )
        except TelegramError as e:
            logger.error(f"Failed to forward manual reply from topic {topic_id} to user {target_user_id}: {e}")
            try:
                escaped_error = escape_markdown_v2(str(e))
                await message.reply_text(
                    f"⚠️ Error: Could not forward message to user `{target_user_id}`. Reason: `{escaped_error}`",
                    quote=True,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception:
                pass
        except Exception as e:
            logger.exception(f"Unexpected error forwarding manual reply from topic {topic_id} to user {target_user_id}")
            try:
                await message.reply_text(
                    f"⚠️ Unexpected Error forwarding message to user `{target_user_id}`.",
                    quote=True,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception:
                pass
    else:
        logger.warning(f"Received manual reply in topic {topic_id}, but no user found associated with this topic.")

async def handle_aimode_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not query.message:
        logger.warning("Received callback query without data or message.")
        if query:
            await query.answer("Error processing request.")
        return

    try:
        await query.answer()
    except BadRequest as e:
        logger.warning(f"Failed to answer callback query (likely message too old or double click): {e}")
        return
    except Exception as e:
        logger.error(f"Error answering callback query: {e}", exc_info=True)

    try:
        parts = query.data.split("_")
        if len(parts) != 4 or parts[0] != "aimode" or parts[1] != "toggle":
            logger.error(f"Invalid callback data format: {query.data}")
            await query.answer("Error: Invalid button data.")
            return
        user_id = int(parts[2])
        action = parts[3]
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing callback data '{query.data}': {e}")
        await query.answer("Error: Could not parse button data.")
        return

    new_state = True if action == "enable" else False if action == "disable" else None
    if new_state is None:
        logger.error(f"Unknown action in callback data: {action}")
        await query.answer("Error: Unknown action.")
        return

    success = set_ai_mode(user_id, new_state)
    if success:
        logger.info(f"AIMode for user {user_id} toggled to {new_state} via button by {query.from_user.id}.")
        try:
            new_keyboard = get_aimode_toggle_keyboard(user_id, new_state)
            await query.edit_message_reply_markup(reply_markup=new_keyboard)
        except TelegramError as e:
            if "Message is not modified" in str(e):
                logger.warning(f"Message not modified when updating AIMode button for user {user_id} (state: {new_state}). Already in desired state?")
                await query.answer(f"AI Mode already {'Enabled' if new_state else 'Disabled'}")
            else:
                logger.error(f"Failed to edit message reply markup for user {user_id} after toggle: {e}")
                await query.answer("Error updating button state.")
        except Exception as e:
            logger.exception(f"Unexpected error editing message reply markup for user {user_id} after toggle.")
            await query.answer("Unexpected error updating button.")
    else:
        logger.error(f"Failed to update AIMode state for user {user_id} via button (user might not exist in map).")
        await query.answer("Error: Could not update AI mode status.")

async def handle_tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tag commands for adding, removing, and listing tags for users"""
    if not update.effective_chat or update.effective_chat.id != SUPPORT_GROUP_ID:
        logger.warning(f"Tag command attempted outside support group by {update.effective_user.id if update.effective_user else 'unknown'}")
        return
    
    if not update.effective_user:
        logger.warning("Tag command received without user information")
        return
    
    if not update.message or not update.message.text:
        logger.warning("Tag command received without message text")
        return
    
    args = update.message.text.split()
    if len(args) < 2:
        await update.message.reply_text("Usage:\n/tag add username tag\n/tag remove username tag\n/tag list username")
        return
    
    action = args[1].lower()
    
    from tag_commands import add_tag_by_username, remove_tag_by_username, list_tags_by_username
    
    if action == "add" and len(args) >= 4:
        username = args[2]
        tag = args[3]
        success, message = add_tag_by_username(username, tag)
        await update.message.reply_text(message)
    
    elif action == "remove" and len(args) >= 4:
        username = args[2]
        tag = args[3]
        success, message = remove_tag_by_username(username, tag)
        await update.message.reply_text(message)
    
    elif action == "list" and len(args) >= 3:
        username = args[2]
        success, message, _ = list_tags_by_username(username)
        await update.message.reply_text(message)
    
    else:
        await update.message.reply_text("Usage:\n/tag add username tag\n/tag remove username tag\n/tag list username")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

async def post_init(application: Application) -> None:
    try:
        bot_user = await application.bot.get_me()
        logger.info(f"Bot started: {bot_user.first_name} (@{bot_user.username} ID: {bot_user.id})")
        application.bot_data["bot_id"] = bot_user.id
        try:
            chat_member = await application.bot.get_chat_member(SUPPORT_GROUP_ID, bot_user.id)
            if chat_member.status not in ['administrator', 'member']:
                logger.error(f"Bot is not a member or admin in the support group {SUPPORT_GROUP_ID}. Status: {chat_member.status}")
            else:
                logger.info(f"Bot is '{chat_member.status}' in support group {SUPPORT_GROUP_ID}.")
        except TelegramError as e:
            logger.error(f"Could not verify bot status in support group {SUPPORT_GROUP_ID}: {e}")
    except Exception as e:
        logger.exception("Error during post_init get_me or group check.")
    if not GEMINI_API_KEY:
        logger.warning("Reminder: API key is missing or invalid. AI features are disabled.")

def main() -> None:
    load_data()
    builder = ApplicationBuilder().token(BOT_TOKEN)
    application = builder.post_init(post_init).build()

    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (~filters.COMMAND),
        handle_private_message
    ))
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=SUPPORT_GROUP_ID) & filters.UpdateType.MESSAGE & filters.IS_TOPIC_MESSAGE,
        handle_topic_reply
    ))
    application.add_handler(CallbackQueryHandler(
        handle_aimode_toggle,
        pattern=r"^aimode_toggle_"
    ))
    application.add_handler(CommandHandler(
        "tag",
        handle_tag_command,
        filters=filters.Chat(chat_id=SUPPORT_GROUP_ID)
    ))
    async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command for initializing user interaction"""
        user = update.effective_user
        if not user:
            logger.warning("Start command received without user information")
            return
    
        await update.message.reply_text(
            f"Hi {user.first_name}! What is on your mind? I will forward your message to the Admin.",
            parse_mode=ParseMode.MARKDOWN
        )
    

    application.add_handler(CommandHandler("start", handle_start_command))
    application.add_error_handler(error_handler)
    logger.info("Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()