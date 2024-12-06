# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_pk_edi_sale_type_id = fields.Many2one('l10n.pk.product.type', 'Sale Type',
        compute='_compute_l10n_pk_edi_sale_type', readonly=False, store=True,
    )
    l10n_pk_edi_schedule_code_id = fields.Many2one('l10n.pk.schedule.code', 'Schedule Code',
        compute='_compute_l10n_pk_edi_schedule_code', readonly=False, store=True,
    )

    @api.depends('type')
    def _compute_l10n_pk_edi_sale_type(self):
        def _get_pk_sale_type(sale_type):
            return {
               'consu': 'T1000017',
               'service': 'T1000018',
            }.get(sale_type, 'T1000083')  # Otherwise, default to 'T1000083' which represent 'Other'
        for line in self:
            line.l10n_pk_edi_sale_type_id = self.env['l10n.pk.product.type'].search(
                [('sale_type', '=', _get_pk_sale_type(line.type))],
                limit=1
            )

    @api.depends('type')
    def _compute_l10n_pk_edi_schedule_code(self):
        schedule_code = self.env['l10n.pk.schedule.code'].search([('schedule_code', '=', "S1000012")])
        for line in self:
            line.l10n_pk_edi_schedule_code_id = schedule_code
