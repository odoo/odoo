# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import datetime
import pytz
from markupsafe import Markup
from markdown import markdown

from odoo import fields, models, api, Command
from odoo.exceptions import AccessError

from odoo.addons.iap.tools import iap_tools
from odoo.tools.mail import html_sanitize


DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'

class DiscussChannel(models.Model):
    """ Chat Session
        Reprensenting a conversation between users.
        It extends the base method for usage with AI assistant.
    """

    _name = 'discuss.channel'
    _inherit = ['discuss.channel']

    channel_type = fields.Selection(selection_add=[('ai_composer', 'Draft with AI')], ondelete={'ai_composer': 'cascade'})
    ai_context = fields.Json("Context for AI agent")

    @api.model
    def _get_record_info(self, model, record):
        # Get all fields metadata for the model
        fields_info = model.fields_get()
        result = {}

        for field_name, field_attrs in fields_info.items():
            field_type = field_attrs['type']
            field_value = record[field_name]

            try:
                # Handle relational fields
                if field_type == 'many2one':
                    result[field_name] = field_value.display_name if field_value else None
                elif field_type in ['one2many', 'many2many']:
                    linked_records = self.env[field_value._name].browse(field_value.ids)
                    if len(linked_records) > 50:  # there have been cases were too many linked records have flooded the context - avoid that by filtering them out
                        continue
                    else:
                        result[field_name] = [record.display_name for record in linked_records]
                elif field_type == 'binary':
                    continue  # we don't include binary fields in the record info JSON
                else:
                    # Handle basic field types (dates, binaries, etc.)
                    if isinstance(field_value, datetime.datetime):
                        user_tz = pytz.timezone(self.env.user.tz)
                        result[field_name] = field_value.astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S') if field_value else None
                    elif isinstance(field_value, models.BaseModel):
                        # Handle unexpected recordset returns (shouldn't happen for non-relational fields)
                        result[field_name] = field_value.ids
                    else:
                        result[field_name] = field_value
            except AccessError:  # if the user doesn't have access to a field, don't include it in the AI's context
                continue

        final_json = json.dumps(result, default=str)

        return {
            'role': 'system',
            'content':
                f'This conversation is applying on an odoo {model.display_name} record. The following JSON contains all of the records details.\n' + final_json
        }

    @api.model
    def _get_chatter_info(self, record):
        chatter_messages = []

        for message in record['message_ids']:
            chatter_messages.append(f'({message.subtype_id.name}) {message.author_id.name}: {Markup(message.body).striptags().strip()},')
        # the messages are stored from newest to oldest - reverse them so they are formatted like the conversation history
        chatter_messages = " ".join(list(reversed(chatter_messages)))

        return {
            'role': 'system',
            'content': 'The previous correspondance, from oldest to newest, for this record is this: ' + chatter_messages
        }

    @api.model
    def _initialise_context(self, record_model, record_id, caller_component, textSelection):
        # Get the model and record if needed
        if caller_component in ['html_field_record', 'html_field_composer', 'composer_ai_button', 'chatter_ai_button']:
            model = self.env[record_model]
            record = model.browse(record_id).ensure_one()

        temp_context = [{
            'role': 'system',
            'content': f'You are a helpful AI assistant to {self.env.user.display_name}. Your job is to assist with text drafting inside the ERP software odoo.',
        }]

        # If required, pass some record information to the model's context
        if caller_component in ['html_field_record', 'html_field_composer', 'composer_ai_button', 'chatter_ai_button']:
            temp_context.append(self._get_record_info(model, record))

        # If required, pass the previous chatter messsages to the model's context
        if caller_component in ['html_field_composer', 'composer_ai_button', 'chatter_ai_button']:
            temp_context.append(self._get_chatter_info(record))

        # Further instruction message based on where we call the AI is called from
        if caller_component in ['composer_ai_button', 'html_field_composer', 'chatter_ai_button']:
            # from the message composer
            temp_context.append({
                'role': 'system',
                'content': 'Your job is to help with drafting messages. If the user asks you to write a reply or a message, YOUR REPLY WILL BE INSERTED AS IS for the correspondance. Follow the tone from the previous correspondance, and WRITE ONLY THE BODY OF THE MESSAGE. DO NOT ADD ADDITIONAL COMMENTARY, A SUBJECT LINE, OR A SIGNATURE. ALWAYS FORMAT YOUR ANSWERS USING MARKDOWN, AVOID USING HTML'
            })
        elif caller_component in ['html_field_record']:
            # from an html field in model record descriptions
            temp_context.append({
                'role': 'system',
                'content': f'Your job is to help with drafting the description of a {record_model} record. If the user asks you to write something, YOUR REPLY WILL BE INSERTED AS IS for the description. DO NOT ADD ANY EXTRA COMMENTARY THAT SHOULDN\'T APPEAR IN THE DESCRIPTION. Give your answers succinctly and to the point. ALWAYS FORMAT YOUR ANSWERS USING MARKDOWN, AVOID USING HTML'
            })
        elif caller_component in ['html_field_editor']:
            # from an html field in the web editor
            temp_context.append({
                'role': 'system',
                'content': 'Your job is to help with drafting text for the user\'s website inside the website editor. If the user asks you to write something, YOUR REPLY WILL BE INSERTED AS IS in the website. DO NOT ADD ANY EXTRA COMMENTARY THAT SHOULDN\'T APPEAR IN THE WEBSITE. Give your answers succinctly and to the point. ALWAYS FORMAT YOUR ANSWERS USING MARKDOWN, AVOID USING HTML'
            })
        elif caller_component in ['html_field_text_select']:
            # from the text select inside an html field
            temp_context.append({
                'role': 'system',
                'content': f'Your job is to suggest alternatives to a piece of text the user has written. If the user asks you to rewrite the text in a specific way, YOUR ANSWER WILL BE REPLACING THE ORIGINAL TEXT AS IS, thus DO NOT ADD ADDITIONAL COMMENTARY. The text that you will be rewritting is the following: {textSelection}'
            })

        # Finish the context by the "first" message sent by the assistant
        if caller_component in ['html_field_record', 'html_field_composer', 'composer_ai_button', 'html_field_editor']:
            temp_context.append({
                'role': 'assistant',
                'content': 'Hello, what can I help you with?',
            })
        else:
            temp_context.append({
                'role': 'assistant',
                'content': 'Hello, how can I rewrite your text?',
            })

        self.ai_context = temp_context

    @api.model
    def create_ai_composer_channel(self, caller_component, record_name, record_model=None, record_id=None, textSelection=None):
        # create a new AI chat
        channel = self.create({
            'channel_member_ids': [
                Command.create({
                    'partner_id': self.env.user.partner_id.id,
                }),
            ],
            'channel_type': 'ai_composer',
            'name': 'AI: ' + record_name,
        })

        # fetch the record's info and feed it into context
        channel._initialise_context(record_model, record_id, caller_component, textSelection)

        return channel

    def add_message_to_context(self, message, author):
        # here I tried doing self.ai_context.append(...) but it didn't work :()
        current_context = self.ai_context
        current_context.append({
            'role': author,
            'content': message,
        })
        self.ai_context = current_context

    def submit_to_model(self, prompt, conversation_history):
        try:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = IrConfigParameter.get_param('web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            database_id = IrConfigParameter.get_param('database.uuid')
            print(conversation_history)
            response = iap_tools.iap_jsonrpc(olg_api_endpoint + "/api/olg/1/chat", params={
                'prompt': prompt,
                'conversation_history': conversation_history or [],
                'database_id': database_id,
            }, timeout=30)
            if response['status'] == 'success':
                return response['content']
            elif response['status'] == 'error_prompt_too_long':
                return "⚠️ Sorry, your prompt is too long. Try to say it in fewer words."
            elif response['status'] == 'limit_call_reached':
                return "⚠️ You have reached the maximum number of requests for this service. Try again later."
            else:
                return "⚠️ Sorry, we could not generate a response. Please try again later."
        except AccessError:
            return "⚠️ Oops, it looks like our AI is unreachable!"

    def create_response(self, model_response):
        # add the model response in the context
        self.add_message_to_context(model_response, 'assistant')
        # translate the markdown formatted text into HTML and sanitize the HTML
        response_html = markdown(model_response, extensions=["fenced_code", "tables"])
        final_response = Markup(html_sanitize(response_html))
        odoobot_id = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
        self.sudo().message_post(
            author_id=odoobot_id,
            body=final_response,
            message_type="comment",
            silent=True,
            subtype_xmlid="mail.mt_comment",
        )
