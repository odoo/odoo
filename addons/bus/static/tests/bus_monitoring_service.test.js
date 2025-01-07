import {
    defineBusModels,
    lockBusServiceStart,
    lockWebsocketConnect,
} from "@bus/../tests/bus_test_helpers";
import { busMonitoringservice } from "@bus/services/bus_monitoring_service";
import { WEBSOCKET_CLOSE_CODES, WORKER_STATE } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";
import {
    asyncStep,
    makeMockEnv,
    MockServer,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { Deferred } from "@odoo/hoot-dom";

defineBusModels();
describe.current.tags("desktop");

function stepConnectionStateChanges() {
    patchWithCleanup(busMonitoringservice, {
        start() {
            const api = super.start(...arguments);
            Object.defineProperty(api, "isConnectionLost", {
                get() {
                    return this._isConnectionLost;
                },
                set(value) {
                    if (value === this._isConnectionLost) {
                        return;
                    }
                    this._isConnectionLost = value;
                    asyncStep(`isConnectionLost - ${value}`);
                },
                configurable: true,
                enumerable: true,
            });
            return api;
        },
    });
}

test("connection considered as lost after failed reconnect attempt", async () => {
    stepConnectionStateChanges();
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    const def = new Deferred();
    env.services.bus_service.addEventListener("worker_state_updated", ({ detail }) => {
        if (detail === WORKER_STATE.DISCONNECTED) {
            def.resolve();
        }
    });
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["isConnectionLost - false", "connect"]);
    const unlockWebsocket = lockWebsocketConnect();
    MockServer.current.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE
    );
    await def;
    await runAllTimers();
    await waitForSteps([`isConnectionLost - true`]);
    unlockWebsocket();
    await waitForSteps([`isConnectionLost - false`]);
});

test("brief disconect not considered lost", async () => {
    stepConnectionStateChanges();
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["isConnectionLost - false", "connect"]);
    MockServer.current.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.SESSION_EXPIRED);
    await waitForSteps(["reconnect"]); // Only reconnect step, which means the monitoring state didn't change.
});

test("computer sleep doesn't mark connection as lost", async () => {
    stepConnectionStateChanges();
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["isConnectionLost - false", "connect"]);
    patchWithCleanup(navigator, { onLine: false });
    browser.dispatchEvent(new Event("offline")); // Offline event is triggered when the computer goes to sleep.
    const unlockWebsocket = lockWebsocketConnect();
    await waitForSteps(["disconnect"]);
    patchWithCleanup(navigator, { onLine: true });
    browser.dispatchEvent(new Event("online")); // Online event is triggered when the computer wakes up.
    unlockWebsocket();
    await runAllTimers();
    await waitForSteps(["connect"]);
    expect(env.services["bus.monitoring_service"].isConnectionLost).toBe(false);
});
