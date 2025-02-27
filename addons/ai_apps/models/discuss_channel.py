# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import datetime
from markupsafe import Markup

from odoo import fields, models, api, Command, _
from odoo.exceptions import UserError, AccessError

from odoo.addons.iap.tools import iap_tools

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
    def _initialise_context(self, record_model, record_id):
        # Get the model and record
        model = self.env[record_model]
        record = model.browse(int(record_id[1:-1])).ensure_one()

        # Get all fields metadata for the model
        fields_info = model.fields_get()
        result = {}

        for field_name, field_attrs in fields_info.items():
            field_type = field_attrs['type']
            field_value = record[field_name]

            # Handle relational fields
            if field_type == 'many2one':
                result[field_name] = field_value.display_name if field_value else None
            elif field_type in ['one2many', 'many2many']:
                result[field_name] = [record.display_name for record in self.env[field_value._name].browse(field_value.ids)]
            else:
                # Handle basic field types (dates, binaries, etc.)
                if isinstance(field_value, datetime.datetime):
                    result[field_name] = field_value.strftime('%Y-%m-%d %H:%M:%S') if field_value else None
                elif isinstance(field_value, models.BaseModel):
                    # Handle unexpected recordset returns (shouldn't happen for non-relational fields)
                    result[field_name] = field_value.ids
                else:
                    result[field_name] = field_value

        final_json = json.dumps(result, default=str)

        # Get all previous communication from the chatter
        chatter_messages = []
        for message in record['message_ids']:
            # chatter_messages.append({
            #     'author': message.author_id.name,
            #     'message_type': message.subtype_id.name,
            #     'message_body': message.body,
            # })
            chatter_messages.append(f'({message.subtype_id.name}) {message.author_id.name}: {message.body},')
        # the messages are stored from newest to oldest - reverse them so they are formatted like the conversation history
        chatter_messages = " ".join(list(reversed(chatter_messages)))

        self.ai_context = [{
            'role': 'system',
            'content': f'You are a helpful AI assistant to {self.env.user.display_name}. Your job is to assist with message composition inside the ERP software odoo.',
        }, {
            'role': 'system',
            'content':
                f'This conversation is applying on an odoo {record_model} record. The following JSON contains all of the records details.\n' + final_json
        }, {
            'role': 'system',
            'content': 'The previous correspondance, from oldest to newest, for this record is this: ' + chatter_messages
        }, {
            'role': 'system',
            'content': 'If the user asks you to write a reply, your reply will be used as is for the message. Format it like an email and write only the body of the email. Do not add additional commentary or a subject line. Otherwise, the user is conversing with you. Reply as if you are in a conversation with the user.'
        }, {
            'role': 'assistant',
            'content': 'Hello, what can I help you with?',
        }]

    @api.model
    def create_ai_composer_channel(self, record_name, record_model, record_id):
        # create a new AI chat
        channel = self.create({
            'channel_member_ids': [
                Command.create({
                    'partner_id': self.env.user.partner_id.id,
                })
            ],
            'channel_type': 'ai_composer',
            'name': 'AI: ' + record_name,
        })

        # fetch the record's info and feed it into context
        channel._initialise_context(record_model, record_id)

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
            response = iap_tools.iap_jsonrpc(olg_api_endpoint + "/api/olg/1/chat", params={
                'prompt': prompt,
                'conversation_history': conversation_history or [],
                'database_id': database_id,
            }, timeout=30)
            if response['status'] == 'success':
                return response['content']
            elif response['status'] == 'error_prompt_too_long':
                raise UserError(_("Sorry, your prompt is too long. Try to say it in fewer words."))
            elif response['status'] == 'limit_call_reached':
                raise UserError(_("You have reached the maximum number of requests for this service. Try again later."))
            else:
                raise UserError(_("Sorry, we could not generate a response. Please try again later."))
        except AccessError:
            raise AccessError(_("Oops, it looks like our AI is unreachable!"))

    def create_response(self, model_response):
        odoobot_id = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
        self.add_message_to_context(model_response, 'assistant')
        # dummy_message = "poop \n poop"
        self.sudo().message_post(
            author_id=odoobot_id,
            body=Markup(model_response),
            message_type="comment",
            silent=True,
            subtype_xmlid="mail.mt_comment",
        )
