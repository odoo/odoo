import {
    addBusServiceListeners,
    defineBusModels,
    lockWebsocketConnect,
} from "@bus/../tests/bus_test_helpers";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, runAllTimers } from "@odoo/hoot-dom";
import {
    asyncStep,
    getService,
    makeMockEnv,
    MockServer,
    mockService,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

defineBusModels();
describe.current.tags("desktop");

function stepConnectionStateChanges() {
    mockService("bus.monitoring_service", {
        get isConnectionLost() {
            return this._isConnectionLost;
        },
        set isConnectionLost(value) {
            if (value !== this._isConnectionLost) {
                asyncStep(`isConnectionLost - ${value}`);
            }
            this._isConnectionLost = value;
        },
    });
}

test("connection considered as lost after failed reconnect attempt", async () => {
    stepConnectionStateChanges();
    addBusServiceListeners(
        ["connect", () => asyncStep("connect")],
        ["disconnect", () => asyncStep("disconnect")]
    );
    await makeMockEnv();
    await waitForSteps(["isConnectionLost - false", "connect"]);
    const unlockWebsocket = lockWebsocketConnect();
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["disconnect"]);
    await runAllTimers();
    await waitForSteps(["isConnectionLost - true"]);
    unlockWebsocket();
    await runAllTimers();
    await waitForSteps(["isConnectionLost - false"]);
});

test("brief disconect not considered lost", async () => {
    stepConnectionStateChanges();
    addBusServiceListeners(
        ["connect", () => asyncStep("connect")],
        ["disconnect", () => asyncStep("disconnect")],
        ["reconnect", () => asyncStep("reconnect")]
    );
    await makeMockEnv();
    await waitForSteps(["isConnectionLost - false", "connect"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.SESSION_EXPIRED);
    await waitForSteps(["disconnect"]);
    await runAllTimers();
    await waitForSteps(["reconnect"]); // Only reconnect step, which means the monitoring state didn't change.
});

test("computer sleep doesn't mark connection as lost", async () => {
    stepConnectionStateChanges();
    addBusServiceListeners(
        ["connect", () => asyncStep("connect")],
        ["disconnect", () => asyncStep("disconnect")],
        ["reconnect", () => asyncStep("reconnect")]
    );
    await makeMockEnv();
    await waitForSteps(["isConnectionLost - false", "connect"]);
    const unlockWebsocket = lockWebsocketConnect();
    patchWithCleanup(navigator, { onLine: false });
    await manuallyDispatchProgrammaticEvent(window, "offline"); // Offline event is triggered when the computer goes to sleep.
    await waitForSteps(["disconnect"]);
    patchWithCleanup(navigator, { onLine: true });
    await manuallyDispatchProgrammaticEvent(window, "online"); // Online event is triggered when the computer wakes up.
    unlockWebsocket();
    await runAllTimers();
    await waitForSteps(["connect"]);
    expect(getService("bus.monitoring_service").isConnectionLost).toBe(false);
});
