# coding: utf-8

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_mx_edi_addenda = fields.Many2one('edi.mx.addenda',
        string='Addenda XML',
        help='The XML to append at the MX EDI document')