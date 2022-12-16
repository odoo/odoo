# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import SavepointCase, tagged


@tagged('post_install', '-at_install')
class TestAccountTaxUpdate(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountTaxUpdate, cls).setUpClass()
        cls.chart_template = cls.env.company.chart_template_id
        cls.inv_base_tag = cls.env['account.account.tag'].create({
            'name': 'invoice_base',
            'applicability': 'taxes',
            'country_id': cls.env.company.country_id.id,
        })
        cls.inv_tax_tag = cls.env['account.account.tag'].create({
            'name': 'invoice_tax',
            'applicability': 'taxes',
            'country_id': cls.env.company.country_id.id,
        })
        cls.ref_base_tag = cls.env['account.account.tag'].create({
            'name': 'refund_base',
            'applicability': 'taxes',
            'country_id': cls.env.company.country_id.id,
        })
        cls.ref_tax_tag = cls.env['account.account.tag'].create({
            'name': 'refund_tax',
            'applicability': 'taxes',
            'country_id': cls.env.company.country_id.id,
        })
        cls.template = cls.env['account.tax.template']._load_records([{
            'xml_id': 'foo.test_tax_template',
            'values': {
                'name': 'Tax Test',
                'amount_type': 'fixed',
                'type_tax_use': 'sale',
                'amount': 30,
                'chart_template_id': cls.chart_template.id,
                'invoice_repartition_line_ids': [
                    (0, 0, {'factor_percent': 100, 'repartition_type': 'base', 'tag_ids': [(4, cls.inv_base_tag.id, 0)]}),
                    (0, 0, {'factor_percent': 100, 'repartition_type': 'tax', 'tag_ids': [(4, cls.inv_tax_tag.id, 0)]}),
                ],
                'refund_repartition_line_ids': [
                    (0, 0, {'factor_percent': 100, 'repartition_type': 'base', 'tag_ids': [(4, cls.ref_base_tag.id, 0)]}),
                    (0, 0, {'factor_percent': 100, 'repartition_type': 'tax', 'tag_ids': [(4, cls.ref_tax_tag.id, 0)]}),
                ],
            },
            'noupdate': True,
        }])
        template_vals = cls.template._get_tax_vals_complete(cls.env.company)
        tax_id = cls.chart_template.create_record_with_xmlid(cls.env.company, cls.template, 'account.tax', template_vals)
        cls.tax = cls.env['account.tax'].browse(tax_id)

    def test_xmlid_match_template_match(self):
        inv_tax_updated_tag = self.env['account.account.tag'].create({
            'name': 'invoice_tax_updated',
            'applicability': 'taxes',
            'country_id': self.env.company.country_id.id,
        })
        self.tax.invoice_repartition_line_ids.write({'tag_ids': [(4, inv_tax_updated_tag.id, 0), (3, self.inv_tax_tag.id)]})
        self.assertNotEqual(self.template.invoice_repartition_line_ids.tag_ids, self.tax.invoice_repartition_line_ids.tag_ids,
                            "Tax template tags and tax tags should be different.")
        self.env['account.tax.update'].update_taxes()
        self.assertEqual(self.template.invoice_repartition_line_ids.tag_ids, self.tax.invoice_repartition_line_ids.tag_ids,
                         "After update, tax tags should be the same than template tags.")
