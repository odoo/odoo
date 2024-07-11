import lxml
from freezegun.api import freeze_time

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_es_edi_facturae.tests.test_edi_xml import TestEdiFacturaeXmls


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiFacturaeAdmCentersXmls(TestEdiFacturaeXmls):
    @classmethod
    def setUpClass(cls, chart_template_ref='es_full'):
        super().setUpClass(chart_template_ref)

        cls.partner_b.write({
            'name': 'Ayuntamiento de San Sebastián de los Reyes',
            'is_company': True,
            'country_id': cls.env.ref('base.es').id,
            'vat': 'P2813400E',
            'city': 'San Sebastián de los Reyes',
            'street': 'Plaza de la Constitución, 1',
            'zip': '28701',
            'state_id': cls.env.ref('base.state_es_m').id,
        })
        partner_b_ac = cls.partner_b.copy()
        partner_b_ac.write({
            'type': 'facturae_ac',
            'parent_id': cls.partner_b.id,
            'name': 'Intervención Municipal',
            'l10n_es_edi_facturae_ac_center_code': 'L01281343',
            'l10n_es_edi_facturae_ac_role_type_ids': [
                Command.link(cls.env.ref('l10n_es_edi_facturae_adm_centers.ac_role_type_01').id),
                Command.link(cls.env.ref('l10n_es_edi_facturae_adm_centers.ac_role_type_02').id),
                Command.link(cls.env.ref('l10n_es_edi_facturae_adm_centers.ac_role_type_03').id),
            ],
        })

    @freeze_time('2023-01-01')
    def test_generate_with_administrative_centers(self):
        invoice = self.create_invoice(
            partner_id=self.partner_b.id,
            move_type='out_invoice',
            invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]},]
        )
        invoice.action_post()
        generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
        self.assertFalse(errors)
        self.assertTrue(generated_file)

        with file_open('l10n_es_edi_facturae_adm_centers/tests/data/expected_ac_document.xml', 'rt') as f:
            expected_xml = lxml.etree.fromstring(f.read().encode())
        self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)
