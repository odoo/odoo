import { AccountAnalyticAccount } from "@analytic/../tests/mock_server/mock_models/account_analytic_account";
import { AccountAnalyticLine } from "@analytic/../tests/mock_server/mock_models/account_analytic_line";
import { AccountAnalyticPlan } from "@analytic/../tests/mock_server/mock_models/account_analytic_plan";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const analyticModels = {
    AccountAnalyticAccount,
    AccountAnalyticLine,
    AccountAnalyticPlan,
};

export function defineAnalyticModels() {
    return defineModels({ ...mailModels, ...analyticModels });
}
