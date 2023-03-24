# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MailPerformanceThread(models.Model):
    _name = 'mail.performance.thread'
    _description = 'Performance: mail.thread'
    _inherit = ['mail.thread']

    name = fields.Char()
    value = fields.Integer()
    value_pc = fields.Float(compute="_value_pc", store=True)
    track = fields.Char(default='test', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value_pc = float(record.value) / 100


class MailPerformanceTracking(models.Model):
    _name = 'mail.performance.tracking'
    _description = 'Performance: multi tracking'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    field_0 = fields.Char(tracking=True)
    field_1 = fields.Char(tracking=True)
    field_2 = fields.Char(tracking=True)


class MailTestFieldType(models.Model):
    """ Test default values, notably type, messing through models during gateway
    processing (i.e. lead.type versus attachment.type). """
    _description = 'Test Field Type'
    _name = 'mail.test.field.type'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    datetime = fields.Datetime(default=fields.Datetime.now)
    customer_id = fields.Many2one('res.partner', 'Customer')
    type = fields.Selection([('first', 'First'), ('second', 'Second')])
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Emulate an addon that alters the creation context, such as `crm`
        if not self._context.get('default_type'):
            self = self.with_context(default_type='first')
        return super(MailTestFieldType, self).create(vals_list)

    def _mail_get_partner_fields(self):
        return ['customer_id']


class MailTestLang(models.Model):
    """ A simple chatter model with lang-based capabilities, allowing to
    test translations. """
    _description = 'Lang Chatter Model'
    _name = 'mail.test.lang'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    customer_id = fields.Many2one('res.partner')
    lang = fields.Char('Lang')

    def _mail_get_partner_fields(self):
        return ['customer_id']

    def _notify_get_recipients_groups(self, msg_vals=None):
        groups = super(MailTestLang, self)._notify_get_recipients_groups(msg_vals=msg_vals)

        local_msg_vals = dict(msg_vals or {})

        for group in [g for g in groups if g[0] in('follower', 'customer')]:
            group_options = group[2]
            group_options['has_button_access'] = True
            group_options['actions'] = [
                {'url': self._notify_get_action_link('controller', controller='/test_mail/do_stuff', **local_msg_vals),
                 'title': _('NotificationButtonTitle')}
            ]
        return groups

# ------------------------------------------------------------
# TRACKING MODELS
# ------------------------------------------------------------

class MailTestTrackCompute(models.Model):
    _name = 'mail.test.track.compute'
    _description = "Test tracking with computed fields"
    _inherit = ['mail.thread']

    partner_id = fields.Many2one('res.partner', tracking=True)
    partner_name = fields.Char(related='partner_id.name', store=True, tracking=True)
    partner_email = fields.Char(related='partner_id.email', store=True, tracking=True)
    partner_phone = fields.Char(related='partner_id.phone', tracking=True)


class MailTestTrackMonetary(models.Model):
    _name = 'mail.test.track.monetary'
    _description = 'Test tracking monetary field'
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company')
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True, tracking=True)
    revenue = fields.Monetary('Revenue', currency_field='company_currency', tracking=True)


class MailTestSelectionTracking(models.Model):
    """ Test tracking for selection fields """
    _description = 'Test Selection Tracking'
    _name = 'mail.test.track.selection'
    _inherit = ['mail.thread']

    name = fields.Char()
    selection_type = fields.Selection([('first', 'First'), ('second', 'Second')], tracking=True)


class MailTestTrackAll(models.Model):
    _name = 'mail.test.track.all'
    _description = 'Test tracking on all field types'
    _inherit = ['mail.thread']

    boolean_field = fields.Boolean('Boolean', tracking=True)
    char_field = fields.Char('Char', tracking=True)
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    date_field = fields.Date('Date', tracking=True)
    datetime_field = fields.Datetime('Datetime', tracking=True)
    float_field = fields.Float('Float', tracking=True)
    html_field = fields.Html('Html', tracking=True)
    integer_field = fields.Integer('Integer', tracking=True)
    many2one_field_id = fields.Many2one('res.partner', string='Many2one', tracking=True)
    monetary_field = fields.Monetary('Monetary', tracking=True)
    selection_field = fields.Selection(string='Selection', selection=[['first', 'FIRST']], tracking=True)
    text_field = fields.Text('Text', tracking=True)

# ------------------------------------------------------------
# OTHER
# ------------------------------------------------------------

class MailTestMultiCompany(models.Model):
    """ This model can be used in multi company tests"""
    _name = 'mail.test.multi.company'
    _description = "Test Multi Company Mail"
    _inherit = 'mail.thread'

    name = fields.Char()
    company_id = fields.Many2one('res.company')


class MailTestMultiCompanyRead(models.Model):
    """ Just mail.test.simple, but multi company and supporting posting
    even if the user has no write access. """
    _description = 'Simple Chatter Model '
    _name = 'mail.test.multi.company.read'
    _inherit = ['mail.test.multi.company']
    _mail_post_access = 'read'


class MailTestNotMailThread(models.Model):
    """ Models not inheriting from mail.thread but using some cross models
    capabilities of mail. """
    _name = 'mail.test.nothread'
    _description = "NoThread Model"

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    customer_id = fields.Many2one('res.partner')
