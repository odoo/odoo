# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    country_id = fields.Many2one('res.country', string="Country", related='company_id.country_id')
    country_code = fields.Char(related='country_id.code', depends=['country_id'], readonly=True)
    l10n_pt_pos_tax_authority_series_id = fields.Many2one("l10n_pt.tax.authority.series", string="Official Series of the Tax Authority")

    def open_ui(self):
        if not self.company_id.country_id:
            raise UserError(_("You have to set a country in your company setting."))
        if self.company_id.country_id.code == 'PT' and not self.l10n_pt_pos_tax_authority_series_id:
            raise UserError(_("You have to set a official Tax Authority Series in the POS configuration settings"))
        return super().open_ui()

    def write(self, vals):
        res = super().write(vals)
        for config in self:
            if vals.get('l10n_pt_pos_tax_authority_series_id') and config.l10n_pt_pos_tax_authority_series_id:
                if self.env['pos.order'].search_count([('config_id', '=', config.id)]):
                    raise UserError(_("You cannot change the official series of a journal once it has been used."))
        return res

