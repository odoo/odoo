import { addBusServiceListeners, lockWebsocketConnect } from "@bus/../tests/bus_test_helpers";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { defineMailModels, openDiscuss, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, runAllTimers, waitFor, waitForNone } from "@odoo/hoot-dom";
import { asyncStep, MockServer, waitForSteps } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("show warning when bus connection encounters issues", async () => {
    addBusServiceListeners(
        ["connect", () => asyncStep("connect")],
        ["reconnect", () => asyncStep("reconnect")],
        ["reconnecting", () => asyncStep("reconnecting")]
    );
    await start();
    await openDiscuss();
    await waitForSteps(["connect"]);
    const unlockWebsocket = lockWebsocketConnect();
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["reconnecting"]);
    expect(await waitFor(".o-bus-ConnectionAlert")).toHaveText("Real-time connection lost...");
    await runAllTimers();
    await animationFrame();
    expect(".o-bus-ConnectionAlert").toHaveText("Real-time connection lost...");
    unlockWebsocket();
    await runAllTimers();
    await waitForSteps(["reconnect"]);
    await waitForNone(".o-bus-ConnectionAlert");
});
