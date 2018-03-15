from datetime import datetime
from odoo import api, fields, models, tools, SUPERUSER_ID

class MailPartnerMixin(models.AbstractModel):
    """ A mixin to add partner registration support to mail.thread
        mail_thread model is meant to be inherited (before mail.thread) by any model that needs to
        add partner registration and auto subscribe of partner on reply.
        -Register mail informations on "new_message" (email_from,email_cc,partner_id,name)
        -Create partner on update_message or new_message with respect to the "_partner_creation_strategy".
        -The list of partner to subcribe and/or register are defined by "_emails_subscribe" 
        and "_emails_subscribe_if_exists". By default, the "email_from" used for the creation of the record and all cc 
        will be subscribed and a partner can be created only for the "email_from".
        -Once a partner is created, (using odoo interface when posting message or when repplying to a mail), 
        the field partner_id is updated with the new partner 
        corresponding to email_from for every record having the same value for "email_from" and partner field not set. 
    """
    ALWAYS_STRATEGY, ON_REPLY_STRATEGY, NEVER_STRATEGY = range(3)
    _name = 'mail.partner.mixin'

    email_from = fields.Char('Email', help="Email address of the contact", index=True)
    email_cc = fields.Text('Global CC', help="Email adress added as cc of the first incoming mail of the record")
    partner_id = fields.Many2one('res.partner', string='Customer', track_visibility='onchange', index=True, help="Linked partner (optional).")

    def _partner_creation_strategy(self, msg):
        return self.ON_REPLY_STRATEGY

    def _emails_subscribe(self, msg):
        """
            Email to subscribe.
            A partner is create (only if _partner_creation_strategy() matched the case)
            Overwrite this method to add more email to subscribe. 
            email_from should be present in the list to allow partner auto update with emails
        """
        return [self.email_from]

    def _emails_subscribe_if_exists(self, msg):
        """
            Email to subscribe only if a partner exists
            Overwrite this method to add more partner to subscribe. 
        """
        return tools.email_split(msg.get('cc'))  # + [tools.email_split(self.email_cc)] ?

    def _message_partner_update_condition(self):
        """
        Additionnal condition to update the partner_id record. See _message_update_partner_id
        """
        return []  # example: ('stage_id.fold', '=', False)

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread new that is called by the mailgateway
            through process.
            This override adds the name, email_from, email_cc and partner_id to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(self.env.context or {})
        create_context['default_user_id'] = False
        if custom_values is None:
            custom_values = {}
        defaults = {
            self._rec_name: msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
        }
        defaults.update(custom_values)
        thread = super(MailPartnerMixin, self.with_context(create_context)).message_new(msg, custom_values=defaults)
        thread._partner_auto_subscribe(msg, isreply=False)
        return thread

    def message_update(self, msg, update_vals=None):
        """ Overrides mail_thread update that is called by the mailgateway through process.
            This override create and subscribe the partner partner_id if it doesnt exist based on the initial email_from
            Check if the reply is from an existing user, or the message wont be consider as an answer 
            in partner creation process
        """
        sender = msg.get('from')
        user = self.env['res.users'].sudo().search([('email', '=ilike', sender)], limit=1)
        self._partner_auto_subscribe(msg, isreply=bool(user))
        super(MailPartnerMixin, self).message_update(msg, update_vals)

    def _message_post_after_hook(self, message, values, notif_layout, notif_values):
        #Case after hook: a partner is created in odoo interface (front end side) when posting a message.
        #The partner id is added in the kwargs of message_post and will appear in "message.partner_ids"
        self._message_update_partner_id(message.partner_ids)
        return super(MailPartnerMixin, self)._message_post_after_hook(message, values, notif_layout, notif_values)

    def _partner_auto_subscribe(self, msg, isreply=False):
        """
            Subscribe some partners based on emails.
            -will subscribe and create partners if necessary for all emails in "_emails_subscribe"
            (depending of the strategy and isreply flag)
            -will subscribe all email contained in "_emails_subscribe_if_exists" if a corresponding partner exists
        """
        subscription_strategy = self._partner_creation_strategy(msg)
        def update_on_reply():
            return isreply and subscription_strategy == self.ON_REPLY_STRATEGY
        def update_always():
            return subscription_strategy == self.ALWAYS_STRATEGY

        allow_partner_creation = update_always() or update_on_reply()
        email_list = self._emails_subscribe(msg)
        partner_ids = [p for p in self._find_partner_from_emails(email_list, force_create=allow_partner_creation) if p]
        self.message_subscribe(partner_ids)
        #Case autosubscribe: a partner is created automaticaly when answering to an email
        self._message_update_partner_id(self.env['res.partner'].browse(partner_ids))
        partner_email_list = self._emails_subscribe_if_exists(msg)
        real_partner_ids = [p for p in self._find_partner_from_emails(partner_email_list, force_create=False) if p]
        self.message_subscribe(real_partner_ids)

    def _message_update_partner_id(self, new_partner_candidates):
        """
        Method call by _partner_auto_subscribe and _message_post_after_hook. 
        update the field partner_id if not set and te email is set. 
        Other condition can be added with _message_partner_update_conditions() (as search parameter)
        """
        if self.email_from and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            email_split = tools.email_split(self.email_from)
            if email_split:
                new_partner = new_partner_candidates.filtered(lambda partner: partner.email == email_split[0])
                if new_partner:
                    # update all the records using this email and without partner
                    self.search([
                        ("partner_id", '=', False),
                        ('email_from', '=', self.email_from)
                        ] + self._message_partner_update_condition()).write({"partner_id": new_partner.id})