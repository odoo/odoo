from freezegun import freeze_time
from odoo.tests import tagged
from odoo.addons.account_followup.tests.test_account_followup import TestAccountFollowupReports


@tagged('post_install', '-at_install')
class TestNoFollowupAccountFollowupReports(TestAccountFollowupReports):

    def test_followup_line_and_status(self):
        followup_line = self.create_followup(delay=-10)

        self.create_invoice('2022-01-02')

        with freeze_time('2022-02-03'):
            aml_ids = self.partner_a.unreconciled_aml_ids

            # Exclude every unreconciled invoice line.
            aml_ids.no_followup = True
            # Every unreconciled invoice line is excluded, so the result should be `no_action_needed`.
            self.assertPartnerFollowup(self.partner_a, 'no_action_needed', followup_line)

            # It resets if we don't exclude them anymore.
            aml_ids.no_followup = False
            self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', followup_line)
