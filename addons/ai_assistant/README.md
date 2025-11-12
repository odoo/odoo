# AI Assistant for Odoo

🤖 An intelligent conversational AI assistant integrated with OpenAI's GPT models for Odoo ERP.

## Features

### 💬 Conversational Interface
- **System Tray Integration**: Click the robot icon in the system tray to open the chat window
- **Real-time Chat**: Instant messaging with the AI assistant
- **Beautiful UI**: Modern, responsive chat interface with smooth animations
- **Conversation History**: All conversations are automatically saved

### 🎯 Context-Aware Intelligence
- **Module Detection**: Automatically detects which Odoo module you're working in
- **Contextual Prompts**: Different system prompts for Sales, CRM, Accounting, Inventory, etc.
- **Record Context**: Knows which record you're viewing for targeted assistance

### 🔍 Database Operations
- **Smart Search**: Ask the AI to find records using natural language
- **Record Creation**: Create new records through conversation (when enabled)
- **Record Updates**: Modify existing data via AI (when enabled)
- **Model Information**: Get details about Odoo models and their fields

### ⚙️ Fully Configurable
- **Custom System Prompts**: Define how the AI should behave
- **Module-Specific Prompts**: Customize AI behavior per module
- **Feature Toggles**: Enable/disable database operations
- **Provider Settings**: Configure API keys, models, temperature, etc.

## Installation

1. Copy the `ai_assistant` folder to your Odoo addons directory
2. Update the addons list: `odoo-bin -u all -d your_database`
3. Install the module from Apps menu

## Configuration

### 1. Configure AI Provider

Navigate to: **AI Assistant → Configuration → AI Providers**

