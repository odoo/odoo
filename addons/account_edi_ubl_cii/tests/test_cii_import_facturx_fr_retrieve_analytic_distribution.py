from odoo.addons.account_edi_ubl_cii.tests.test_cii_import_facturx_fr import CiiImportFacturXFR
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCiiImportFacturXFRRetrieveAnalyticDistribution(CiiImportFacturXFR):

    def test_partial_import_analytic_distribution_invoice_predictive(self):
        self.ensure_installed('account_accountant')

        self.env.user.group_ids += self.env.ref('analytic.group_analytic_accounting')
        analytic_plan = self.env['account.analytic.plan'].create({'name': "Plan Test"})
        analytic_account = self.env['account.analytic.account'].create({
            'name': "turlututu",
            'plan_id': analytic_plan.id,
        })
        analytic_distribution = {str(analytic_account.id): 100.0}
        product = self._create_product(name='turlututu', barcode='12345678912345')

        # Invoice to train the prediction.
        invoice = self._create_invoice_one_line(
            name="turlututu",
            product_id=product,
            partner_id=self.partner_be,
        )
        invoice.invoice_line_ids.analytic_distribution = analytic_distribution
        invoice.action_post()

        # Check the prediction.
        self.env.flush_all()
        imported_invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_account_invoice_predictive',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(imported_invoice, [{'partner_id': self.partner_be.id}])
        self.assertRecordValues(imported_invoice.invoice_line_ids, [{
            'name': "turlutututu",
            'product_id': product.id,
            'analytic_distribution': analytic_distribution,
        }])
