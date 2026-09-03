import { expect, test } from "@odoo/hoot";
import { contains, mockService } from "@web/../tests/web_test_helpers";
import { mountWithCleanup } from "@web/../tests/_framework/component_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { AccountDashboardKpis } from "@account/components/account_dashboard_kpis/account_dashboard_kpis";

defineMailModels();

test("account dashboard KPIs are loaded, rendered, and clickable", async () => {
    const incomeAction = {
        type: "ir.actions.act_window",
        res_model: "account.move.line",
    };
    mockService("orm", {
        async call(model, method, args) {
            expect(model).toBe("account.journal");
            expect(args).toEqual([]);

            if (method === "action_open_income_journal_items") {
                expect.step("load income action");
                return incomeAction;
            }

            expect.step("load kpis");
            expect(method).toBe("get_account_dashboard_kpis");
            return [
                {
                    id: "income",
                    name: "Income",
                    has_total: true,
                    value: "$ 100.00",
                    action_id: 42,
                    action_method: "action_open_income_journal_items",
                },
                {
                    id: "unpaid",
                    name: "Unpaid",
                    has_total: false,
                    values: [
                        {
                            label: "Customers",
                            value: "$ 100.00",
                        },
                        {
                            label: "Suppliers",
                            value: "$ 40.00",
                        },
                    ],
                    action_id: 43,
                },
            ];
        },
    });

    mockService("action", {
        doAction(action) {
            if (typeof action === "object") {
                expect(action).toBe(incomeAction);
                expect.step("open income action");
            } else {
                expect.step(`open action ${action}`);
            }
        },
    });

    await mountWithCleanup(AccountDashboardKpis, {
        noMainContainer: true,
    });

    await expect.waitForSteps(["load kpis"]);

    expect(".o_account_dashboard_kpi_card").toHaveCount(2);
    expect(".o_account_dashboard_kpi_card:eq(0) .o_account_dashboard_kpi_name").toHaveText(
        "Income"
    );
    expect(".o_account_dashboard_kpi_card:eq(0) .o_account_dashboard_kpi_value").toHaveText(
        "$ 100.00"
    );

    expect(".o_account_dashboard_kpi_card:eq(1) .o_account_dashboard_kpi_name").toHaveText(
        "Unpaid"
    );
    expect(".o_account_dashboard_kpi_card:eq(1) .o_account_dashboard_kpi_value").toHaveCount(0);
    expect(".o_account_dashboard_kpi_card:eq(1) .o_account_dashboard_kpi_value_item").toHaveCount(
        2
    );
    expect(
        ".o_account_dashboard_kpi_card:eq(1) .o_account_dashboard_kpi_value_label:eq(0)"
    ).toHaveText("Customers");
    expect(
        ".o_account_dashboard_kpi_card:eq(1) .o_account_dashboard_kpi_value_amount:eq(0)"
    ).toHaveText("$ 100.00");
    expect(
        ".o_account_dashboard_kpi_card:eq(1) .o_account_dashboard_kpi_value_label:eq(1)"
    ).toHaveText("Suppliers");
    expect(
        ".o_account_dashboard_kpi_card:eq(1) .o_account_dashboard_kpi_value_amount:eq(1)"
    ).toHaveText("$ 40.00");

    await contains(".o_account_dashboard_kpi_card:eq(0)").click();
    await contains(".o_account_dashboard_kpi_card:eq(1)").click();

    expect.verifySteps(["load income action", "open income action", "open action 43"]);
});
