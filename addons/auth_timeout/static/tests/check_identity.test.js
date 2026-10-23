import { onWebsocketEvent } from "@bus/../tests/mock_websocket";
import { BACK_ONLINE_RECONNECT_DELAY } from "@bus/services/bus_plugin";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { advanceTime, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";

import {
    makeTestApp,
    MockServer,
    mockService,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";

defineMailModels();
describe.current.tags("headless");

test("send the presence on each bus connection", async () => {
    // Simulate a website or portal page without live chat, where mail does not load im_status.
    mockService("im_status", () => ({ updateBusPresence() {} }));
    patchWithCleanup(session, { lock_timeout_inactivity: 600 });
    onWebsocketEvent("update_presence", () => expect.step("update_presence"));
    await makeTestApp();
    await expect.waitForSteps(["update_presence", "update_presence"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await advanceTime(1000);
    await expect.waitForSteps(["update_presence"]);
    manuallyDispatchProgrammaticEvent(window, "offline");
    manuallyDispatchProgrammaticEvent(window, "online");
    await advanceTime(BACK_ONLINE_RECONNECT_DELAY);
    await expect.waitForSteps(["update_presence"]);
});
