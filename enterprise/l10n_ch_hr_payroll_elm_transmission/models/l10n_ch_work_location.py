# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class L10nChWorkLocation(models.Model):
    _inherit = 'l10n.ch.location.unit'

    active = fields.Boolean(default=True)
    in_house_id = fields.Char(string="InHouseID")
    bur_ree_number = fields.Char(required=False)
    dpi_number = fields.Char(required=False)
    canton = fields.Selection(required=False, compute="_compute_autocomplete_canton_municipality", store=True, readonly=False)
    municipality = fields.Char(required=False, compute="_compute_autocomplete_canton_municipality", store=True, readonly=False)

    @api.depends("partner_id.zip")
    def _compute_autocomplete_canton_municipality(self):
        ZIP_DATA = self.env['hr.rule.parameter']._get_parameter_from_code("l10n_ch_bfs_municipalities", fields.Date.today(), raise_if_not_found=False)
        if ZIP_DATA:
            for record in self:
                if record.partner_id.zip:
                    data = ZIP_DATA.get(record.partner_id.zip)
                    if data:
                        record.municipality = data[1]
                        record.canton = data[2]
