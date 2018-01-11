# -*- coding: utf-8 -*-


from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    transport_mode_id = fields.Many2one('account.intrastat.transport', string='Intrastat Transport Mode')
    intrastat_country_id = fields.Many2one('res.country', string='Intrastat Country',
        help='Intrastat country, delivery for sales, origin for purchases',
        domain=[('intrastat', '=', True)])


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    intrastat_transaction_id = fields.Many2one('account.intrastat.transaction', string='Intrastat Transaction Type',
        help='Intrastat nature of transaction')
