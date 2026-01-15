import { describe, expect, test } from "@odoo/hoot";
import { queryFirst, waitFor } from "@odoo/hoot-dom";
import {
    asyncStep,
    makeMockEnv,
    MockServer,
    mockService,
    mountWithCleanup,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";
import { defineBusModels } from "./bus_test_helpers";

defineBusModels();
describe.current.tags("desktop");

test("receive and display simple notification", async () => {
    await mountWithCleanup(WebClient);
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "simple_notification", {
        message: "simple notification",
    });
    await waitFor(".o_notification");
    expect(queryFirst(".o_notification_content")).toHaveText("simple notification");
});

test("receive and display simple notification with specific type", async () => {
    await mountWithCleanup(WebClient);
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "simple_notification", {
        message: "simple notification",
        type: "info",
    });
    await waitFor(".o_notification");
    expect(".o_notification_bar").toHaveClass("bg-info");
});

test("receive and display simple notification as sticky", async () => {
    mockService("notification", {
        add(_, options) {
            expect(options.sticky).toBe(true);
            asyncStep("add notification");
        },
    });
    await makeMockEnv();
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "simple_notification", {
        message: "simple notification",
        sticky: true,
    });
    await waitForSteps(["add notification"]);
});
