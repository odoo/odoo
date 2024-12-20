import {
    defineBusModels,
    lockBusServiceStart,
    waitForChannels,
    waitForWorkerEvent,
    waitNotifications,
} from "@bus/../tests/bus_test_helpers";
import { busParametersService } from "@bus/bus_parameters_service";
import { busService } from "@bus/services/bus_service";
import { WEBSOCKET_CLOSE_CODES, WORKER_STATE } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { Deferred, runAllTimers, waitFor } from "@odoo/hoot-dom";
import {
    asyncStep,
    contains,
    makeMockEnv,
    makeMockServer,
    MockServer,
    mountWithCleanup,
    patchWithCleanup,
    restoreRegistry,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { WebClient } from "@web/webclient/webclient";
import { patchWebsocketWorkerWithCleanup } from "./mock_websocket";

defineBusModels();
describe.current.tags("desktop");

test("notifications not received after stoping the service", async () => {
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    firstTabEnv.services.bus_service.start();
    secondTabEnv.services.bus_service.start();
    firstTabEnv.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    const pyEnv = MockServer.current.env;
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications(
        [firstTabEnv, "notifType", "beta"],
        [secondTabEnv, "notifType", "beta"]
    );
    secondTabEnv.services.bus_service.stop();
    await waitForWorkerEvent("leave");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "epsilon");
    await waitNotifications(
        [firstTabEnv, "notifType", "epsilon"],
        [secondTabEnv, "notifType", "epsilon", { received: false }]
    );
});

test("notifications still received after disconnect/reconnect", async () => {
    const env = await makeMockEnv();
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    env.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    const pyEnv = MockServer.current.env;
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications([env, "notifType", "beta"]);
    pyEnv["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["reconnect"]);
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "gamma");
    await waitNotifications([env, "notifType", "gamma"]);
});

test("notifications are received by each tab", async () => {
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    firstTabEnv.services.bus_service.addChannel("lambda");
    secondTabEnv.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    MockServer.current.env["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications(
        [firstTabEnv, "notifType", "beta"],
        [secondTabEnv, "notifType", "beta"]
    );
});

test("second tab still receives notifications after main pagehide", async () => {
    const mainEnv = await makeMockEnv();
    restoreRegistry(registry);
    // Prevent second tab from receiving pagehide event.
    patchWithCleanup(browser, {
        addEventListener(eventName, callback) {
            if (eventName != "pagehide") {
                super.addEventListener(eventName, callback);
            }
        },
    });
    const secondEnv = await makeMockEnv(null, { makeNew: true });
    mainEnv.services.bus_service.addChannel("lambda");
    secondEnv.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    const pyEnv = MockServer.current.env;
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications([mainEnv, "notifType", "beta"], [secondEnv, "notifType", "beta"]);
    // simulate unloading main
    window.dispatchEvent(new Event("pagehide"));
    await waitForWorkerEvent("leave");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "gamma");
    await waitNotifications(
        [mainEnv, "notifType", "gamma", { received: false }],
        [secondEnv, "notifType", "gamma"]
    );
});

test("add two different channels from different tabs", async () => {
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    firstTabEnv.services.bus_service.addChannel("alpha");
    secondTabEnv.services.bus_service.addChannel("beta");
    await waitForChannels(["alpha", "beta"]);
    MockServer.current.env["bus.bus"]._sendmany([
        ["alpha", "notifType", "alpha"],
        ["beta", "notifType", "beta"],
    ]);
    await waitNotifications(
        [firstTabEnv, "notifType", "alpha"],
        [secondTabEnv, "notifType", "alpha"],
        [firstTabEnv, "notifType", "beta"],
        [secondTabEnv, "notifType", "beta"]
    );
});

