# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests.common import tagged


@tagged('mailing_templates')
@tagged('at_install', '-post_install')
class TestMailingTemplates(MassMailCommon):

    def test_template_use_this(self):
        # Prepare
        mailing_template = self.env['mailing.mailing'].with_context(
            some_attribute="attribute value"
        ).create([
            {
                "subject": "First template",
                "is_template": True,
            },
        ])

        # Execute
        res_action = mailing_template.action_use_template()
        created_mailing_id = res_action['res_id']

        # Assert
        self.assertEqual("attribute value", res_action['context']['some_attribute'])
        self.assertEqual(False, res_action['context']['default_is_template'])
        self.assertEqual(False, res_action['context']['default_favorite'])
        self.assertEqual(2, self.env['mailing.mailing'].search_count([]))
        self.assertEqual(False, self.env['mailing.mailing'].search([('id', '=', created_mailing_id)]).favorite)
        self.assertEqual(False, self.env['mailing.mailing'].search([('id', '=', created_mailing_id)]).is_template)

    def test_template_duplicate(self):
        # Prepare
        mailing_template = self.env['mailing.mailing'].create([
            {
                "subject": "First template",
                "is_template": True,
            },
        ])

        # Execute
        res_action = mailing_template.action_duplicate_template()
        duplicated_template_id = res_action['res_id']
        rendered_remplate_form_view = self.env.ref('mass_mailing.mailing_templates_view_form', raise_if_not_found=False)

        # Assert
        self.assertNotEqual(duplicated_template_id, mailing_template.id)
        self.assertEqual(rendered_remplate_form_view, self.env['ir.ui.view'].browse(res_action['views'][0][0]))
        self.assertEqual(True, self.env['mailing.mailing'].search([('id', '=', duplicated_template_id)]).favorite)
        self.assertEqual(True, self.env['mailing.mailing'].search([('id', '=', duplicated_template_id)]).is_template)
