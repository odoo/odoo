# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_tracking = fields.Selection(
        selection_add=[('membership', 'Membership / Partnership')], ondelete={'membership': 'set default'}
    )
    members_grade_id = fields.Many2one('res.partner.grade')
    members_pricelist_id = fields.Many2one('product.pricelist', groups='product.group_product_pricelist')
    membership_grade_label = fields.Char(compute='_compute_membership_labels')
    membership_pricelist_label = fields.Char(
        compute='_compute_membership_labels', groups="product.group_product_pricelist"
    )

    @api.model
    def _compute_membership_labels(self):
        if self.env['ir.config_parameter'].sudo().get_param('crm.membership_type') == 'Partner':
            self.membership_grade_label = self.env._("Partner Level")
            self.membership_pricelist_label = self.env._("Partner Pricelist")
        else:
            self.membership_grade_label = self.env._("Member Level")
            self.membership_pricelist_label = self.env._("Member Pricelist")
