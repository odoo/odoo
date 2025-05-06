from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestClLatamDocumentType(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('cl')
    def setUpClass(cls):
        super().setUpClass()

        country_cl = cls.env.ref('base.cl')
        rut_id_type = cls.env.ref('l10n_cl.it_RUT')

        cls.cl_partner_a, cls.cl_partner_b = cls.env['res.partner'].create([
            {
                'name': 'Chilean Partner A',
                'country_id': country_cl.id,
                'l10n_latam_identification_type_id': rut_id_type.id,
                'vat': '76201224-3',
                'l10n_cl_sii_taxpayer_type': '1',
            },
            {
                'name': 'Chilean Partner B',
                'country_id': country_cl.id,
                'l10n_latam_identification_type_id': rut_id_type.id,
                'vat': '76201224-3',
                'l10n_cl_sii_taxpayer_type': '1',
            },
        ])

        # Create a purchase journal that uses latam documents
        cls.purchase_journal = cls.env['account.journal'].create([{
            'name': 'Vendor bills elec',
            'code': 'VBE',
            'company_id': cls.company_data['company'].id,
            'type': 'purchase',
            'l10n_latam_use_documents': True,
            'default_account_id': cls.company_data['default_journal_purchase'].default_account_id.id,
        }])

    def test_document_type_not_modified_when_partner_changes(self):
        """ Test that when the partner changes, the document type is not reset to default
        if the currently selected document type is compatible with the new partner.
        """
        document_type_33 = self.env.ref('l10n_cl.dc_a_f_dte')
        document_type_46 = self.env.ref('l10n_cl.dc_fc_f_dte')

        # 1. Do the test with a new invoice
        with Form(self.env['account.move'].with_context({'default_move_type': 'in_invoice'})) as invoice_form:
            # Change the journal to the one that uses documents, set the partner and check that the
            # l10n_latam_document_type_id is computed and set to 33 (Factura Electronica, the default).
            invoice_form.journal_id = self.purchase_journal
            invoice_form.partner_id = self.cl_partner_a
            self.assertEqual(invoice_form.l10n_latam_document_type_id.id, document_type_33.id)

            # Change the document type to 45 (Factura de Compra)
            invoice_form.l10n_latam_document_type_id = document_type_46

            # Change the partner and check that the document type hasn't changed
            invoice_form.partner_id = self.cl_partner_b
            self.assertEqual(invoice_form.l10n_latam_document_type_id.id, document_type_46.id)

            invoice_form.l10n_latam_document_number = '000001'

        invoice = invoice_form.save()
        self.assertRecordValues(invoice, [{
            'partner_id': self.cl_partner_b.id,
            'l10n_latam_document_type_id': document_type_46.id,
        }])

        # 2. Do the test again with the existing invoice
        with Form(invoice) as invoice_form:
            # Change the partner and check that the document type hasn't changed
            invoice_form.partner_id = self.cl_partner_a
            self.assertEqual(invoice_form.l10n_latam_document_type_id.id, document_type_46.id)

        invoice_form.save()
        self.assertRecordValues(invoice, [{
            'partner_id': self.cl_partner_a.id,
            'l10n_latam_document_type_id': document_type_46.id,
        }])
