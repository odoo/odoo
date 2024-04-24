import { defineModels } from "@web/../tests/web_test_helpers";
import { HrExpenseSheet } from "@hr_expense/../tests/mock_server/mock_models/hr_expense_sheet";
import { HrExpense } from "@hr_expense/../tests/mock_server/mock_models/hr_expense";
import { mailModels } from "@mail/../tests/mail_test_helpers";

export function defineHrExpenseModels() {
    return defineModels(hrExpenseModels);
}

export const hrExpenseModels = { ...mailModels, HrExpenseSheet, HrExpense };
