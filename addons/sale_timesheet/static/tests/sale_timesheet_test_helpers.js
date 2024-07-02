import { AccountAnalyticLine } from "./mock_server/mock_models/account_analytic_line";
import { ProjectTask } from "./mock_server/mock_models/project_task";
import { SaleOrderLine } from "./mock_server/mock_models/sale_order_line";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const saleTimesheetModels = {
    AccountAnalyticLine,
    ProjectTask,
    SaleOrderLine,
};

export function defineSaleTimesheetModels() {
    return defineModels({ ...mailModels, ...saleTimesheetModels });
}
