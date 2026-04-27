# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_mx_address_issued_id = fields.Many2one(
        comodel_name='res.partner',
        domain="[('type', '=', 'invoice')]",
        string="Address Issued",
        help="Used in multiple-offices environments to fill, with the given address, the node 'ExpedidoEn' in the XML "
             "for invoices of this journal. If empty, the node won't be added.")
