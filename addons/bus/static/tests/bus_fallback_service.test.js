import {
    addBusServiceListeners,
    defineBusModels,
    lockWebsocketConnect,
} from "@bus/../tests/bus_test_helpers";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";
import { getService, makeMockEnv, MockServer, mockService } from "@web/../tests/web_test_helpers";

defineBusModels();
describe.current.tags("desktop");

function stepConnectionStateChanges() {
    mockService("bus.monitoring_service", {
        get isConnectionLost() {
            return this._isConnectionLost;
        },
        set isConnectionLost(value) {
            if (value !== this._isConnectionLost) {
                expect.step(`isConnectionLost - ${value}`);
            }
            this._isConnectionLost = value;
            if (value) {
                window.dispatchEvent(new CustomEvent("bus:connection_lost"));
            }
        },
    });
}

test("bus fallback is started when disconnected", async () => {
    stepConnectionStateChanges();
    addBusServiceListeners(
        ["BUS:CONNECT", () => expect.step("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => expect.step("BUS:DISCONNECT")]
    );
    await makeMockEnv();
    const busFallbackService = getService("bus_fallback_service");
    busFallbackService.registerFallback(async () => {
        expect.step("fallback called");
    });

    await expect.waitForSteps(["isConnectionLost - false", "BUS:CONNECT"]);
    const unlockWebsocket = lockWebsocketConnect();
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await expect.waitForSteps(["BUS:DISCONNECT"]);
    await runAllTimers();
    await expect.waitForSteps(["isConnectionLost - true", "fallback called"]);
    unlockWebsocket();
    await runAllTimers();
    await expect.waitForSteps(["fallback called", "isConnectionLost - false"]);
});
