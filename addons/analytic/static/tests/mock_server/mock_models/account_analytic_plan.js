import { models, fields } from "@web/../tests/web_test_helpers";

export class AccountAnalyticPlan extends models.ServerModel {
    _name = "account.analytic.plan";

    name = fields.Char()
    parent_id = fields.Many2one({ relation: "account.analytic.plan" })
}
