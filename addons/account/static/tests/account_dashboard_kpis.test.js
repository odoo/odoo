import { expect, test } from "@odoo/hoot";
import { contains, mockService } from "@web/../tests/web_test_helpers";
import { mountWithCleanup } from "@web/../tests/_framework/component_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { AccountDashboardKpis } from "@account/components/account_dashboard_kpis/account_dashboard_kpis";

defineMailModels();

test.tags("desktop");
test("account dashboard KPIs are loaded, rendered, and clickable", async () => {
    const revenueAction = {
        type: "ir.actions.act_window",
        res_model: "account.move.line",
    };
    mockService("orm", {
        async call(model, method, args) {
            expect(model).toBe("account.journal");
            expect(args).toEqual([]);

            if (method === "action_open_revenue_journal_items") {
                expect.step("load revenue action");
                return revenueAction;
            }

            expect.step("load kpis");
            expect(method).toBe("get_account_dashboard_kpis");
            return [
                {
                    id: "revenue",
                    name: "Revenue",
                    has_total: true,
                    value: "$ 100.00",
                    action_id: 42,
                    action_method: "action_open_revenue_journal_items",
                },
                {
                    id: "cashflow",
                    has_total: false,
                    is_cashflow_card: true,
                    values: [
                        {
                            label: "Cash In",
                            value: "$ 100.00",
                        },
                        {
                            label: "Cash Out",
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
                expect(action).toBe(revenueAction);
                expect.step("open revenue action");
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
    expect('[data-kpi-id="revenue"] .o_account_dashboard_kpi_name').toHaveText("Revenue");
    expect('[data-kpi-id="revenue"] .o_account_dashboard_kpi_value').toHaveText("$ 100.00");

    expect('[data-kpi-id="cashflow"] .o_account_dashboard_kpi_name').toHaveCount(0);
    expect('[data-kpi-id="cashflow"] .o_account_dashboard_kpi_value').toHaveCount(0);
    expect('[data-kpi-id="cashflow"] .o_account_dashboard_kpi_value_item').toHaveCount(2);
    expect(
        '[data-kpi-id="cashflow"] .o_account_dashboard_kpi_value_label:eq(0)'
    ).toHaveText("Cash In");
    expect(
        '[data-kpi-id="cashflow"] .o_account_dashboard_kpi_value_amount:eq(0)'
    ).toHaveText("$ 100.00");
    expect(
        '[data-kpi-id="cashflow"] .o_account_dashboard_kpi_value_label:eq(1)'
    ).toHaveText("Cash Out");
    expect(
        '[data-kpi-id="cashflow"] .o_account_dashboard_kpi_value_amount:eq(1)'
    ).toHaveText("$ 40.00");

    await contains('[data-kpi-id="revenue"]').click();
    await contains('[data-kpi-id="cashflow"]').click();

    expect.verifySteps(["load revenue action", "open revenue action", "open action 43"]);
});
