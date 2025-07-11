import { models, fields } from "@web/../tests/web_test_helpers";

export class AccountAnalyticPlan extends models.ServerModel {
    _name = "account.analytic.plan";

    name = fields.Char()
    parent_id = fields.Many2one({ relation: "account.analytic.plan" })

    get_relevant_plans() {
        return this.filter((plan) => !plan.parent_id).map((plan) => {
            return {
                "id": plan.id,
                "name": plan.name,
                "color": plan.color,
                "applicability": plan.default_applicability || "optional",
                "all_account_count": 1,
                "column_name": `x_plan${plan.id}_id`,
            }
        })
    }
}
