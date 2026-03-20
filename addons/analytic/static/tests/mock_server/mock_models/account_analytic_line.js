import { models, fields } from "@web/../tests/web_test_helpers";

export class AccountAnalyticLine extends models.ServerModel {
    _name = "account.analytic.line";

    amount = fields.Float()
    account_id = fields.Many2one({ relation: "account.analytic.account" })
    x_plan1_id = fields.Many2one({ string: "State", relation: "account.analytic.account" })
    x_plan1_id_1 = fields.Many2one({ string: "Continent", relation: "account.analytic.plan" })
    x_plan1_id_2 = fields.Many2one({ string: "Country ", relation: "account.analytic.plan" })
    analytic_distribution = fields.Json();
}
