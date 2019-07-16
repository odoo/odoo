# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    l10n_latam_identification_type_id = fields.Many2one(
        related='partner_id.l10n_latam_identification_type_id',
        readonly=True,
    )
    l10n_cl_rut = fields.Char(
        related='partner_id.l10n_cl_rut',
        readonly=True
    )
    l10n_cl_rut_dv = fields.Char(
        related='partner_id.l10n_cl_rut_dv',
        readonly=True
    )
    l10n_cl_county_id = fields.Many2one(
        "l10n_cl.county", 'County')

    @api.onchange('l10n_cl_county_id', 'city', 'state_id')
    def _change_city_province(self):
        if self.country_id != self.env.ref('base.cl'):
            return
        self.state_id = self.l10n_cl_county_id.state_id.parent_id
        if self.state_id == self.env.ref('l10n_cl_base.CL13'):
            self.city = 'Santiago'
        else:
            self.city = self.l10n_cl_county_id.name

    @api.multi
    def validate_rut(self):
        return self.partner_id.validate_rut()
