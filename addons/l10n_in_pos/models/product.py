# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_in_hsn_missing_in_pos = fields.Boolean(
        search="_search_l10n_in_hsn_missing_in_pos",
        store=False,
        string="HSN Missing in POS",
    )

    def _search_l10n_in_hsn_missing_in_pos(self, operator, value):
        if operator not in ("=", "!="):
            return NotImplemented

        domain = [
            ("order_id.session_id.state", "!=", "closed"),
            ("order_id.account_move", "=", False),
            ("product_id.product_tmpl_id.l10n_in_hsn_code", "=", False),
            ("product_id.product_tmpl_id.taxes_id", "!=", False),
        ]
        grouped_data = self.env["pos.order.line"]._read_group(
            domain,
            aggregates=["__count"],
            groupby=["product_id"],
        )

        product_ids = [row[0].id for row in grouped_data]
        positive = (operator == "=" and value) or (operator == "!=" and not value)

        return [("id", "in" if positive else "not in", product_ids)]

    @api.model
    def l10n_in_get_hsn_code_action(self):
        """
        Returns the action to open the HSN code dialog with the given products.
        FIXME: This method dynamically creates a view at runtime.
        FIXME: Remove this method and the dynamic view in master.
        """

        action_xml_id = 'l10n_in_pos.action_missing_hsn_product'
        action = self.env.ref(action_xml_id, False)
        if not action:
            action = self.env['ir.actions.act_window'].sudo().create({
                'name': 'Missing HSN Products',
                'type': 'ir.actions.act_window',
                'res_model': 'product.product',
                'view_mode': 'kanban,list,form',
                'domain': [
                    ('l10n_in_hsn_missing_in_pos', '=', True)
                ],
                'help': """
                    <p class="o_view_nocontent_smiling_face">
                        Create a new product variant
                    </p>
                    <p>
                        You must define an HSN for every product you sell through
                        the point of sale interface.
                    </p>
                """,
            })
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': action_xml_id,
                'record': action,
            }])

        return action_xml_id
