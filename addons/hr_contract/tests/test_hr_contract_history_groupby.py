# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

class TestHrContractHistoryGroupby(TransactionCase):

    def test_related_activity_state_groupable(self):
        self.env['hr.contract.history']._read_group([], ['activity_state'])
        with self.assertQueries([
            """
            SELECT "hr_contract__last_activity_state"."activity_state"
            FROM "hr_contract_history"
            LEFT JOIN "hr_contract"
                ON ("hr_contract_history"."contract_id" = "hr_contract"."id")
            LEFT JOIN (
                    SELECT res_id,
                        CASE
                            WHEN min(EXTRACT(day from (mail_activity.date_deadline - DATE_TRUNC('day', %s AT TIME ZONE COALESCE(mail_activity.user_tz, %s))))) > 0 THEN 'planned'
                            WHEN min(EXTRACT(day from (mail_activity.date_deadline - DATE_TRUNC('day', %s AT TIME ZONE COALESCE(mail_activity.user_tz, %s))))) < 0 THEN 'overdue'
                            WHEN min(EXTRACT(day from (mail_activity.date_deadline - DATE_TRUNC('day', %s AT TIME ZONE COALESCE(mail_activity.user_tz, %s))))) = 0 THEN 'today'
                            ELSE null
                        END AS activity_state
                        FROM mail_activity
                        WHERE res_model = %s AND mail_activity.active = TRUE
                        GROUP BY res_id
                    ) AS "hr_contract__last_activity_state"
                ON ("hr_contract"."id" = "hr_contract__last_activity_state"."res_id")
            GROUP BY "hr_contract__last_activity_state"."activity_state"
            ORDER BY "hr_contract__last_activity_state"."activity_state" ASC
            """,
        ]):
            self.env['hr.contract.history']._read_group([], ['activity_state'])
