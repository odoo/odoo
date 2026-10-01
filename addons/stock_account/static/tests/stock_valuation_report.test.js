import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { getPickerCell } from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    contains,
    defineActions,
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

defineActions([
    {
        id: 42,
        name: "Stock Valuation",
        tag: "stock_valuation_report",
        type: "ir.actions.client",
    },
    {
        id: 43,
        xml_id: "account.action_account_moves_all",
        name: "Journal Items",
        res_model: "account.move.line",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    },
]);
defineMailModels();

describe.current.tags("desktop");

test("Report dates follow the company's today", async function () {
    // 2026-07-01 22:00 for the user, already 2026-07-02 for a company in UTC+9.
    mockDate("2026-07-01 20:00:00", +2);
    onRpc("get_report_values", ({ kwargs }) => {
        expect.step(`report: ${kwargs.date}`);
        return {
            data: {
                company_id: 1,
                currency_id: 1,
                today: "2026-07-02",
                date_upper_bound: kwargs.date ? "2026-07-01 14:59:59" : false,
                accounts_by_id: { 1: { id: 1, display_name: "Stock Valuation" } },
                initial_balance: { value: 10, lines_by_account_id: { 1: { value: 10 } } },
                inventory_loss: { value: 0, lines: [] },
                stock_variation: { value: 0, lines: [] },
                ending_stock: { value: 0, lines_by_account_id: {} },
            },
            context: {},
        };
    });
    onRpc("action_close_stock_valuation", ({ args }) => {
        expect.step(`close: ${args[1]}`);
        return false;
    });
    await mountWithCleanup(WebClient);
    mockService("action", {
        doAction(action) {
            if (action?.res_model === "account.move.line") {
                expect.step(`journal items: ${JSON.stringify(action.domain)}`);
                return;
            }
            if (action?.res_model === "stock.move") {
                expect.step(`stock moves: ${JSON.stringify(action.domain.at(-1))}`);
                return;
            }
            return super.doAction(...arguments);
        },
    });

    await getService("action").doAction(42);
    expect.verifySteps(["report: false"]);
    expect("#filter_date").toHaveText("As of 07/02/2026");

    await contains("#filter_date").click();
    await contains(getPickerCell("1", true)).click();
    expect.verifySteps(["report: 2026-07-01"]);

    await contains(".o_report_button_generate_entry").click();
    expect.verifySteps(["close: 2026-07-01"]);

    await contains(".line_name a:contains(Initial Balance)").click();
    expect.verifySteps([`journal items: [["account_id","in",[1]],["date","<=","2026-07-01"]]`]);

    await contains(".line_name a:contains(Inventory Loss)").click();
    expect.verifySteps([`stock moves: ["date","<=","2026-07-01 14:59:59"]`]);
});
