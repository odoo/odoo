import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers, waitFor } from "@odoo/hoot-dom";
import { contains, getService, MockServer, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { defineBusModels } from "./bus_test_helpers";

defineBusModels();
describe.current.tags("desktop");

test("can listen on bus and display notifications in DOM", async () => {
    browser.location.addEventListener("reload", () => expect.step("reload-page"));
    await mountWithCleanup(WebClient);
    getService("bus_service").subscribe("bundle_changed", () => expect.step("bundle_changed"));
    MockServer.env["bus.bus"]._sendone("broadcast", "bundle_changed", {
        server_version: "NEW_MAJOR_VERSION",
    });
    await expect.waitForSteps(["bundle_changed"]);
    await runAllTimers();
    await waitFor(".o_notification", { text: "The page appears to be out of date." });
    await contains(".o_notification button:contains(Refresh)").click();
    await expect.waitForSteps(["reload-page"]);
});
