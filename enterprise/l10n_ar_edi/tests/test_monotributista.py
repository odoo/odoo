from odoo.addons.account.tests.common import skip_unless_external
from odoo.addons.l10n_ar_edi.tests.common import TestArEdiCommon
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install', *TestArEdiCommon.extra_tags)
class TestArEdiWsfeMono(TestArEdiCommon):

    @classmethod
    @TestArEdiCommon.setup_afip_ws('wsfe')
    def setUpClass(cls):
        # Issue ['C', 'E'] and  Receive ['B', 'C', 'I']
        # Login in "Monotributista" Company
        super().setUpClass()
        cls.subfolder = "wsfe/mono"
        cls.env.user.write({'company_id': cls.company_mono.id})

        cls.partner = cls.res_partner_adhoc
        cls.journal = cls._create_journal('wsfe')
        cls.document_type.update({
            'invoice_c': cls.env.ref('l10n_ar.dc_c_f'),
            'debit_note_c': cls.env.ref('l10n_ar.dc_c_nd'),
            'credit_note_c': cls.env.ref('l10n_ar.dc_c_nc'),
        })

        if 'external' in cls.test_tags:
            cls.company_mono.write({'l10n_ar_afip_ws_crt_id': cls.ar_certificate_2})
            cls._create_afip_connections(cls.company_mono, cls.afip_ws)
        else:
            cls.company_mono.l10n_ar_afip_ws_crt_id = False

    @skip_unless_external
    def test_ar_edi_wsfe_mono_external_flow(self):
        self._test_ar_edi_common_external()

    def test_ar_edi_wsfe_mono_flow_suite(self):
        for test_name, move_type, document_code, concept in (
                ('test_wsfe_mono_invoice_c_product', 'invoice', 'c', 'product'),
                ('test_wsfe_mono_invoice_c_service', 'invoice', 'c', 'service'),
                ('test_wsfe_mono_invoice_c_product_service', 'invoice', 'c', 'product_service'),
                ('test_wsfe_mono_debit_note_c_product', 'debit_note', 'c', 'product'),
                ('test_wsfe_mono_debit_note_c_service', 'debit_note', 'c', 'service'),
                ('test_wsfe_mono_debit_note_c_product_service', 'debit_note', 'c', 'product_service'),
                ('test_wsfe_mono_credit_note_c_product', 'credit_note', 'c', 'product'),
                ('test_wsfe_mono_credit_note_c_service', 'credit_note', 'c', 'service'),
                ('test_wsfe_mono_credit_note_c_product_service', 'credit_note', 'c', 'product_service'),
        ):
            with self.subTest(test_name=test_name), self.cr.savepoint() as sp:
                self._test_ar_edi_flow(test_name, move_type, document_code, concept)
                sp.close()  # Rollback to ensure all subtests start in the same situation
