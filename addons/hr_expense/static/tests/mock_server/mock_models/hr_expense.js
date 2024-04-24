import { models } from "@web/../tests/web_test_helpers";

export class HrExpense extends models.ServerModel {
    _name = "hr.expense";

    get_expense_dashboard() {
        return {
            draft: {
                description: "to report",
                amount: 1000000000.00,
                currency: 2,
            },
            reported: {
                description: "under validation",
                amount: 1000000000.00,
                currency: 2,
            },
            approved: {
                description: "to be reimbursed",
                amount: 1000000000.00,
                currency: 2,
            },
        };
    }
}
