# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ActivityReport(models.Model):
    """ sale Activity Analysis """

    _name = "sale.activity.report"
    _auto = False
    _description = "Sale Activity Analysis"
    _rec_name = 'id'

    date = fields.Datetime('Date', readonly=True)
    create_uid = fields.Many2one('res.users', 'Created By', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Channel', readonly=True)
    order_id = fields.Many2one('sale.order', "Order", readonly=True)
    subject = fields.Char('Summary', readonly=True)
    subtype_id = fields.Many2one('mail.message.subtype', 'Subtype', readonly=True)
    mail_activity_type_id = fields.Many2one('mail.activity.type', 'Activity Type', readonly=True)
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status')
    partner_id = fields.Many2one('res.partner', 'Partner/Customer', readonly=True)

    def _select(self):
        return """
            SELECT
                m.id,
                m.subtype_id,
                m.mail_activity_type_id,
                m.create_uid,
                m.date,
                m.subject,
                so.id as order_id,
                so.user_id,
                so.team_id,
                partner.country_id,
                so.company_id,
                so.state,
                so.partner_id
        """

    def _from(self):
        return """
            FROM mail_message AS m
        """

    def _join(self):
        return """
            JOIN sale_order AS so ON m.res_id = so.id
            JOIN res_partner AS partner ON so.partner_id = partner.id
        """

    def _where(self):
        return """
            WHERE
                m.model = 'sale.order' AND m.mail_activity_type_id IS NOT NULL
        """

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._join(), self._where())
        )
