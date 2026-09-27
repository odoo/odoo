import {
    addBusServiceListeners,
    defineBusModels,
    lockWebsocketConnect,
} from "@bus/../tests/bus_test_helpers";
import { BusMonitoringPlugin } from "@bus/services/bus_monitoring_plugin";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, runAllTimers } from "@odoo/hoot-dom";
import {
    getService,
    makeTestApp,
    MockServer,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { useOnChange } from "@odoo/owl";

defineBusModels();
describe.current.tags("desktop");

function stepConnectionStateChanges() {
    patchWithCleanup(BusMonitoringPlugin.prototype, {
        setup() {
            super.setup();

            useOnChange(
                () => [this.isConnectionLost()],
                () => {
                    expect.step(`isConnectionLost - ${this.isConnectionLost()}`);
                }
            );
        },
    });
}

test("connection considered as lost after failed reconnect attempt", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => expect.step("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => expect.step("BUS:DISCONNECT")]
    );
    stepConnectionStateChanges();
    await makeTestApp();
    await expect.waitForSteps(["isConnectionLost - false", "BUS:CONNECT"]);
    const unlockWebsocket = lockWebsocketConnect();
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await expect.waitForSteps(["BUS:DISCONNECT"]);
    await runAllTimers();
    await expect.waitForSteps(["isConnectionLost - true"]);
    unlockWebsocket();
    await runAllTimers();
    await expect.waitForSteps(["isConnectionLost - false"]);
});

test("brief disconect not considered lost", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => expect.step("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => expect.step("BUS:DISCONNECT")],
        ["BUS:RECONNECT", () => expect.step("BUS:RECONNECT")]
    );
    stepConnectionStateChanges();
    await makeTestApp();
    await expect.waitForSteps(["isConnectionLost - false", "BUS:CONNECT"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.SESSION_EXPIRED);
    await expect.waitForSteps(["BUS:DISCONNECT"]);
    await runAllTimers();
    await expect.waitForSteps(["BUS:RECONNECT"]); // Only reconnect step, which means the monitoring state didn't change.
});

test("computer sleep doesn't mark connection as lost", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => expect.step("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => expect.step("BUS:DISCONNECT")],
        ["BUS:RECONNECT", () => expect.step("BUS:RECONNECT")]
    );
    stepConnectionStateChanges();
    await makeTestApp();
    await expect.waitForSteps(["isConnectionLost - false", "BUS:CONNECT"]);
    const unlockWebsocket = lockWebsocketConnect();
    patchWithCleanup(navigator, { onLine: false });
    await manuallyDispatchProgrammaticEvent(window, "offline"); // Offline event is triggered when the computer goes to sleep.
    await expect.waitForSteps(["BUS:DISCONNECT"]);
    patchWithCleanup(navigator, { onLine: true });
    await manuallyDispatchProgrammaticEvent(window, "online"); // Online event is triggered when the computer wakes up.
    unlockWebsocket();
    await runAllTimers();
    await expect.waitForSteps(["BUS:CONNECT"]);
    expect(getService(BusMonitoringPlugin).isConnectionLost()).toBe(false);
});
