import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { defineActions, getService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

defineActions([
    {
        id: 42,
        name: "Stock report",
        tag: "stock_report_generic",
        type: "ir.actions.client",
        context: {},
        params: {},
    },
]);
defineMailModels();

test("Rendering with no lines", async function () {
    onRpc("get_main_lines", () => []);
    await mountWithCleanup(WebClient);

    await getService("action").doAction(42);
    expect(".o_stock_reports_page").toHaveText("No operation made on this lot.");
});
