import { expect, test } from "@odoo/hoot";
import { contains, mockService } from "@web/../tests/web_test_helpers";
import { mountWithCleanup } from "@web/../tests/_framework/component_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { AccountDashboardKpis } from "@account/components/account_dashboard_kpis/account_dashboard_kpis";

defineMailModels();

test.tags("desktop");
test("account dashboard KPIs are loaded, rendered, and clickable", async () => {
    mockService("orm", {
        async call(model, method, args) {
            expect(model).toBe("account.journal");
            expect(args).toEqual([]);
            expect.step("load kpis");
            expect(method).toBe("get_account_dashboard_kpis");
            return [
                {
                    id: "invoices",
                    name: "Invoices",
                    value: "$ 100.00",
                    action_id: 42,
                },
                {
                    id: "cash",
                    name: "Cash",
                    value: "$ 60.00",
                    action_id: 43,
                },
            ];
        },
    });

    mockService("action", {
        doAction(action) {
            expect.step(`open action ${action}`);
        },
    });

    await mountWithCleanup(AccountDashboardKpis, {
        noMainContainer: true,
    });

    await expect.waitForSteps(["load kpis"]);

    expect(".o_account_dashboard_kpi_card").toHaveCount(2);
    expect('[data-kpi-id="invoices"] .o_account_dashboard_kpi_name').toHaveText("Invoices");
    expect('[data-kpi-id="invoices"] .o_account_dashboard_kpi_value').toHaveText("$ 100.00");
    expect('[data-kpi-id="cash"] .o_account_dashboard_kpi_name').toHaveText("Cash");
    expect('[data-kpi-id="cash"] .o_account_dashboard_kpi_value').toHaveText("$ 60.00");

    await contains('[data-kpi-id="invoices"]').click();
    await contains('[data-kpi-id="cash"]').click();

    expect.verifySteps(["open action 42", "open action 43"]);
});
