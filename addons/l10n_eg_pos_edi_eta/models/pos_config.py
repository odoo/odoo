from odoo import fields, models


class NewModule(models.Model):
    _inherit = 'pos.config'

    country_code = fields.Char(related="company_id.country_id.code")

    l10n_eg_pos_serial = fields.Char("POS Serial")
    l10n_eg_pos_version = fields.Char("POS Version")
    l10n_eg_pos_model_framework = fields.Char("POS Model Framework")
    l10n_eg_pos_pre_shared_key = fields.Char("POS Pre-Shared Key")