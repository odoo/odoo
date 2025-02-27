import { describe, test } from "@odoo/hoot";
import { runAllTimers, waitFor } from "@odoo/hoot-dom";
import {
    asyncStep,
    contains,
    getService,
    MockServer,
    mountWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { defineBusModels } from "./bus_test_helpers";

defineBusModels();
describe.current.tags("desktop");

test("can listen on bus and display notifications in DOM", async () => {
    browser.location.addEventListener("reload", () => asyncStep("reload-page"));
    await mountWithCleanup(WebClient);
    getService("bus_service").subscribe("bundle_changed", () => asyncStep("bundle_changed"));
    MockServer.env["bus.bus"]._sendone("broadcast", "bundle_changed", {
        server_version: "NEW_MAJOR_VERSION",
    });
    await waitForSteps(["bundle_changed"]);
    await runAllTimers();
    await waitFor(".o_notification", { text: "The page appears to be out of date." });
    await contains(".o_notification button:contains(Refresh)").click();
    await waitForSteps(["reload-page"]);
});
