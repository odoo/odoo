# AI Assistant Setup Guide

## Quick Start

After installing the AI Assistant module, follow these steps to configure it:

## Step 1: Configure Your OpenAI API Key

1. **Get an OpenAI API Key**
   - Go to https://platform.openai.com/api-keys
   - Sign in or create an account
   - Create a new API key
   - Copy the key (it starts with `sk-...`)

2. **Configure the AI Provider in Odoo**
   - Navigate to: **AI Assistant → Configuration → AI Providers**
   - Open the "OpenAI" provider record
   - Paste your API key in the **API Key** field
   - Set **Active** to `True`
   - Click **Save**

3. **Test the Connection**
   - Click the **Test Connection** button
   - You should see a success notification

## Step 2: Configure AI Settings (Optional)

Navigate to: **AI Assistant → Configuration → Settings**

### System Prompts
Customize how the AI behaves:
- **Default System Prompt**: The base instructions for the AI
- **Module-Specific Prompts**: Additional context for Sales, CRM, Accounting, etc.

### Features
Enable/disable AI capabilities:
- ✅ **Enable Database Search**: Recommended (allows AI to query records)
- ⚠️ **Enable Record Creation**: Use with caution (allows AI to create data)
- ⚠️ **Enable Record Updates**: Use with caution (allows AI to modify data)

### Limits
- **Max Messages in History**: How many messages to keep in context (default: 20)
- **Conversation Timeout**: Auto-close inactive conversations (default: 30 minutes)

### UI Settings
- **Welcome Message**: First message shown to users
- **Show in System Tray**: Display the robot icon (default: Yes)

## Step 3: Start Chatting!

1. Click the **🤖 robot icon** in the system tray (top right)
2. The chat window will open
3. Start typing your questions or requests

## Example API Key Configuration

If you have the API key provided by your administrator, you can configure it via SQL (for advanced users):

```sql
UPDATE ai_provider
SET api_key = 'sk-proj-YOUR-ACTUAL-KEY-HERE',
    active = TRUE
WHERE name = 'OpenAI';
```

**Important**: Replace `sk-proj-YOUR-ACTUAL-KEY-HERE` with your actual API key.

## Security Notes

- ⚠️ **Never commit API keys to git repositories**
- 🔒 Keep your API key confidential
- 👥 Only grant "AI Assistant / Manager" role to trusted users
- 🛡️ Start with search-only features before enabling write operations
- 📊 Monitor API usage on OpenAI's platform

## Troubleshooting

### "API Key is not configured"
- Ensure you've set the API key in the AI Provider
- Make sure the provider is set to **Active**

### "Connection Failed"
- Verify your API key is correct
- Check your internet connection
- Ensure the API URL is: `https://api.openai.com/v1/chat/completions`

### "Invalid API Key"
- The key may be expired or invalid
- Generate a new key from OpenAI's platform

### Chat window not appearing
- Verify the module is installed
- Check that "Show in System Tray" is enabled in settings
- Ensure your user has the "AI Assistant / User" group

## Models Supported

The following OpenAI models are supported:
- `gpt-4` (most capable, more expensive)
- `gpt-4-turbo` (faster, cost-effective)
- `gpt-3.5-turbo` (fast, economical)
- `openai/gpt-5-mini` (latest model, configured by default)

You can change the model in: **AI Assistant → Configuration → AI Providers**

## Need Help?

- Check the [README.md](README.md) for detailed documentation
- Review the inline help in configuration forms
- Contact your system administrator

---

**Ready to use AI Assistant?** Click the robot icon and start chatting! 🤖
