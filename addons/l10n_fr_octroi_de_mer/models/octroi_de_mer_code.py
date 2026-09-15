from odoo import api, fields, models


class OctroiDeMerCode(models.Model):
    _name = 'l10n_fr.octroi.de.mer.code'
    _description = "Octroi de Mer Code"

    code = fields.Char(string="Border reference")
    description = fields.Char()
    om_rate = fields.Many2one(comodel_name='account.tax', string="Octroi de Mer")
    omr_rate = fields.Many2one(comodel_name='account.tax', string="Octroi de Mer Regional")
