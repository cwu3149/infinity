# Infinity - AI-Powered Telegram DM Bot

Contact CWWWW Through His Infinity Bot: [Click Here](t.me/CWWWWInfinity_bot)

Infinity is a Telegram bot that allows users to manage direct messages (DMs) through a support group with AI-powered auto-replies. The bot forwards messages from users to a designated support group and can automatically respond using Google's Gemini AI.

## Features

- **Message Forwarding**: Forwards private messages to a designated support group
- **Topic Management**: Creates a separate topic for each user in the support group
- **AI Auto-Replies**: Automatically responds to users with AI-generated messages
- **Conversation History**: Maintains conversation history for context-aware AI responses
- **Toggle AI Mode**: Admins can enable/disable AI auto-replies for specific users
- **User Tagging**: Support for tagging users with custom labels for better organization

## Demo
![image](https://github.com/user-attachments/assets/3aae4053-556f-4d11-a048-6450ef4a8bf7)

## Limitations

This bot is a basic implementation with several limitations:

- **No Message Editing**: The bot cannot handle edited messages
- **No Message Deletion**: The bot cannot detect or handle deleted messages
- **Limited Media Support**: While the bot can forward media, it may not process all types optimally
- **No Inline Queries**: The bot does not support inline queries
- **No Group Chat Support**: The bot is designed for private messages only
- **Limited Error Handling**: Some edge cases may not be handled gracefully

## Prerequisites

- Python 3.7+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- A Google Gemini API Key (from [Google AI Studio](https://makersuite.google.com/app/apikey))
- A Telegram group with topic mode enabled

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/infinity-bot.git
cd infinity-bot
```

### 2. Install Dependencies

```bash
pip install python-telegram-bot google-generativeai
```

### 3. Configure the Bot

Open `Infinity.py` and update the following configuration variables:

```python
# --- Configuration ---
BOT_TOKEN = "Your bot token from BotFather"
SUPPORT_GROUP_ID = -1001234567890  # Your support group ID (see step 4)
GEMINI_API_KEY = "Your Gemini API key"
YOUR_NAME = "Your Name"  # The name the AI will use

# Base prompt for the AI
GEMINI_BASE_PROMPT = f"Act as {YOUR_NAME} and Chat with the User Through the Chat History(If Have) in a Short Sentance:"
```

### 4. Get Your Support Group ID

1. Create a Telegram group where you want to receive forwarded messages
2. Add [@username_to_id_bot](https://t.me/username_to_id_bot) to your group
3. Send `/id` command in the group
4. Copy the group ID (it will be a negative number) and update `SUPPORT_GROUP_ID` in the configuration

### 5. Set Up Your Support Group

1. Make your bot an admin in the support group
2. Enable topic mode in the group settings:
   - Go to group settings > Group Type > View as Forum
3. Grant all admin permissions to your bot:
   - Change group info
   - Delete messages
   - Ban users
   - Invite users via link
   - Pin messages
   - Manage topics

### 6. Run the Bot

```bash
python Infinity.py
```

## Usage

### For Users

1. Start a conversation with your bot by sending any message
2. The bot will create a topic in your support group and forward the message
3. If AI mode is enabled, the bot will automatically reply with an AI-generated response

### For Admins

1. View and respond to user messages in the support group
2. Toggle AI auto-replies using the button under AI responses
3. Use tag commands to organize users (see tag_commands.py for available commands)

## How It Works

1. When a user sends a message to the bot, it creates a dedicated topic in the support group
2. All messages from the user are forwarded to this topic
3. If AI mode is enabled, the bot generates a response using Gemini AI and sends it to the user
4. Admins can see both the user's messages and the AI's responses in the support group
5. Admins can reply directly to the user by sending messages in their topic

## Files

- `Infinity.py`: Main bot code
- `data_management.py`: Functions for loading and saving user data
- `tag_commands.py`: Commands for tagging and organizing users
- `user_topic_map.json`: Stores user-topic mappings and settings
- `conversation_history.json`: Stores conversation history for AI context

## Customization

You can customize the AI behavior by modifying the `GEMINI_BASE_PROMPT` variable in `Infinity.py`. This prompt sets the tone and behavior of the AI responses.

## Troubleshooting

- If the bot fails to create topics, ensure it has admin permissions with "Manage Topics" enabled
- If AI responses are not working, check that your Gemini API key is valid
- If messages are not being forwarded, ensure the bot has permission to forward messages

## License

GPL

## Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Google Generative AI](https://github.com/google/generative-ai-python)
