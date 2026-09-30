# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    snailmail_color = fields.Boolean(string='Print In Color', related='company_id.snailmail_color', readonly=False)
    snailmail_cover = fields.Boolean(string='Add a Cover Page', related='company_id.snailmail_cover', readonly=False)
    snailmail_duplex = fields.Boolean(string='Print Both sides', related='company_id.snailmail_duplex', readonly=False)

    snailmail_cover_readonly = fields.Boolean(compute="_compute_cover_readonly")

    def _is_layout_cover_required(self):
        return self.external_report_layout_id in {
            self.env.ref(f'web.external_layout_{layout}')
            for layout in ('boxed', 'bold', 'striped')
        }

    @api.onchange('external_report_layout_id')
    def _onchange_layout(self):
        for record in self:
            if record._is_layout_cover_required():
                record.company_id.snailmail_cover = True

    @api.depends('external_report_layout_id')
    def _compute_cover_readonly(self):
        for record in self:
            record.snailmail_cover_readonly = self._is_layout_cover_required()
