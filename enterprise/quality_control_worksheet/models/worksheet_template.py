# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class WorksheetTemplate(models.Model):
    _inherit = 'worksheet.template'

    @api.model
    def _default_quality_check_template_fields(self):
        return [
            (0, 0, {
                'name': 'x_passed',
                'ttype': 'boolean',
                'field_description': 'Passed',
            })
        ]

    @api.model
    def _default_quality_check_worksheet_form_arch(self):
        return """
            <form create="false" js_class="worksheet_validation">
                <sheet>
                    <h1 invisible="context.get('studio') or context.get('default_x_quality_check_id')">
                        <field name="x_quality_check_id" domain="[('test_type', '=', 'worksheet')]"/>
                    </h1>
                    <group>
                        <group>
                            <field name="x_comments"/>
                            <field name="x_passed"/>
                        </group>
                        <group>
                        </group>
                    </group>
                </sheet>
            </form>
        """

    @api.model
    def _get_quality_check_user_group(self):
        return self.env.ref('quality.group_quality_user')

    @api.model
    def _get_quality_check_manager_group(self):
        return self.env.ref('quality.group_quality_manager')

    @api.model
    def _get_quality_check_access_all_groups(self):
        return self.env.ref('quality.group_quality_manager')

    @api.model
    def _get_quality_check_module_name(self):
        return 'quality_control_worksheet'

    @api.model
    def _get_models_to_check_dict(self):
        res = super()._get_models_to_check_dict()
        res['quality.check'] = [('quality.check', 'Quality Check'), ('quality.point', 'Quality Point')]
        return res

    @api.model
    def _create_demo_data_quality(self):
        # create demo data in batch for performance reasons (avoid multiple calls to setup_models)
        model_id = self.env.ref('quality_control_worksheet.quality_control_worksheet_template1').model_id.id
        self.env['ir.model.fields'].create([{
            'name': 'x_date',
            'ttype': 'date',
            'field_description': 'Date',
            'model_id': model_id,
        }, {
            'name': 'x_product',
            'ttype': 'many2one',
            'relation': 'product.product',
            'field_description': 'Product',
            'model_id': model_id,
        }, {
            'name': 'x_responsible',
            'ttype': 'many2one',
            'relation': 'res.users',
            'field_description': 'Responsible',
            'model_id': model_id,
        }, {
            'name': 'x_texture',
            'ttype': 'selection',
            'field_description': 'Wood Texture',
            'selection': "[('rough','Rough'),('smooth','Smooth')]",
            'model_id': model_id,
        }, {
            'name': 'x_length',
            'ttype': 'selection',
            'field_description': 'Length',
            'selection': "[('short','1.80m ~ 1.85m'), ('medium','1.86m ~ 1.90m'), ('long', '1.91m ~ 2.00m')]",
            'model_id': model_id,
        }])

    def get_x_model_form_action(self):
        action = super().get_x_model_form_action()
        if self.res_model == 'quality.check':
            action['context'].update({
                'action_xml_id': 'quality_control_worksheet.quality_control_worksheet_template_action_settings',
                'worksheet_template_id': self.id,
            })
        return action
