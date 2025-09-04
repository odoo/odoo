from odoo import api, fields, models
from odoo.fields import Domain

# ------------------------------------------------------------
# RECIPIENTS
# ------------------------------------------------------------


class MailTestRecipients(models.Model):
    _name = 'mail.test.recipients'
    _description = "Test Recipients Computation"
    _inherit = ['mail.thread.cc']
    _primary_email = 'customer_email'

    company_id = fields.Many2one('res.company')
    contact_ids = fields.Many2many('res.partner')
    customer_id = fields.Many2one('res.partner')
    customer_email = fields.Char('Customer Email', compute='_compute_customer_email', readonly=False, store=True)
    customer_phone = fields.Char('Customer Phone', compute='_compute_customer_phone', readonly=False, store=True)
    name = fields.Char()

    @api.depends('customer_id')
    def _compute_customer_email(self):
        for source in self.filtered(lambda r: r.customer_id and not r.customer_email):
            source.customer_email = source.customer_id.email_formatted

    @api.depends('customer_id')
    def _compute_customer_phone(self):
        for source in self.filtered(lambda r: r.customer_id and not r.customer_phone):
            source.customer_phone = source.customer_id.phone

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id', 'contact_ids']


class MailTestThreadCustomer(models.Model):
    _name = 'mail.test.thread.customer'
    _description = "Test Customer Thread Model"
    _inherit = ['mail.test.recipients']
    _mail_thread_customer = True
    _primary_email = 'customer_email'

# ------------------------------------------------------------
# PROPERTIES
# ------------------------------------------------------------


class MailTestProperties(models.Model):
    _name = 'mail.test.properties'
    _description = 'Mail Test Properties'
    _inherit = ['mail.thread']

    name = fields.Char('Name')
    parent_id = fields.Many2one('mail.test.properties', string='Parent')
    properties = fields.Properties('Properties', definition='parent_id.definition_properties')
    definition_properties = fields.PropertiesDefinition('Definitions')

# ------------------------------------------------------------
# ROTTING RESOURCES
# ------------------------------------------------------------


class MailTestStageField(models.Model):
    _description = 'Fake model to be a stage to help test rotting implementation'
    _name = 'mail.test.rotting.stage'

    name = fields.Char()
    rotting_threshold_days = fields.Integer(default=3)
    no_rot = fields.Boolean(default=False)


class MailTestRottingMixin(models.Model):
    _description = 'Fake model to test the rotting part of the mixin mail.thread.tracking.duration.mixin'
    _name = 'mail.test.rotting.resource'
    _track_duration_field = 'stage_id'
    _inherit = ['mail.tracking.duration.mixin']

    name = fields.Char()
    date_last_stage_update = fields.Datetime(
        'Last Stage Update', compute='_compute_date_last_stage_update', index=True, readonly=True, store=True)
    stage_id = fields.Many2one('mail.test.rotting.stage', 'Stage')
    done = fields.Boolean(default=False)

    def _get_rotting_depends_fields(self):
        return super()._get_rotting_depends_fields() + ['done', 'stage_id.no_rot']

    def _get_rotting_domain(self):
        return super()._get_rotting_domain() & Domain([
            ('done', '=', False),
            ('stage_id.no_rot', '=', False),
        ])

    @api.depends('stage_id')
    def _compute_date_last_stage_update(self):
        self.date_last_stage_update = fields.Datetime.now()
