from odoo import api, fields, models

# ------------------------------------------------------------
# RECIPIENTS
# ------------------------------------------------------------


class MailTestRecipients(models.Model):
    _name = 'mail.test.recipients'
    _description = "Test Recipients Computation"
    _inherit = ['mail.thread']
    _primary_email = 'customer_email'

    company_id = fields.Many2one('res.company')
    contact_ids = fields.Many2many('res.partner')
    customer_id = fields.Many2one('res.partner')
    customer_email = fields.Char('Customer Email', compute='_compute_customer_email', readonly=False, store=True)
    customer_phone = fields.Char('Customer Phone', compute='_compute_customer_phone', readonly=False, store=True)
    email_cc = fields.Char('Email CC')
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