test("channel management from multiple tabs", async () => {
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                asyncStep(`${event_name} - [${data.channels.toString()}]`);
            }
            super._sendToServer(...arguments);
        },
    });
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    firstTabEnv.services.bus_service.addChannel("channel1");
    await waitForSteps(["subscribe - [channel1]"]);
    // Already known: no subscription.
    secondTabEnv.services.bus_service.addChannel("channel1");
    // Remove from tab1, but tab2 still listens: no subscription.
    firstTabEnv.services.bus_service.deleteChannel("channel1");
    // New channel: subscription.
    secondTabEnv.services.bus_service.addChannel("channel2");
    await waitForSteps(["subscribe - [channel1,channel2]"]);
    // Removing last listener of channel1: subscription.
    secondTabEnv.services.bus_service.deleteChannel("channel1");
    await waitForSteps(["subscribe - [channel2]"]);
});

test("re-subscribe on reconnect", async () => {
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                asyncStep(`${event_name} - [${data.channels.toString()}]`);
            }
            super._sendToServer(...arguments);
        },
    });
    const env = await makeMockEnv();
    await env.services.bus_service.start();
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    await waitForSteps(["subscribe - []"]);
    MockServer.current.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT
    );
    await waitForSteps(["reconnect", "subscribe - []"]);
});

