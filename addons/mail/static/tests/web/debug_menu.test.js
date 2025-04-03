import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { asyncStep, onRpc, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("Manage messages", async () => {
    serverState.debug = "1";
    const pyEnv = await startServer();
    onRpc("mail.message", "web_search_read", (params) => {
        expect(params.kwargs.context.default_res_id).toBe(partnerId);
        expect(params.kwargs.context.default_res_model).toBe("res.partner");
        expect(params.kwargs.domain).toEqual([
            "&",
            ["res_id", "=", partnerId],
            ["model", "=", "res.partner"],
        ]);
        asyncStep("message_read");
    });
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "Bob" });
    await openFormView("res.partner", partnerId);
    await click(".o_debug_manager .dropdown-toggle");
    await click(".dropdown-item", { text: "Messages" });
    await waitForSteps(["message_read"]);
    await contains(".o_breadcrumb .active > span", { text: "Messages" });
});
