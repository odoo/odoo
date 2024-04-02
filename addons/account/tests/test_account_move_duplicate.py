from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import RedirectWarning


@tagged('post_install', '-at_install')
class TestAccountMoveDuplicate(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.init_invoice('in_invoice', products=cls.product_a + cls.product_b)

    def test_in_invoice_multiple_duplicate_reference_constrains(self):
        """ Ensure that an error is raised on post if some invoices with duplicated ref share the same invoice_date """
        invoice_1 = self.invoice
        invoice_1.ref = 'a unique supplier reference that will be copied'
        invoice_2 = invoice_1.copy(default={'invoice_date': invoice_1.invoice_date})
        invoice_3 = invoice_1.copy(default={'invoice_date': invoice_1.invoice_date})

        # reassign to trigger the compute method
        invoices = invoice_1 + invoice_2 + invoice_3
        invoices.ref = invoice_1.ref

        # test constrains: batch without any previous posted invoice
        with self.assertRaises(RedirectWarning) as cm:
            (invoice_1 + invoice_2 + invoice_3).action_post()
        # Check that the RedirectWarning has a correct domain
        redirection_domain = cm.exception.args[1]["domain"]
        self.assertEqual(redirection_domain[0][:2], ("id", "in"))
        self.assertEqual(set(redirection_domain[0][2]), set(invoices.ids))
