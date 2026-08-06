import { models, fields } from "@web/../tests/web_test_helpers";

export class AccountAnalyticDistributionModel extends models.ServerModel {
    _name = "account.analytic.distribution.model";

    analytic_distribution = fields.Json();
}
