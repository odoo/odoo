from odoo.tests import common
from lxml import etree


class TestHrBaseIrUiViewL10n(common.TransactionCase):

    def test_ir_ui_view_l10n_form(self):
        res_partner_original_form = self.env.ref('base.view_partner_form')
        duplicated_view = res_partner_original_form.copy()
        tree_arch = etree.fromstring(duplicated_view.arch)

        company_type_node = tree_arch.xpath("//field[@name='company_type']")[0]
        company_type_node.set('l10n', 'BE')

        invisible_node = tree_arch.xpath("//*[@invisible]")[0]
        invisible_node.set('l10n', 'KE')

        duplicated_view.arch = etree.tostring(tree_arch)

        altered_arch = self.env['ir.ui.view'].get_view(duplicated_view.id)['arch']
        arch_tree = etree.fromstring(altered_arch)

        company_type_node = arch_tree.xpath("//*[@l10n='BE']")[0]
        assert company_type_node.get('invisible') == "'US' != 'BE'"

        invisible_node = arch_tree.xpath("//*[@l10n='KE']")[0]
        assert "'US' != 'KE' or (" in invisible_node.get('invisible')

        partner_with_country = self.env['res.partner'].create({
            'name': 'Test Partner',
            'country_id': self.env.ref('base.us').id,
        })

        rendered_arch = partner_with_country.get_views(views = [(duplicated_view.id, 'form')])['views']['form']['arch']
        assert "invisible=\"country_code != 'KE' or (" in rendered_arch
        assert "invisible=\"country_code != 'BE'\"" in rendered_arch

    def test_ir_ui_view_l10n_bad_l10n(self):
        res_partner_original_form = self.env.ref('base.view_partner_form')
        duplicated_view = res_partner_original_form.copy()
        tree_arch = etree.fromstring(duplicated_view.arch)

        company_type_node = tree_arch.xpath("//field[@name='company_type']")[0]
        company_type_node.set('l10n', 'BEA')

        duplicated_view.arch = etree.tostring(tree_arch)
        with self.assertRaises(Exception):
            self.env['ir.ui.view'].get_view(duplicated_view.id)

        company_type_node.set('l10n', 'B')
        duplicated_view.arch = etree.tostring(tree_arch)
        with self.assertRaises(Exception):
            self.env['ir.ui.view'].get_view(duplicated_view.id)

        company_type_node.set('l10n', 'BE')
        duplicated_view.arch = etree.tostring(tree_arch)
