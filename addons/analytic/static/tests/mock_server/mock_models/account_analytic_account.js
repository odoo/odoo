import { models, fields } from "@web/../tests/web_test_helpers";

export class AccountAnalyticAccount extends models.ServerModel {
    _name = "account.analytic.account";

    name = fields.Char()
    plan_id = fields.Many2one({ relation: 'account.analytic.plan' })
}
