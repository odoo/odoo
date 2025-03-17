# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.osv import expression
from odoo.tools import html2plaintext, is_html_empty, email_normalize, plaintext2html
from odoo.addons.mail.tools.discuss import Store

from collections import defaultdict
from markupsafe import Markup


class ChatbotScriptStep(models.Model):
    _name = 'chatbot.script.step'
    _description = 'Chatbot Script Step'
    _order = 'sequence, id'
    _rec_name = 'message'

    message = fields.Text(string='Message', translate=True)
    sequence = fields.Integer(string='Sequence')
    chatbot_script_id = fields.Many2one(
        'chatbot.script', string='Chatbot', required=True, ondelete='cascade')
    step_type = fields.Selection([
        ('text', 'Text'),
        ('question_selection', 'Question'),
        ('question_email', 'Email'),
        ('question_phone', 'Phone'),
        ('forward_operator', 'Forward to Operator'),
        ('free_input_single', 'Free Input'),
        ('free_input_multi', 'Free Input (Multi-Line)'),
    ], default='text', required=True)
    # answers
    answer_ids = fields.One2many(
        'chatbot.script.answer', 'script_step_id',
        copy=True, string='Answers')
    triggering_answer_ids = fields.Many2many(
        'chatbot.script.answer', domain="[('script_step_id.sequence', '<', sequence)]",
        compute='_compute_triggering_answer_ids', readonly=False, store=True,
        copy=False,  # copied manually, see chatbot.script#copy
        string='Only If', help='Show this step only if all of these answers have been selected.')
    # forward-operator specifics
    is_forward_operator_child = fields.Boolean(compute='_compute_is_forward_operator_child')

    @api.depends('sequence')
    def _compute_triggering_answer_ids(self):
        for step in self.filtered('triggering_answer_ids'):
            update_command = [Command.unlink(answer.id) for answer in step.triggering_answer_ids
                                if answer.script_step_id.sequence >= step.sequence]
            if update_command:
                step.triggering_answer_ids = update_command

    @api.depends('sequence', 'triggering_answer_ids', 'chatbot_script_id.script_step_ids.triggering_answer_ids',
                 'chatbot_script_id.script_step_ids.answer_ids', 'chatbot_script_id.script_step_ids.sequence')
    def _compute_is_forward_operator_child(self):
        parent_steps_by_chatbot = {}
        for chatbot in self.chatbot_script_id:
            parent_steps_by_chatbot[chatbot.id] = chatbot.script_step_ids.filtered(
                lambda step: step.step_type in ['forward_operator', 'question_selection']
            ).sorted(lambda s: s.sequence, reverse=True)
        for step in self:
            parent_steps = parent_steps_by_chatbot[step.chatbot_script_id.id].filtered(
                lambda s: s.sequence < step.sequence
            )
            parent = step
            while True:
                parent = parent._get_parent_step(parent_steps)
                if not parent or parent.step_type == 'forward_operator':
                    break
            step.is_forward_operator_child = parent and parent.step_type == 'forward_operator'

    @api.model_create_multi
    def create(self, vals_list):
        """ Ensure we correctly assign sequences when creating steps.
        Indeed, sequences are very important within the script, and will break the whole flow if
        not correctly defined.

        This override will group created steps by chatbot_id and increment the sequence accordingly.
        It will also look for an existing step for that chatbot and resume from the highest sequence.

        This cannot be done in a default_value for the sequence field as we cannot search by
        runbot_id.
        It is also safer and more efficient to do it here (we can batch everything).

        It is still possible to manually pass the 'sequence' in the values, which will take priority. """

        vals_by_chatbot_id = {}
        for vals in vals_list:
            chatbot_id = vals.get('chatbot_script_id')
            if chatbot_id:
                step_values = vals_by_chatbot_id.get(chatbot_id, [])
                step_values.append(vals)
                vals_by_chatbot_id[chatbot_id] = step_values

        read_group_results = self.env['chatbot.script.step']._read_group(
            [('chatbot_script_id', 'in', list(vals_by_chatbot_id))],
            ['chatbot_script_id'],
            ['sequence:max'],
        )
        max_sequence_by_chatbot = {
            chatbot_script.id: sequence
            for chatbot_script, sequence in read_group_results
        }

        for chatbot_id, step_vals in vals_by_chatbot_id.items():
            current_sequence = 0
            if chatbot_id in max_sequence_by_chatbot:
                current_sequence = max_sequence_by_chatbot[chatbot_id] + 1

            for vals in step_vals:
                if 'sequence' in vals:
                    current_sequence = vals.get('sequence')
                else:
                    vals['sequence'] = current_sequence
                    current_sequence += 1

        return super().create(vals_list)

    # --------------------------
    # Business Methods
    # --------------------------

    def _chatbot_prepare_customer_values(self, discuss_channel, create_partner=True, update_partner=True):
        """ Common method that allows retreiving default customer values from the discuss.channel
        following a chatbot.script.

        This method will return a dict containing the 'customer' values such as:
        {
            'partner': The created partner (see 'create_partner') or the partner from the
              environment if not public
            'email': The email extracted from the discuss.channel messages
              (see step_type 'question_email')
            'phone': The phone extracted from the discuss.channel messages
              (see step_type 'question_phone')
            'description': A default description containing the "Please contact me on" and "Please
              call me on" with the related email and phone numbers.
              Can be used as a default description to create leads or tickets for example.
        }

        :param record discuss_channel: the discuss.channel holding the visitor's conversation with the bot.
        :param bool create_partner: whether or not to create a res.partner is the current user is public.
          Defaults to True.
        :param bool update_partner: whether or not to set update the email and phone on the res.partner
          from the environment (if not a public user) if those are not set yet. Defaults to True.

        :return dict: a dict containing the customer values."""

        partner = False
        user_inputs = discuss_channel._chatbot_find_customer_values_in_messages({
            'question_email': 'email',
            'question_phone': 'phone',
        })
        input_email = user_inputs.get('email', False)
        input_phone = user_inputs.get('phone', False)

        if self.env.user._is_public() and create_partner:
            partner = self.env['res.partner'].create({
                'name': input_email,
                'email': input_email,
                'phone': input_phone,
            })
        elif not self.env.user._is_public():
            partner = self.env.user.partner_id
            if update_partner:
                # update email/phone value from partner if not set
                update_values = {}
                if input_email and not partner.email:
                    update_values['email'] = input_email
                if input_phone and not partner.phone:
                    update_values['phone'] = input_phone
                if update_values:
                    partner.write(update_values)

        description = Markup('')
        if input_email:
            description += Markup('%s<strong>%s</strong><br>') % (_('Please contact me on: '), input_email)
        if input_phone:
            description += Markup('%s<strong>%s</strong><br>') % (_('Please call me on: '), input_phone)
        if description:
            description += Markup('<br>')

        return {
            'partner': partner,
            'email': input_email,
            'phone': input_phone,
            'description': description,
        }

    def _fetch_next_step(self, selected_answer_ids):
        """ Fetch the next step depending on the user's selected answers.
            If a step contains multiple triggering answers from the same step the condition between
            them must be a 'OR'. If is contains multiple triggering answers from different steps the
            condition between them must be a 'AND'.

            e.g:

            STEP 1 : A B
            STEP 2 : C D
            STEP 3 : E
            STEP 4 ONLY IF A B C E

            Scenario 1 (A C E):

            A in (A B) -> OK
            C in (C)   -> OK
            E in (E)   -> OK

            -> OK

            Scenario 2 (B D E):

            B in (A B) -> OK
            D in (C)   -> NOK
            E in (E)   -> OK

            -> NOK
        """
        self.ensure_one()
        domain = [('chatbot_script_id', '=', self.chatbot_script_id.id), ('sequence', '>', self.sequence)]
        if selected_answer_ids:
            domain = expression.AND([domain, [
                '|',
                ('triggering_answer_ids', '=', False),
                ('triggering_answer_ids', 'in', selected_answer_ids.ids)]])
        steps = self.env['chatbot.script.step'].search(domain)
        for step in steps:
            if not step.triggering_answer_ids:
                return step
            answers_by_step = defaultdict(list)
            for answer in step.triggering_answer_ids:
                answers_by_step[answer.script_step_id.id].append(answer)
            if all(any(answer in step_triggering_answers for answer in selected_answer_ids)
                   for step_triggering_answers in answers_by_step.values()):
                return step
        return self.env['chatbot.script.step']

    def _get_parent_step(self, all_parent_steps):
        """ Returns the first preceding step that matches either the triggering answers
         or the possible answers the user can select """
        self.ensure_one()

        if not self.chatbot_script_id.ids:
            return self.env['chatbot.script.step']

        for step in all_parent_steps:
            if step.sequence >= self.sequence:
                continue
            if self.triggering_answer_ids:
                if not (all(answer in self.triggering_answer_ids for answer in step.triggering_answer_ids) or
                        any(answer in self.triggering_answer_ids for answer in step.answer_ids)):
                    continue
            elif step.triggering_answer_ids:
                continue
            return step
        return self.env['chatbot.script.step']

    def _is_last_step(self, discuss_channel=False):
        self.ensure_one()
        discuss_channel = discuss_channel or self.env['discuss.channel']

        # if it's not a question and if there is no next step, then we end the script
        # sudo: chatbot.script.answser - visitor can access their own answers
        if self.step_type != "question_selection" and not self._fetch_next_step(
            discuss_channel.sudo().chatbot_message_ids.user_script_answer_id
        ):
            return True

        return False

    def _process_answer(self, discuss_channel, message_body):
        """ Method called when the user reacts to the current chatbot.script step.
        For most chatbot.script.step#step_types it simply returns the next chatbot.script.step of
        the script (see '_fetch_next_step').

        Some extra processing is done for steps of type 'question_email' and 'question_phone' where
        we store the user raw answer (the mail message HTML body) into the chatbot.message in order
        to be able to recover it later (see '_chatbot_prepare_customer_values').

        :param discuss_channel:
        :param message_body:
        :return: script step to display next
        :rtype: 'chatbot.script.step' """

        self.ensure_one()

        user_text_answer = html2plaintext(message_body)
        if self.step_type == 'question_email' and not email_normalize(user_text_answer):
            # if this error is raised, display an error message but do not go to next step
            raise ValidationError(_('"%s" is not a valid email.', user_text_answer))

        if self.step_type in ['question_email', 'question_phone']:
            chatbot_message = self.env['chatbot.message'].search([
                ('discuss_channel_id', '=', discuss_channel.id),
                ('script_step_id', '=', self.id),
            ], limit=1)

            if chatbot_message:
                chatbot_message.write({'user_raw_answer': message_body})
                self.env.flush_all()

        # sudo: chatbot.script.answer - visitor can access their own answer
        return self._fetch_next_step(discuss_channel.sudo().chatbot_message_ids.user_script_answer_id)

    def _process_step(self, discuss_channel):
        """ When we reach a chatbot.step in the script we need to do some processing on behalf of
        the bot. Which is for most chatbot.script.step#step_types just posting the message field.

        Some extra processing may be required for special step types such as 'forward_operator',
        'create_lead', 'create_ticket' (in their related bridge modules).
        Those will have a dedicated processing method with specific docstrings.

        Returns the mail.message posted by the chatbot's operator_partner_id. """

        self.ensure_one()
        # sudo: discuss.channel - updating current step on the channel is allowed
        discuss_channel.sudo().chatbot_current_step_id = self.id

        if self.step_type == 'forward_operator':
            return self._process_step_forward_operator(discuss_channel)
        return discuss_channel._chatbot_post_message(self.chatbot_script_id, plaintext2html(self.message))

    def _process_step_forward_operator(self, discuss_channel):
        """ Special type of step that will add a human operator to the conversation when reached,
        which stops the script and allow the visitor to discuss with a real person.

        In case we don't find any operator (e.g: no-one is available) we don't post any messages.
        The script will continue normally, which allows to add extra steps when it's the case
        (e.g: ask for the visitor's email and create a lead). """

        human_operator = False
        posted_message = self.env["mail.message"]

        if discuss_channel.livechat_channel_id:
            # sudo: res.users - visitor can access operator of their channel
            # sudo: res.lang - visitor can access their own lang
            human_operator = discuss_channel.livechat_channel_id.sudo()._get_operator(
                lang=self.env.context.get("lang"), country_id=discuss_channel.country_id.id
            )

        # handle edge case where we found yourself as available operator -> don't do anything
        # it will act as if no-one is available (which is fine)
        if human_operator and human_operator != self.env.user:
            if self.message:
                # first post the message of the step (if we have one)
                posted_message = discuss_channel._chatbot_post_message(self.chatbot_script_id, plaintext2html(self.message))

            # next, add the human_operator to the channel and post a "Operator joined the channel" notification
            discuss_channel.with_user(human_operator).sudo().add_members(human_operator.partner_id.ids, open_chat_window=True)

            # finally, rename the channel to include the operator's name
            discuss_channel.sudo().name = ' '.join([
                self.env.user.display_name if not self.env.user._is_public() else discuss_channel.anonymous_name,
                human_operator.livechat_username if human_operator.livechat_username else human_operator.name
            ])
            step_message = next((
                # sudo - chatbot.message.id: visitor can access chat bot messages.
                m.mail_message_id for m in discuss_channel.sudo().chatbot_message_ids
                if m.script_step_id == self
                and m.mail_message_id.author_id == self.chatbot_script_id.operator_partner_id
            ), self.env["mail.message"])
            discuss_channel._bus_send_store(
                Store(
                    "ChatbotStep",
                    {
                        "id": (self.id, step_message.id),
                        "scriptStep": self.id,
                        "message": step_message.id,
                        "operatorFound": True,
                    },
                )
            )
            discuss_channel._broadcast(human_operator.partner_id.ids)
            discuss_channel.channel_pin(pinned=True)

        return posted_message

    def _to_store(self, store: Store, /, *, fields=None):
        if fields is None:
            fields = ["answer_ids", "message", "type"]
        for step in self:
            data = step._read_format(
                [f for f in fields if f not in {"answer_ids", "message", "type"}], load=False
            )[0]
            if "answer_ids" in fields:
                data["answers"] = Store.many(step.answer_ids)
            if "message" in fields:
                data["message"] = plaintext2html(step.message) if step.message else False
            if "type" in fields:
                data["type"] = step.step_type
            store.add("chatbot.script.step", data)

    # --------------------------
    # Tooling / Misc
    # --------------------------

    def _format_for_frontend(self):
        """ Small utility method that formats the step into a dict usable by the frontend code. """
        self.ensure_one()

        return {
            'id': self.id,
            'answers': [{
                'id': answer.id,
                "name": answer.name,
                "redirect_link": answer.redirect_link,
            } for answer in self.answer_ids],
            'message': plaintext2html(self.message) if not is_html_empty(self.message) else False,
            'isLast': self._is_last_step(),
            'type': self.step_type
        }
