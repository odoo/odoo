from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import freeze_time

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon


@freeze_time('2024-06-15')
@tagged('external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestL10nPtHashing(TestL10nPtCommon):
    def test_l10n_pt_hash_sequence(self):
        """
        Test that the hash sequence is correct.
        For this, we use the following resource provided by the Portuguese tax authority:
        https://info.portaldasfinancas.gov.pt/apps/saft-pt01/local/saft_idemo599999999.xml
        We create invoices with the same info as in the link, and we check that the hash that we obtain in Odoo
        is the same as the one given in the link (using the same sample keys).
        """

        # This patch is necessary because we use the move_type in l10n_pt_document_number, but our
        # move types (out_invoice, out_refund, ...) are different from the ones used in the link (FT, NC, ...)
        l10n_pt_document_number = ""

        def _l10n_pt_get_document_number_patched(self_patched):
            return l10n_pt_document_number

        with patch('odoo.addons.l10n_pt_certification.models.account_move.AccountMove._l10n_pt_get_document_number', _l10n_pt_get_document_number_patched):
            for (l10n_pt_document_number, invoice_date, l10n_pt_hashed_on, amount, expected_hash) in [
                ('1T 1/1', '2017-03-10', '2017-03-10T15:58:01', 28.07, "vfinNfF+rToGp3dWF1LV6mEctQ76hAeZm+PlhBnV4wokN//N79L7fTNvi71ONnMHzfIzVR/Iz2zOOo9MUrYfYYZhqtpcEgFNHMdET6ZqbVVke7HbfqSACzaKXNdgWZt7lm7AFOfhcizQgC4a66SNvJvPJUqF7bCTUMIJFR9Zfro="),
                ('1T 1/2', '2017-09-16', '2017-09-16T15:58:10', 235.15, "jABYv0ThJHWoocmbzuLPOJXknl2WHBpLRBPqhIBSYP6GRzo3WiMxh6ryFiaa8rQD2BM9tdLxjhPHOZo1XPeGR5hFGK5BI/NzTXBu9+ponV4wvASOhjy2iomBlOxISN3MYGBcG1XWLfi+aDBw0TLrVwpbsENk0MtypYGU78OPPjg="),
                ('1T 1/3', '2017-09-16', '2017-09-16T15:58:45', 679.61, "MqvfiYZOh1L1fgfrAXBemPED1xy27MUs79vWxk/0P99Bq+jxvxwjJa3HQdElGfogj5bslcxX3ia9Tps2Oxfw1kH3GnsmfzqHbVagqnNxiI/KMZGfR4XXXNSOf7l7K7iMELz29b/c8u8eRmUwm13sgk9E9yAyk9zLuQ/s5TByG9k="),
            ]:
                with self.subTest(invoice_date=invoice_date, l10n_pt_hashed_on=l10n_pt_hashed_on, amount=amount, expected_hash=expected_hash):
                    move = self.create_invoice('out_invoice', invoice_date, l10n_pt_hashed_on, amount, self.tax_sale_0, do_hash=True)
                    move.flush_recordset()
                    self.assertEqual(move.inalterable_hash.split("$")[2], expected_hash)

            # Now we'll test with a different move_type/InvoiceType (first part of the l10n_pt_document_number is different),
            # Therefore we have a new chain and the following first move has no previous move (i.e. 1T 1/3 is not the previous).
            for (l10n_pt_document_number, l10n_pt_hashed_on, amount, expected_hash) in [
                ('2T A/1', '2017-09-16T16:02:16', 235.15, "CM1pPaqk/pTE5DajJZ3H9VejD00FL455GvHx0FjuNj3UKj1V9EkP5dPsOpB6/KXlttY1WsHGG4dcunSOKULW0FMEWAMQYxBo/HqLcIojedKxrzh6m9+P61VM4BnYxbtEBQRFdVs0MGP8X85uSc4ikPrY4OeO1UOixGR9xLIAtr4="),
                ('2T A/2', '2017-09-16T16:03:11', 2261.34, "Y7kXSvGiS1eCSU9DY1GlWHw+HMmpI/gdZKEv17EXFC7OFdOdSCwcRNPzBUB6QjB1aQ60T8+4jvQb+tSWAQJdsCoiNUMcZl+oQJKJjJTfPJTmDBlrnh0JGXaOrg4sPe1eVvjjtCKxyJ3xoQnwU/bVBjMde2Kx0zXBsBwIWoT0ukg="),
                ('2T A/3', '2017-09-16T16:04:45', 47.03, "W3Z1jj4rNG5CREwXq0ZCjaRHDqrB1U9U6NmyKZZ7VpruDsw+NxcbwUubuMgejYBCVr6OIRrUNlm1UvNuYx/EXFZpzhdoWRc7O1HPBSQFhAfhByE6QxvumsVtxSome95/cG2VmAU1MJUJTVQN4Y//snz8YaCy1/81bB7aGfUs0C0="),
            ]:
                with self.subTest(l10n_pt_hashed_on=l10n_pt_hashed_on, amount=amount, expected_hash=expected_hash):
                    move = self.create_invoice('out_refund', '2017-09-16', l10n_pt_hashed_on, amount, self.tax_sale_0, do_hash=True)
                    move.flush_recordset()
                    self.assertEqual(move.inalterable_hash.split("$")[2], expected_hash)