Required settings:
- **API Key**: Your OpenAI API key (get one from https://platform.openai.com)
- **Model Name**: e.g., `openai/gpt-5-mini`, `gpt-4`, `gpt-3.5-turbo`
- **Temperature**: 0.0 (focused) to 2.0 (creative), default 0.7
- **Max Tokens**: Maximum response length, default 2000

Click **Test Connection** to verify your setup.

### 2. Configure AI Settings

Navigate to: **AI Assistant → Configuration → Settings**

**System Prompts**:
- Default system prompt (applies to all conversations)
- Module-specific prompts (Sales, CRM, Accounting, Inventory)

**Features**:
- ✅ **Enable Database Search**: Allow AI to search records
- ⚠️ **Enable Record Creation**: Allow AI to create records (use with caution)
- ⚠️ **Enable Record Updates**: Allow AI to update records (use with caution)

**Limits**:
- Max messages in conversation history
- Conversation auto-close timeout

**UI Settings**:
- Welcome message
- Show in system tray

## Usage

### Starting a Conversation

1. Click the 🤖 robot icon in the system tray
2. The chat window opens with a welcome message
3. Type your question or request
4. Press Enter or click the send button

### Example Queries

**Search for data**:
- "Find all sales orders from last month"
- "Show me customers from California"
- "List my open opportunities"

**Get information**:
- "What fields does the sale.order model have?"
- "Explain the invoice validation process"
- "How do I create a new quotation?"

**Create records** (if enabled):
- "Create a new contact for John Doe at ABC Corp"
- "Add a new product called 'Widget X' priced at $99"

**Context-specific**:
- While viewing a customer: "What are this customer's recent orders?"
- While in Sales: "Show my sales target for this quarter"

### Managing Conversations

- **View All**: Click the list icon in the chat header
- **Close**: Click the X button
- **Minimize**: Click the minimize button
- **New Conversation**: Close current and click robot icon again

## Architecture

### Backend Components

```
ai_assistant/
├── models/
│   ├── ai_provider.py      # OpenAI API integration
│   ├── ai_config.py         # Configuration management
│   ├── ai_conversation.py   # Conversation handling
│   └── ai_message.py        # Message storage
├── controllers/
│   └── main.py              # HTTP/JSON-RPC endpoints
├── security/
│   ├── ai_assistant_security.xml  # Groups and rules
│   └── ir.model.access.csv        # Model access rights
└── views/
    ├── ai_config_views.xml         # Configuration UI
    ├── ai_conversation_views.xml   # Conversation management
    └── ai_assistant_menu.xml       # Menu structure
```

### Frontend Components

```
static/src/
├── js/
│   ├── ai_assistant_service.js  # Backend communication service
│   └── ai_chat_window.js        # Chat UI component
├── xml/
│   └── ai_chat_window.xml       # OWL templates
└── scss/
    └── ai_assistant.scss        # Styles
```

### API Endpoints

- `POST /ai_assistant/start_conversation` - Create new conversation
- `POST /ai_assistant/send_message` - Send message and get response
- `POST /ai_assistant/get_conversation` - Get conversation details
- `POST /ai_assistant/list_conversations` - List user's conversations
- `POST /ai_assistant/close_conversation` - Close a conversation
- `POST /ai_assistant/get_config` - Get configuration

### Database Models

- `ai.provider` - AI provider configuration (API keys, models)
- `ai.config` - Global AI assistant settings
- `ai.conversation` - User conversations
- `ai.message` - Individual messages in conversations

## Security

### User Groups

- **AI Assistant / User**: Can use the assistant and view own conversations
- **AI Assistant / Manager**: Can configure settings and view all conversations

### Access Control

- Users can only see their own conversations (enforced by record rules)
- AI operations respect Odoo's permission system
- Users can only query/modify data they have access to
- API keys are stored with password-level security

### Best Practices

1. **Start with Search Only**: Enable only database search initially
2. **Test Before Enabling Writes**: Thoroughly test in a staging environment
3. **Monitor Usage**: Review conversations regularly
4. **Limit Permissions**: Only grant Manager role to trusted users
5. **Secure API Keys**: Keep your OpenAI API keys confidential

## Function Calling / Tools

The AI can use these tools when appropriate:

### search_records
Search for records in the database.

Parameters:
- `model`: Odoo model name (e.g., "res.partner")
- `domain`: Odoo domain filter
- `fields`: List of fields to retrieve
- `limit`: Max number of records

### create_record
Create a new record (requires permission).

Parameters:
- `model`: Odoo model name
- `values`: Dictionary of field values

### update_record
Update an existing record (requires permission).

Parameters:
- `model`: Odoo model name
- `record_id`: ID of record to update
- `values`: Dictionary of field values to update

### get_model_info
Get information about an Odoo model.

Parameters:
- `model`: Odoo model name

## Troubleshooting

### AI not responding
- Check API key is configured correctly
- Test the connection in AI Provider settings
- Check Odoo logs for errors
- Verify internet connectivity

### Can't find records
- Ensure "Enable Database Search" is enabled
- Check user has access to the records
- Review Odoo logs for permission errors

### Chat window not appearing
- Verify module is installed and updated
- Check browser console for JavaScript errors
- Clear browser cache
- Ensure user has "AI Assistant / User" group

### Conversations not saving
- Check database permissions
- Review ir.model.access.csv configuration
- Check Odoo logs for database errors

## Development

### Adding Custom Tools

Edit `ai_config.py` → `get_available_tools()`:

```python
tools.append({
    'type': 'function',
    'function': {
        'name': 'my_custom_tool',
        'description': 'What this tool does',
        'parameters': {
            'type': 'object',
            'properties': {
                'param1': {
                    'type': 'string',
                    'description': 'Parameter description'
                }
            },
            'required': ['param1']
        }
    }
})
```

Then implement in `ai_conversation.py` → `_execute_tool()`.

### Customizing UI

- Modify `static/src/scss/ai_assistant.scss` for styling
- Edit `static/src/xml/ai_chat_window.xml` for layout
- Update `static/src/js/ai_chat_window.js` for behavior

### Extending Models

Inherit from the AI models:

```python
class CustomAIConfig(models.Model):
    _inherit = 'ai.config'

    custom_field = fields.Char('Custom Field')
```

## Changelog

### Version 1.0.0 (2024)
- Initial release
- OpenAI GPT integration
- Conversational interface
- Database search, create, update tools
- Context-aware prompts
- User and Manager groups
- Conversation history
- System tray integration

## License

LGPL-3

## Credits

Developed for Odoo 19.0

## Support

For issues and feature requests, contact your system administrator.
