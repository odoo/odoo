import { onWebsocketEvent } from "@bus/../tests/mock_websocket";
import { BACK_ONLINE_RECONNECT_DELAY } from "@bus/services/bus_service";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { advanceTime, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";

import {
    asyncStep,
    makeMockEnv,
    MockServer,
    mockService,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";

defineMailModels();
describe.current.tags("headless");

test("send the presence on each bus connection", async () => {
    // Simulate a website or portal page, where mail does not load im_status.
    mockService("im_status", () => ({ updateBusPresence() {} }));
    patchWithCleanup(session, { lock_timeout_inactivity: 600 });
    onWebsocketEvent("update_presence", () => asyncStep("update_presence"));
    await makeMockEnv();
    await waitForSteps(["update_presence"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await advanceTime(1000);
    await waitForSteps(["update_presence"]);
    manuallyDispatchProgrammaticEvent(window, "offline");
    manuallyDispatchProgrammaticEvent(window, "online");
    await advanceTime(BACK_ONLINE_RECONNECT_DELAY);
    await waitForSteps(["update_presence"]);
});
