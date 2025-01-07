import {
    defineBusModels,
    lockBusServiceStart,
    lockWebsocketConnect,
} from "@bus/../tests/bus_test_helpers";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { queryFirst, runAllTimers, waitFor, waitUntil } from "@odoo/hoot-dom";
import {
    asyncStep,
    MockServer,
    mountWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

defineBusModels();
describe.current.tags("desktop");

test("show warning when bus connection encounters issues", async () => {
    const unlockBus = lockBusServiceStart();
    const { env } = await mountWithCleanup(WebClient);
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("reconnecting", () => asyncStep("reconnecting"));
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    const unlockWebsocket = lockWebsocketConnect();
    MockServer.current.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE
    );
    await waitForSteps(["reconnecting"]);
    await runAllTimers();
    const alert = await waitFor(".o-bus-ConnectionAlert");
    expect(alert).toHaveText("Real-time connection lost...");
    await runAllTimers();
    expect(alert).toHaveText("Real-time connection lost...");
    unlockWebsocket();
    await waitForSteps(["reconnect"]);
    await runAllTimers();
    await waitUntil(() => !queryFirst(".o-bus-ConnectionAlert"));
});