test("pass last notification id on initialization", async () => {
    patchWebsocketWorkerWithCleanup({
        _onClientMessage(_, { action, data }) {
            if (action === "initialize_connection") {
                asyncStep(`${action} - ${data["lastNotificationId"]}`);
            }
            return super._onClientMessage(...arguments);
        },
    });
    const firstEnv = await makeMockEnv();
    firstEnv.services.bus_service.start();
    await waitForSteps(["initialize_connection - 0"]);
    firstEnv.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    MockServer.current.env["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications([firstEnv, "notifType", "beta"]);
    restoreRegistry(registry);
    const secondEnv = await makeMockEnv(null, { makeNew: true });
    await secondEnv.services.bus_service.start();
    await waitForSteps([`initialize_connection - 1`]);
});

test("websocket disconnects when user logs out", async () => {
    const unlockBus = lockBusServiceStart();
    patchWithCleanup(session, { user_id: null });
    patchWithCleanup(user, { userId: 1 });
    const firstTabEnv = await makeMockEnv();
    firstTabEnv.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    firstTabEnv.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    unlockBus();
    await firstTabEnv.services.bus_service.start();
    await waitForSteps(["connect"]);
    patchWithCleanup(user, { userId: null });
    restoreRegistry(registry);
    const env2 = await makeMockEnv(null, { makeNew: true });
    env2.services.bus_service.start();
    await waitForSteps(["disconnect"]);
});

test("websocket reconnects upon user log in", async () => {
    patchWithCleanup(session, { user_id: null });
    patchWithCleanup(user, { userId: false });
    const unlockBus = lockBusServiceStart();
    const firstTabEnv = await makeMockEnv();
    firstTabEnv.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    firstTabEnv.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    unlockBus();
    await firstTabEnv.services.bus_service.start();
    await waitForSteps(["connect"]);
    patchWithCleanup(user, { userId: 1 });
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    secondTabEnv.services.bus_service.start();
    await waitForSteps(["disconnect", "connect"]);
});

test("websocket connects with URL corresponding to given serverURL", async () => {
    const serverURL = "http://random-website.com";
    patchWithCleanup(busParametersService, {
        start() {
            return {
                ...super.start(...arguments),
                serverURL,
            };
        },
    });
    const env = await makeMockEnv();
    patchWithCleanup(window, {
        WebSocket: function (url) {
            asyncStep(url);
            return new EventTarget();
        },
    });
    await env.services.bus_service.start();
    await waitForSteps([
        `${serverURL.replace("http", "ws")}/websocket?version=${session.websocket_worker_version}`,
    ]);
});

test("disconnect on offline, re-connect on online", async () => {
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    browser.addEventListener("online", () => asyncStep("online"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    window.dispatchEvent(new Event("offline"));
    await waitForSteps(["disconnect"]);
    window.dispatchEvent(new Event("online"));
    await waitForSteps(["online"]);
    await runAllTimers();
    await waitForSteps(["connect"]);
});

test("no disconnect on offline/online when bus is inactive", async () => {
    patchWithCleanup(busService, {
        start() {
            // All the services are loaded in the test environment, ensure none
            // will start the bus by preventing calls to `start`/`addChannel`.
            return { ...super.start(...arguments), start: () => {}, addChannel: () => {} };
        },
    });
    const env = await makeMockEnv();
    expect(env.services.bus_service.isActive).toBe(false);
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    browser.addEventListener("online", () => asyncStep("online"));
    browser.addEventListener("offline", () => asyncStep("offline"));
    window.dispatchEvent(new Event("offline"));
    await waitForSteps(["offline"]);
    window.dispatchEvent(new Event("online"));
    await waitForSteps(["online"]);
});

test("can reconnect after late close event", async () => {
    const closeDeferred = new Deferred();
    const worker = patchWebsocketWorkerWithCleanup();
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    env.services.bus_service.addEventListener("reconnecting", () => asyncStep("reconnecting"));
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    browser.addEventListener("online", () => asyncStep("online"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    patchWithCleanup(worker.websocket, {
        close(code = WEBSOCKET_CLOSE_CODES.CLEAN, reason) {
            this.readyState = 2; // WebSocket.CLOSING
            if (code === WEBSOCKET_CLOSE_CODES.CLEAN) {
                closeDeferred.then(() => {
                    // Simulate that the connection could not be closed cleanly.
                    super.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE, reason);
                });
                return;
            }
            super.close(code, reason);
        },
    });
    // Connection will be closed when passing offline. But the close event will
    // be delayed to come after the next open event. The connection will thus be
    // in the closing state in the meantime (Simulates pending TCP closing
    // handshake).
    window.dispatchEvent(new Event("offline"));
    // Worker reconnects upon the reception of the online event.
    window.dispatchEvent(new Event("online"));
    await waitForSteps(["online"]);
    await runAllTimers();
    await waitForSteps(["disconnect", "connect"]);
    // Trigger the close event, it shouldn't have any effect since it is
    // related to an old connection that is no longer in use.
    closeDeferred.resolve();
    await waitForSteps([]);
    // Server closes the connection, the worker should reconnect.
    MockServer.current.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT
    );
    await waitForSteps(["disconnect", "reconnecting", "reconnect"]);
});

test("fallback on simple worker when shared worker failed to initialize", async () => {
    // Starting the server first, the following patch would be overwritten otherwise.
    await makeMockServer();
    const OgSW = browser.SharedWorker;
    const OgWorker = browser.Worker;
    patchWithCleanup(browser, {
        SharedWorker: function (url, options) {
            asyncStep("shared-worker-creation");
            const sw = new OgSW(url, options);
            // Simulate error during shared worker creation.
            setTimeout(() => sw.dispatchEvent(new Event("error")));
            return sw;
        },
        Worker: function (url, options) {
            asyncStep("worker-creation");
            return new OgWorker(url, options);
        },
    });
    patchWithCleanup(window.console, { warn: (message) => asyncStep(message) });
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps([
        "shared-worker-creation",
        'Error while loading "bus_service" SharedWorker, fallback on Worker.',
        "worker-creation",
        "connect",
    ]);
});

test("subscribe to single notification", async () => {
    const env = await makeMockEnv();
    await env.services.bus_service.start();
    env.services.bus_service.addChannel("my_channel");
    await waitForChannels(["my_channel"]);
    env.services.bus_service.subscribe("message_type", (payload) =>
        asyncStep(`message - ${JSON.stringify(payload)}`)
    );
    MockServer.current.env["bus.bus"]._sendone("my_channel", "message_type", {
        body: "hello",
        id: 1,
    });
    await waitForSteps(['message - {"body":"hello","id":1}']);
});

test("do not reconnect when worker version is outdated", async () => {
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    const worker = patchWebsocketWorkerWithCleanup();
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    expect(worker.state).toBe(WORKER_STATE.CONNECTED);
    const pyEnv = MockServer.current.env;
    pyEnv["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["disconnect", "reconnect"]);
    expect(worker.state).toBe(WORKER_STATE.CONNECTED);
    patchWithCleanup(console, { warn: (message) => asyncStep(message) });
    pyEnv["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.CLEAN, "OUTDATED_VERSION");
    await waitForSteps(["Worker deactivated due to an outdated version.", "disconnect"]);
    await env.services.bus_service.start();
    await waitForWorkerEvent("start");
    // Verify the worker state instead of the steps as the connect event is
    // asynchronous and may not be fired at this point.
    expect(worker.state).toBe(WORKER_STATE.DISCONNECTED);
});

test("reconnect on demande after clean close code", async () => {
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    const pyEnv = MockServer.current.env;
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("reconnect", () => asyncStep("reconnect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    pyEnv["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["disconnect", "reconnect"]);
    pyEnv["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.CLEAN);
    await waitForSteps(["disconnect"]);
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
});

test("remove from main tab candidates when version is outdated", async () => {
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    patchWithCleanup(env.services.multi_tab, { isOnMainTab: () => true });
    patchWithCleanup(console, { warn: (message) => asyncStep(message) });
    env.services.multi_tab.bus.addEventListener("no_longer_main_tab", () =>
        asyncStep("no_longer_main_tab")
    );
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    expect(env.services.multi_tab.isOnMainTab()).toBe(true);
    MockServer.current.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.CLEAN,
        "OUTDATED_VERSION"
    );
    await waitForSteps([
        "Worker deactivated due to an outdated version.",
        "disconnect",
        "no_longer_main_tab",
    ]);
});

test("show notification when version is outdated", async () => {
    const unlockBus = lockBusServiceStart();
    const { env } = await mountWithCleanup(WebClient);
    patchWithCleanup(console, { warn: (message) => asyncStep(message) });
    patchWithCleanup(browser.location, { reload: () => asyncStep("reload") });
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    MockServer.current.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.CLEAN,
        "OUTDATED_VERSION"
    );
    await waitForSteps(["Worker deactivated due to an outdated version.", "disconnect"]);
    await waitFor(".o_notification", {
        text: "Save your work and refresh to get the latest updates and avoid potential issues.",
    });
    await contains(".o_notification button:contains(Refresh)").click();
    await waitForSteps(["reload"]);
});

test("subscribe message is sent first", async () => {
    // Starting the server first, the following patch would be overwritten otherwise.
    await makeMockServer();
    const ogSocket = window.WebSocket;
    patchWithCleanup(window, {
        WebSocket: function () {
            const ws = new ogSocket(...arguments);
            ws.send = (message) => {
                const evName = JSON.parse(message).event_name;
                if (["subscribe", "some_event", "some_other_event"].includes(evName)) {
                    asyncStep(evName);
                }
            };
            return ws;
        },
    });
    const env = await makeMockEnv();
    await env.services.bus_service.start();
    await waitForSteps(["subscribe"]);
    env.services.bus_service.send("some_event");
    await waitForSteps(["some_event"]);
    MockServer.current.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.CLEAN);
    env.services.bus_service.send("some_event");
    env.services.bus_service.send("some_other_event");
    env.services.bus_service.addChannel("channel_1");
    await waitForSteps([]);
    await env.services.bus_service.start();
    await waitForSteps(["subscribe", "some_event", "some_other_event"]);
});

test("worker state is available from the bus service", async () => {
    const unlockBus = lockBusServiceStart();
    const env = await makeMockEnv();
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.addEventListener("disconnect", () => asyncStep("disconnect"));
    unlockBus();
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    expect(env.services.bus_service.workerState).toBe(WORKER_STATE.CONNECTED);
    MockServer.current.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.CLEAN);
    await waitForSteps(["disconnect"]);
    expect(env.services.bus_service.workerState).toBe(WORKER_STATE.DISCONNECTED);
    await env.services.bus_service.start();
    await waitForSteps(["connect"]);
    expect(env.services.bus_service.workerState).toBe(WORKER_STATE.CONNECTED);
});
