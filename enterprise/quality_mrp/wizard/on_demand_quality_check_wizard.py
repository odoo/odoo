# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QualityCheckOnDemand(models.TransientModel):
    _inherit = 'quality.check.on.demand'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order')

    @api.depends('production_id')
    def _compute_allowed_product_ids(self):
        for wizard in self:
            if wizard.production_id:
                wizard.allowed_product_ids = wizard.production_id.product_id | wizard.production_id.move_byproduct_ids.product_id
        super(QualityCheckOnDemand, self.filtered(lambda w: not w.production_id))._compute_allowed_product_ids()

    @api.depends('production_id', 'product_id')
    def _compute_allowed_quality_point_ids(self):
        for wizard in self:
            if wizard.production_id:
                domain = self.env['quality.point']._get_domain(wizard.product_id, self.production_id.picking_type_id, on_demand=True)
                wizard.allowed_quality_point_ids = self.env['quality.point'].search(domain)
        super(QualityCheckOnDemand, self.filtered(lambda w: not w.production_id))._compute_allowed_quality_point_ids()

    @api.depends('product_id', 'quality_point_id')
    def _compute_show_lot_number(self):
        for wizard in self:
            if wizard.production_id:
                wizard.show_lot_number = False
        super(QualityCheckOnDemand, self.filtered(lambda w: not w.production_id))._compute_show_lot_number()

    def action_confirm(self):
        self.ensure_one()
        if self.production_id and self.production_id.state in ['draft', 'done', 'cancel']:
            raise UserError(_('You can not create quality check for a draft, done or cancelled manufacturing order.'))
        super().action_confirm()

    def _get_check_values(self):
        check_values = super()._get_check_values()
        for check in check_values:
            check['production_id'] = self.production_id.id
        return check_values
