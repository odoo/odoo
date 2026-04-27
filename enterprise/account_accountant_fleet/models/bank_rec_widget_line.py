# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BankRecWidgetLine(models.Model):
    _inherit = 'bank.rec.widget.line'

    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        compute='_compute_vehicle_id',
        store=True,
        readonly=False,
        domain="[('company_id', '=', company_id)]"
    )
    vehicle_required = fields.Boolean(
        compute='_compute_vehicle_required',
    )

    @api.depends('source_aml_id')
    def _compute_vehicle_id(self):
        for line in self:
            if line.flag == 'aml':
                line.vehicle_id = line.source_aml_id.vehicle_id
            else:
                line.vehicle_id = line.vehicle_id

    def _compute_vehicle_required(self):
        self.vehicle_required = False

    def _get_aml_values(self, **kwargs):
        # EXTENDS account_accountant
        return super()._get_aml_values(
            **kwargs,
            vehicle_id=self.vehicle_id.id,
        )
