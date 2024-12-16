from odoo import api, fields, models, _


class MailTestSimple(models.Model):
    """ A very simple model only inheriting from mail.thread when only
    communication history is necessary. """
    _description = 'Simple Chatter Model'
    _name = "mail.test.simple"
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()

    def _message_compute_subject(self):
        """ To ease mocks """
        _a = super()._message_compute_subject()
        return _a

    def _notify_by_email_get_final_mail_values(self, *args, **kwargs):
        """ To ease mocks """
        _a = super()._notify_by_email_get_final_mail_values(*args, **kwargs)
        return _a

    def _notify_by_email_get_headers(self, headers=None):
        headers = super()._notify_by_email_get_headers(headers=headers)
        headers['X-Custom'] = 'Done'
        return headers

class MailTestSimpleUnnamed(models.Model):
    """ A very simple model only inheriting from mail.thread when only
    communication history is necessary, and has no 'name' field """
    _description = 'Simple Chatter Model without "name" field'
    _name = 'mail.test.simple.unnamed'
    _inherit = ['mail.thread']
    _rec_name = "description"

    description = fields.Char()

class MailTestSimpleMainAttachment(models.Model):
    _description = 'Simple Chatter Model With Main Attachment Management'
    _name = "mail.test.simple.main.attachment"
    _inherit = ['mail.test.simple', 'mail.thread.main.attachment']


class MailTestSimpleUnfollow(models.Model):
    """ A very simple model only inheriting from mail.thread when only
    communication history is necessary with unfollow link enabled in
    notification emails even for non-internal user. """
    _description = 'Simple Chatter Model'
    _name = "mail.test.simple.unfollow"
    _inherit = ['mail.thread']
    _partner_unfollow_enabled = True

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    email_from = fields.Char()


class MailTestAliasOptional(models.Model):
    """ A chatter model inheriting from the alias mixin using optional alias_id
    field, hence no inherits. """
    _description = 'Chatter Model using Optional Alias Mixin'
    _name = "mail.test.alias.optional"
    _inherit = ['mail.alias.mixin.optional']

    name = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    email_from = fields.Char()

    def _alias_get_creation_values(self):
        """ Updates itself """
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get_id('mail.test.alias.optional')
        if self.id:
            values['alias_force_thread_id'] = self.id
            values['alias_defaults'] = {'company_id': self.company_id.id}
        return values


class MailTestGateway(models.Model):
    """ A very simple model only inheriting from mail.thread to test pure mass
    mailing features and base performances. """
    _description = 'Simple Chatter Model for Mail Gateway'
    _name = "mail.test.gateway"
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    custom_field = fields.Char()

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Check override of 'message_new' allowing to update record values
        base on incoming email. """
        defaults = {
            'email_from': msg_dict.get('from'),
        }
        defaults.update(custom_values or {})
        return super().message_new(msg_dict, custom_values=defaults)


class MailTestGatewayCompany(models.Model):
    """ A very simple model only inheriting from mail.thread to test pure mass
    mailing features and base performances, with a company field. """
    _description = 'Simple Chatter Model for Mail Gateway with company'
    _name = "mail.test.gateway.company"
    _inherit = ['mail.test.gateway']

    company_id = fields.Many2one('res.company', 'Company')


class MailTestGatewayMainAttachment(models.Model):
    """ A very simple model only inheriting from mail.thread to test pure mass
    mailing features and base performances, with a company field and main
    attachment management. """
    _description = 'Simple Chatter Model for Mail Gateway with company'
    _name = "mail.test.gateway.main.attachment"
    _inherit = ['mail.test.gateway', 'mail.thread.main.attachment']

    company_id = fields.Many2one('res.company', 'Company')


class MailTestGatewayGroups(models.Model):
    """ A model looking like discussion channels / groups (flat thread and
    alias). Used notably for advanced gatewxay tests. """
    _description = 'Channel/Group-like Chatter Model for Mail Gateway'
    _name = "mail.test.gateway.groups"
    _inherit = ['mail.thread.blacklist', 'mail.alias.mixin']
    _mail_flat_thread = False
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    custom_field = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')

    def _alias_get_creation_values(self):
        values = super(MailTestGatewayGroups, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.test.gateway.groups').id
        if self.id:
            values['alias_force_thread_id'] = self.id
            values['alias_parent_thread_id'] = self.id
        return values

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']

    def _message_get_default_recipients(self):
        return dict(
            (record.id, {
                'email_cc': False,
                'email_to': record.email_from if not record.customer_id.ids else False,
                'partner_ids': record.customer_id.ids,
            })
            for record in self
        )


class MailTestTrack(models.Model):
    """ This model can be used in tests when automatic subscription and simple
    tracking is necessary. Most features are present in a simple way. """
    _description = 'Standard Chatter Model'
    _name = "mail.test.track"
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)
    container_id = fields.Many2one('mail.test.container', tracking=True)
    company_id = fields.Many2one('res.company')
    track_fields_tofilter = fields.Char()  # comma-separated list of field names
    track_enable_default_log = fields.Boolean(default=False)

    def _track_filter_for_display(self, tracking_values):
        values = super()._track_filter_for_display(tracking_values)
        filtered_fields = set(self.track_fields_tofilter.split(',') if self.track_fields_tofilter else '')
        return values.filtered(lambda val: val.field_id.name not in filtered_fields)

    def _track_get_default_log_message(self, changes):
        filtered_fields = set(self.track_fields_tofilter.split(',') if self.track_fields_tofilter else '')
        if self.track_enable_default_log and not all(change in filtered_fields for change in changes):
            return f'There was a change on {self.name} for fields "{",".join(changes)}"'
        return super()._track_get_default_log_message(changes)


class MailTestActivity(models.Model):
    """ This model can be used to test activities in addition to simple chatter
    features. """
    _description = 'Activity Model'
    _name = "mail.test.activity"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    date = fields.Date()
    email_from = fields.Char()
    active = fields.Boolean(default=True)

    def action_start(self, action_summary):
        return self.activity_schedule(
            'test_mail.mail_act_test_todo',
            summary=action_summary
        )

    def action_close(self, action_feedback, attachment_ids=None):
        self.activity_feedback(['test_mail.mail_act_test_todo'],
                               feedback=action_feedback,
                               attachment_ids=attachment_ids)


class MailTestComposerMixin(models.Model):
    """ A simple invite-like wizard using the composer mixin, rendering on
    composer source test model. Purpose is to have a minimal composer which
    runs on other records and check notably dynamic template support and
    translations. """
    _description = 'Invite-like Wizard'
    _name = "mail.test.composer.mixin"
    _inherit = ['mail.composer.mixin']

    name = fields.Char('Name')
    author_id = fields.Many2one('res.partner')
    description = fields.Html('Description', render_engine="qweb", render_options={"post_process": True}, sanitize='email_outgoing')
    source_ids = fields.Many2many('mail.test.composer.source', string='Invite source')

    def _compute_render_model(self):
        self.render_model = 'mail.test.composer.source'


class MailTestComposerSource(models.Model):
    """ A simple model on which invites are sent. """
    _description = 'Invite-like Source'
    _name = "mail.test.composer.source"
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char('Name')
    customer_id = fields.Many2one('res.partner', 'Main customer')
    email_from = fields.Char(
        'Email',
        compute='_compute_email_from', readonly=False, store=True)

    @api.depends('customer_id')
    def _compute_email_from(self):
        for source in self.filtered(lambda r: r.customer_id and not r.email_from):
            source.email_from = source.customer_id.email_formatted

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']
