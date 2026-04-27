from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestAccountFollowupCommon(AccountTestInvoicingCommon):
    def assertPartnerFollowup(self, partner, status, line):
        partner.invalidate_recordset(['followup_status', 'followup_line_id'])
        # Since we are querying multiple times with data changes in the same transaction (for the purpose of tests),
        # we need to invalidated the cache in database
        self.env.cr.cache.pop('res_partner_all_followup', None)
        res = partner._query_followup_data()
        self.assertEqual(res.get(partner.id, {}).get('followup_status'), status)
        self.assertEqual(res.get(partner.id, {}).get('followup_line_id'), line.id if line else None)
        self.assertEqual(partner.followup_status, status or 'no_action_needed')
        self.assertEqual(partner.followup_line_id.id if partner.followup_line_id else None, line.id if line else None)
