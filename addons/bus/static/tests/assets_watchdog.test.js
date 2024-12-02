import { describe, test } from "@odoo/hoot";
import { runAllTimers, waitFor } from "@odoo/hoot-dom";
import {
    asyncStep,
    contains,
    MockServer,
    mountWithCleanup,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { defineBusModels } from "./bus_test_helpers";

defineBusModels();
describe.current.tags("desktop");

test("can listen on bus and display notifications in DOM", async () => {
    patchWithCleanup(browser.location, { reload: () => asyncStep("reload-page") });
    const { env } = await mountWithCleanup(WebClient);
    env.services.bus_service.subscribe("bundle_changed", () => asyncStep("bundle_changed"));
    MockServer.current.env["bus.bus"]._sendone("broadcast", "bundle_changed", {
        server_version: "NEW_MAJOR_VERSION",
    });
    await waitForSteps(["bundle_changed"]);
    await runAllTimers();
    await waitFor(".o_notification", { text: "The page appears to be out of date." });
    await contains(".o_notification button:contains(Refresh)").click();
    await waitForSteps(["reload-page"]);
});
