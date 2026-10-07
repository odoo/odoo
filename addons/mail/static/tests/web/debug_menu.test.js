import {
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { contains, onRpc, serverState } from "@web/../tests/web_test_helpers";

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
        expect.step("message_read");
    });
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "Bob" });
    await openFormView("res.partner", partnerId);
    await contains(".o_debug_manager .dropdown-toggle:count(1)").click();
    await contains(".dropdown-item:text('Messages'):count(1)").click();
    await expect.waitForSteps(["message_read"]);
    await waitFor(".o_breadcrumb .active > span:text('Messages'):count(1)");
});
