# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        if self.env.company.country_id.code == 'IN':
            fields += ['l10n_in_hsn_code']
        return fields

    @api.model
    def l10n_in_get_hsn_code_action(self, product_ids):
        """
        Returns the action to open the HSN code dialog with the given products.
        FIXME: This method dynamically creates a view at runtime.
        FIXME: Remove this method and the dynamic view in master.
        """

        xml_id = 'l10n_in_pos.product_tree_hsn_code'
        list_view = self.env.ref('l10n_in_pos.product_tree_hsn_code', False)
        if not list_view:
            list_view = self.env['ir.ui.view'].sudo().create([
                {
                    'name': 'l10n_in_pos.product_tree_hsn_code',
                    'type': 'list',
                    'model': 'product.template',
                    'arch_db': """<list string="Product" multi_edit="1" editable="top" sample="1">
                                    <field name="name" readonly="1"/>
                                     <field name="l10n_in_hsn_code"/>
                                  </list>""",
                }
            ])
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': xml_id,
                'record': list_view,
            }])

        action_xml_id = 'l10n_in_pos.action_missing_hsn_product'
        action = self.env.ref(action_xml_id, False)
        if not action:
            action = self.env['ir.actions.act_window'].sudo().create({
                'name': 'Missing HSN Products',
                'res_model': 'product.template',
                'view_mode': 'list',
                'view_id': list_view.id,
            })
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': action_xml_id,
                'record': action,
            }])
        action.write({
            'domain': [('id', 'in', product_ids)],
        })

        return action_xml_id
