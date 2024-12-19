# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.http import request
from odoo.tools import email_normalize, get_lang, html2plaintext, is_html_empty, plaintext2html


class ChatbotScript(models.Model):
    _name = 'chatbot.script'
    _description = 'Chatbot Script'
    _inherit = ['image.mixin', 'utm.source.mixin']
    _rec_name = 'title'
    _order = 'title, id'

    # we keep a separate field for UI since name is manipulated by 'utm.source.mixin'
    title = fields.Char('Title', required=True, translate=True, default="Chatbot")
    active = fields.Boolean(default=True)
    image_1920 = fields.Image(related='operator_partner_id.image_1920', readonly=False)

    script_step_ids = fields.One2many('chatbot.script.step', 'chatbot_script_id',
        copy=True, string='Script Steps')
    operator_partner_id = fields.Many2one('res.partner', string='Bot Operator',
        ondelete='restrict', required=True, copy=False)
    livechat_channel_count = fields.Integer(string='Livechat Channel Count', compute='_compute_livechat_channel_count')
    first_step_warning = fields.Selection([
        ('first_step_operator', 'First Step Operator'),
        ('first_step_invalid', 'First Step Invalid'),
    ], compute="_compute_first_step_warning")

    def _compute_livechat_channel_count(self):
        channels_data = self.env['im_livechat.channel.rule']._read_group(
            [('chatbot_script_id', 'in', self.ids)], ['chatbot_script_id'], ['channel_id:count_distinct'])
        mapped_channels = {chatbot_script.id: count_distinct for chatbot_script, count_distinct in channels_data}
        for script in self:
            script.livechat_channel_count = mapped_channels.get(script.id, 0)

    @api.depends('script_step_ids.step_type')
    def _compute_first_step_warning(self):
        for script in self:
            allowed_first_step_types = [
                'question_selection',
                'question_email',
                'question_phone',
                'free_input_single',
                'free_input_multi',
            ]
            welcome_steps = script.script_step_ids and script._get_welcome_steps()
            if welcome_steps and welcome_steps[-1].step_type == 'forward_operator':
                script.first_step_warning = 'first_step_operator'
            elif welcome_steps and welcome_steps[-1].step_type not in allowed_first_step_types:
                script.first_step_warning = 'first_step_invalid'
            else:
                script.first_step_warning = False

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, title=_("%s (copy)", script.title)) for script, vals in zip(self, vals_list)]

    def copy(self, default=None):
        """ Correctly copy the 'triggering_answer_ids' field from the original script_step_ids to the clone.
        This needs to be done in post-processing to make sure we get references to the newly created
        answers from the copy instead of references to the answers of the original.

        This implementation assumes that the order of created steps and answers will be kept between
        the original and the clone, using 'zip()' to match the records between the two. """
        default = default or {}
        new_scripts = super().copy(default=default)
        if 'question_ids' in default:
            return new_scripts

        for old_script, new_script in zip(self, new_scripts):
            original_steps = old_script.script_step_ids.sorted()
            clone_steps = new_script.script_step_ids.sorted()

            answers_map = {}
            for clone_step, original_step in zip(clone_steps, original_steps):
                for clone_answer, original_answer in zip(clone_step.answer_ids.sorted(), original_step.answer_ids.sorted()):
                    answers_map[original_answer] = clone_answer

            for clone_step, original_step in zip(clone_steps, original_steps):
                clone_step.write({
                    'triggering_answer_ids': [
                        (4, answer.id)
                        for answer in [
                            answers_map[original_answer]
                            for original_answer
                            in original_step.triggering_answer_ids
                        ]
                    ]
                })
        return new_scripts

    @api.model_create_multi
    def create(self, vals_list):
        operator_partners_values = [{
            'name': vals['title'],
            'image_1920': vals.get('image_1920', False),
            'active': False,
        } for vals in vals_list if 'operator_partner_id' not in vals and 'title' in vals]

        operator_partners = self.env['res.partner'].create(operator_partners_values)

        for vals, partner in zip(
            [vals for vals in vals_list if 'operator_partner_id' not in vals and 'title' in vals],
            operator_partners
        ):
            vals['operator_partner_id'] = partner.id

        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)

        if 'title' in vals:
            self.operator_partner_id.write({'name': vals['title']})

        return res

    def _get_welcome_steps(self):
        """ Returns a sub-set of script_step_ids that only contains the "welcoming steps".
        We consider those as all the steps the bot will say before expecting a first answer from
        the end user.

        Example 1:
        - step 1 (question_selection): What do you want to do? - Create a Lead, -Create a Ticket
        - step 2 (text): Thank you for visiting our website!
        -> The welcoming steps will only contain step 1, since directly after that we expect an
        input from the user

        Example 2:
        - step 1 (text): Hello! I'm a bot!
        - step 2 (text): I am here to help lost users.
        - step 3 (question_selection): What do you want to do? - Create a Lead, -Create a Ticket
        - step 4 (text): Thank you for visiting our website!
        -> The welcoming steps will contain steps 1, 2 and 3.
        Meaning the bot will have a small monologue with himself before expecting an input from the
        end user.

        This is important because we need to display those welcoming steps in a special fashion on
        the frontend, since those are not inserted into the discuss.channel as actual mail.messages,
        to avoid bloating the channels with bot messages if the end-user never interacts with it. """
        self.ensure_one()

        welcome_steps = self.env['chatbot.script.step']
        for step in self.script_step_ids:
            welcome_steps += step
            if step.step_type != 'text':
                break

        return welcome_steps

    def _post_welcome_steps(self, discuss_channel):
        """ Welcome messages are only posted after the visitor's first interaction with the chatbot.
        See 'chatbot.script#_get_welcome_steps()' for more details.

        Side note: it is important to set the 'chatbot_current_step_id' on each iteration so that
        it's correctly set when going into 'discuss_channel#_message_post_after_hook()'. """

        self.ensure_one()
        posted_messages = self.env['mail.message']

        for welcome_step in self._get_welcome_steps():
            discuss_channel.chatbot_current_step_id = welcome_step.id

            if not is_html_empty(welcome_step.message):
                posted_messages += discuss_channel.with_context(mail_create_nosubscribe=True).message_post(
                    author_id=self.operator_partner_id.id,
                    body=plaintext2html(welcome_step.message),
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )

        return posted_messages

    def action_view_livechat_channels(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('im_livechat.im_livechat_channel_action')
        action['domain'] = [('rule_ids.chatbot_script_id', 'in', self.ids)]
        return action

    # --------------------------
    # Tooling / Misc
    # --------------------------

    def _format_for_frontend(self):
        """ Small utility method that formats the script into a dict usable by the frontend code. """
        self.ensure_one()

        return {
            'id': self.id,
            'name': self.title,
            'partner': {'id': self.operator_partner_id.id, 'type': 'partner', 'name': self.operator_partner_id.name},
            'welcomeSteps': [
                step._format_for_frontend()
                for step in self._get_welcome_steps()
            ]
        }

    def _validate_email(self, email_address, discuss_channel):
        email_address = html2plaintext(email_address)
        email_normalized = email_normalize(email_address)

        posted_message = False
        error_message = False
        if not email_normalized:
            error_message = _(
                "'%(input_email)s' does not look like a valid email. Can you please try again?",
                input_email=email_address
            )
            posted_message = discuss_channel._chatbot_post_message(self, plaintext2html(error_message))

        return {
            'success': bool(email_normalized),
            'posted_message': posted_message,
            'error_message': error_message,
        }

    def _get_chatbot_language(self):
        return get_lang(
            self.env, lang_code=request and request.httprequest.cookies.get("frontend_lang")
        ).code
