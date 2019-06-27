# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SmsStatistics(models.Model):
    """ SMS statistics models the statistics collected about sms sent in mass
    sms. Those statistics are stored in a separated model and table to avoid
    bloating the sms_sms table with statistics values, especially that sent
    sms are removed. """
    _name = 'sms.statistics'
    _description = 'SMS Statistics'
    _rec_name = 'sms_sms_id_int'
    _order = 'sms_sms_id_int'

    sms_sms_id = fields.Many2one('sms.sms', string='Mail', index=True, ondelete='set null')
    sms_sms_id_int = fields.Integer(
        string='SMS ID (tech)',
        help='ID of the related sms.sms. This field is an integer field because '
             'the related sms.sms can be deleted separately from its statistics. '
             'However the ID is needed for several action and controllers.',
        index=True,
    )
    sms_number = fields.Char('Number')
    # document
    res_model = fields.Char(string='Document model')
    res_id = fields.Integer(string='Document ID')
    # marketing
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing', index=True)
    utm_campaign_id = fields.Many2one('utm.campaign', string='Marketing Campaign', index=True)
    links_click_ids = fields.One2many('link.tracker.click', 'sms_statistics_id', string='Links click')
    # statistics
    # created = fields.Datetime(help='Date when the email has been created', default=fields.Datetime.now)
    sent = fields.Datetime(help='Date when the sms has been sent')
    clicked = fields.Datetime(help='Date when customer clicked on at least one tracked link')
    ignored = fields.Datetime(help='Date when the email has been invalidated, because of blacklist or wrong number')
    exception = fields.Datetime(help='Date of technical error leading to the sms not being sent')
    state = fields.Selection(
        compute="_compute_state", selection=[
            ('outgoing', 'Outgoing'), ('exception', 'Exception'),
            ('sent', 'Sent'), ('opened', 'Opened/Clicked'), ('ignored', 'Ignored')
        ], store=True)

    @api.depends('sent', 'ignored', 'exception', 'clicked')
    def _compute_state(self):
        for stat in self:
            if stat.ignored:
                stat.state = 'ignored'
            elif stat.exception:
                stat.state = 'exception'
            elif stat.clicked:
                stat.state = 'opened'
            elif stat.sent:
                stat.state = 'sent'
            else:
                stat.state = 'outgoing'

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if 'sms_sms_id' in values:
                values['sms_sms_id_int'] = values['sms_sms_id']
        return super(SmsStatistics, self).create(values_list)

    def _get_records(self, sms_sms_ids=None, domain=None):
        if not self.ids and sms_sms_ids:
            base_domain = [('sms_sms_id_int', 'in', sms_sms_ids)]
        else:
            base_domain = [('id', 'in', self.ids)]
        if domain:
            base_domain = ['&'] + domain + base_domain
        return self.search(base_domain)

    def set_sent(self, sms_sms_ids=None):
        statistics = self._get_records(sms_sms_ids, [('sent', '=', False)])
        statistics.write({'sent': fields.Datetime.now()})
        return statistics

    def set_clicked(self, sms_sms_ids=None):
        statistics = self._get_records(sms_sms_ids, [('clicked', '=', False)])
        statistics.write({'clicked': fields.Datetime.now()})
        return statistics

    def set_ignored(self, sms_sms_ids=None):
        statistics = self._get_records(sms_sms_ids, [('ignored', '=', False)])
        statistics.write({'ignored': fields.Datetime.now()})
        return statistics
