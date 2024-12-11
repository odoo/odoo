# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_pk_edi_pos_key = fields.Char("PoS Key(FBR)", groups="base.group_system")
