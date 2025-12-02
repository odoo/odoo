# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class Uom(models.Model):
    _inherit = "uom.uom"

    l10n_id_uom_code = fields.Many2one("l10n_id_efaktur_coretax.uom.code", string="E-Faktur UoM code")
