# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _is_project_milestone_feature_enabled(self):
        """ Return whether the milestones feature is currently granted in database,
            the way `default_get` computes the `group_project_milestone` field.
        """
        _name, groups, implied_group = self._get_classified_fields(['group_project_milestone'])['group'][0]
        return all(implied_group in group.implied_ids for group in groups)

    def set_values(self):
        milestone_feature_was_enabled = self._is_project_milestone_feature_enabled()
        super().set_values()
        if self.group_project_milestone == milestone_feature_was_enabled:
            # `set_values` runs on every save of the settings, whatever section was
            # edited. The conversions below are one-shot migrations between the
            # manual and the milestone service policies, so they must only run when
            # the feature is actually toggled: otherwise any unrelated settings save
            # silently rewrites the invoicing policy of every product sold on a line
            # linked to a milestone.
            return
        if self.group_project_milestone:
            # Search the milestones containing a SOL and change the qty_delivered_method field of the SOL and the
            # service_policy field set on the product to convert from manual to milestones.
            milestone_read_group = self.env['project.milestone'].read_group(
                [('sale_line_id', '!=', False)],
                ['sale_line_ids:array_agg(sale_line_id)'],
                [],
            )
            sale_line_ids = milestone_read_group[0]['sale_line_ids'] if milestone_read_group else []
            sale_lines = self.env['sale.order.line'].sudo().browse(sale_line_ids)
            # Only the products following the manual policy are converted: a product
            # invoiced on ordered quantities or on timesheets is a deliberate
            # configuration that enabling the feature must not overwrite.
            sale_lines.product_id.filtered(
                lambda product: product.service_policy == 'delivered_manual'
            ).service_policy = 'delivered_milestones'
        else:
            product_domain = [('type', '=', 'service'), ('service_type', '=', 'milestones')]
            products = self.env['product.product'].search(product_domain)
            products.service_policy = 'delivered_manual'
            self.env['sale.order.line'].sudo().search([('product_id', 'in', products.ids)]).qty_delivered_method = 'manual'
