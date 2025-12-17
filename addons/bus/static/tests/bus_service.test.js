import {
    addBusServiceListeners,
    defineBusModels,
    startBusService,
    stepWorkerActions,
    waitForChannels,
    waitNotifications,
} from "@bus/../tests/bus_test_helpers";
import {
    WEBSOCKET_CLOSE_CODES,
    WebsocketWorker,
    WORKER_STATE,
} from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { Deferred, manuallyDispatchProgrammaticEvent, runAllTimers, waitFor } from "@odoo/hoot-dom";
import { mockWebSocket } from "@odoo/hoot-mock";
import {
    asyncStep,
    contains,
    getService,
    makeMockEnv,
    makeMockServer,
    MockServer,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
    restoreRegistry,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { getWebSocketWorker, onWebsocketEvent } from "./mock_websocket";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { WebClient } from "@web/webclient/webclient";

defineBusModels();
describe.current.tags("desktop");

test("notifications not received after stoping the service", async () => {
    const firstTabEnv = await makeMockEnv();
    stepWorkerActions("BUS:LEAVE");
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    startBusService(firstTabEnv);
    startBusService(secondTabEnv);
    firstTabEnv.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    MockServer.env["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications(
        [firstTabEnv, "notifType", "beta"],
        [secondTabEnv, "notifType", "beta"]
    );
    secondTabEnv.services.bus_service.stop();
    await waitForSteps(["BUS:LEAVE"]);
    MockServer.env["bus.bus"]._sendone("lambda", "notifType", "epsilon");
    await waitNotifications(
        [firstTabEnv, "notifType", "epsilon"],
        [secondTabEnv, "notifType", "epsilon", { received: false }]
    );
});

test("notifications still received after disconnect/reconnect", async () => {
    addBusServiceListeners(
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")],
        ["BUS:RECONNECT", () => asyncStep("BUS:RECONNECT")]
    );
    await makeMockEnv();
    getService("bus_service").addChannel("lambda");
    await waitForChannels(["lambda"]);
    MockServer.env["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications(["notifType", "beta"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["BUS:DISCONNECT"]);
    await runAllTimers();
    await waitForSteps(["BUS:RECONNECT"]);
    MockServer.env["bus.bus"]._sendone("lambda", "notifType", "gamma");
    await waitNotifications(["notifType", "gamma"]);
});

test("notifications are received by each tab", async () => {
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    firstTabEnv.services.bus_service.addChannel("lambda");
    secondTabEnv.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    MockServer.env["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications(
        [firstTabEnv, "notifType", "beta"],
        [secondTabEnv, "notifType", "beta"]
    );
});

test("second tab still receives notifications after main pagehide", async () => {
    const mainEnv = await makeMockEnv();
    stepWorkerActions("BUS:LEAVE");
    mainEnv.services.bus_service.addChannel("lambda");
    // Prevent second tab from receiving pagehide event.
    patchWithCleanup(browser, {
        addEventListener(eventName, callback) {
            if (eventName !== "pagehide") {
                super.addEventListener(eventName, callback);
            }
        },
    });
    const worker = getWebSocketWorker();
    patchWithCleanup(worker, {
        _unregisterClient(client) {
            // Ensure that the worker does not receive any messages from the main tab
            // after pagehide, mimicking real-world behavior.
            client.onmessage = null;
            super._unregisterClient(client);
        },
    });
    restoreRegistry(registry);
    const secondEnv = await makeMockEnv(null, { makeNew: true });
    secondEnv.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    MockServer.env["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications([mainEnv, "notifType", "beta"], [secondEnv, "notifType", "beta"]);
    // simulate unloading main
    await manuallyDispatchProgrammaticEvent(window, "pagehide");
    await waitForSteps(["BUS:LEAVE"]);
    MockServer.env["bus.bus"]._sendone("lambda", "notifType", "gamma");
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
    MockServer.env["bus.bus"]._sendmany([
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
    onWebsocketEvent("subscribe", (data) => asyncStep(`subscribe - [${data.channels.toString()}]`));
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
    onWebsocketEvent("subscribe", (data) => asyncStep(`subscribe - [${data.channels.toString()}]`));
    addBusServiceListeners(["BUS:RECONNECT", () => asyncStep("BUS:RECONNECT")]);
    await makeMockEnv();
    startBusService();
    await waitForSteps(["subscribe - []"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT);
    await runAllTimers();
    await waitForSteps(["BUS:RECONNECT", "subscribe - []"]);
});

test("pass last notification id on initialization", async () => {
    patchWithCleanup(WebsocketWorker.prototype, {
        _onClientMessage(_client, { action, data }) {
            if (action === "BUS:INITIALIZE_CONNECTION") {
                asyncStep(`${action} - ${data["lastNotificationId"]}`);
            }
            return super._onClientMessage(...arguments);
        },
    });
    const firstEnv = await makeMockEnv();
    startBusService(firstEnv);
    await waitForSteps(["BUS:INITIALIZE_CONNECTION - 0"]);
    firstEnv.services.bus_service.addChannel("lambda");
    await waitForChannels(["lambda"]);
    MockServer.env["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications([firstEnv, "notifType", "beta"]);
    restoreRegistry(registry);
    const secondEnv = await makeMockEnv(null, { makeNew: true });
    startBusService(secondEnv);
    await waitForSteps([`BUS:INITIALIZE_CONNECTION - 1`]);
});

test("websocket disconnects when user logs out", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:RECONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]
    );
    patchWithCleanup(session, { user_id: null, db: "openerp" });
    patchWithCleanup(user, { userId: 1 });
    const firstTabEnv = await makeMockEnv();
    await startBusService(firstTabEnv);
    await waitForSteps(["BUS:CONNECT"]);
    // second tab connects to the worker, omitting the DB name. Consider same DB.
    patchWithCleanup(session, { db: undefined });
    restoreRegistry(registry);
    const env2 = await makeMockEnv(null, { makeNew: true });
    await startBusService(env2);
    await waitForSteps([]);
    // third tab connects to the worker after disconnection: userId is now false.
    patchWithCleanup(user, { userId: false });
    restoreRegistry(registry);
    const env3 = await makeMockEnv(null, { makeNew: true });
    await startBusService(env3);
    await waitForSteps(["BUS:DISCONNECT", "BUS:CONNECT"]);
});

test("websocket reconnects upon user log in", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]
    );
    patchWithCleanup(session, { user_id: null });
    patchWithCleanup(user, { userId: false });
    await makeMockEnv();
    startBusService();
    await waitForSteps(["BUS:CONNECT"]);
    patchWithCleanup(user, { userId: 1 });
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    startBusService(secondTabEnv);
    await waitForSteps(["BUS:DISCONNECT", "BUS:CONNECT"]);
});

test("websocket connects with URL corresponding to given serverURL", async () => {
    const serverURL = "http://random-website.com";
    mockService("bus.parameters", { serverURL });
    await makeMockEnv();
    mockWebSocket((ws) => asyncStep(ws.url));
    startBusService();
    await waitForSteps([
        `${serverURL.replace("http", "ws")}/websocket?version=${session.websocket_worker_version}`,
    ]);
});

test("disconnect on offline, re-connect on online", async () => {
    browser.addEventListener("online", () => asyncStep("online"));
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]
    );
    await makeMockEnv();
    startBusService();
    await waitForSteps(["BUS:CONNECT"]);
    manuallyDispatchProgrammaticEvent(window, "offline");
    await waitForSteps(["BUS:DISCONNECT"]);
    manuallyDispatchProgrammaticEvent(window, "online");
    await waitForSteps(["online"]);
    await runAllTimers();
    await waitForSteps(["BUS:CONNECT"]);
});

test("no disconnect on offline/online when bus is inactive", async () => {
    browser.addEventListener("online", () => asyncStep("online"));
    browser.addEventListener("offline", () => asyncStep("offline"));
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]
    );
    mockService("bus_service", {
        addChannel() {},
    });
    await makeMockEnv();
    expect(getService("bus_service").isActive).toBe(false);
    manuallyDispatchProgrammaticEvent(window, "offline");
    await waitForSteps(["offline"]);
    manuallyDispatchProgrammaticEvent(window, "online");
    await waitForSteps(["online"]);
});

test("can reconnect after late close event", async () => {
    browser.addEventListener("online", () => asyncStep("online"));
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")],
        ["BUS:RECONNECT", () => asyncStep("BUS:RECONNECT")],
        ["BUS:RECONNECTING", () => asyncStep("BUS:RECONNECTING")]
    );
    const closeDeferred = new Deferred();
    await makeMockEnv();
    startBusService();
    await waitForSteps(["BUS:CONNECT"]);
    patchWithCleanup(getWebSocketWorker().websocket, {
        async close(code = WEBSOCKET_CLOSE_CODES.CLEAN, reason) {
            this._readyState = 2; // WebSocket.CLOSING
            if (code === WEBSOCKET_CLOSE_CODES.CLEAN) {
                // Simulate that the connection could not be closed cleanly.
                await closeDeferred;
                code = WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE;
            }
            return super.close(code, reason);
        },
    });
    // Connection will be closed when passing offline. But the close event will
    // be delayed to come after the next open event. The connection will thus be
    // in the closing state in the meantime (Simulates pending TCP closing
    // handshake).
    manuallyDispatchProgrammaticEvent(window, "offline");
    // Worker reconnects upon the reception of the online event.
    manuallyDispatchProgrammaticEvent(window, "online");
    await waitForSteps(["online"]);
    await runAllTimers();
    await waitForSteps(["BUS:DISCONNECT", "BUS:CONNECT"]);
    // Trigger the close event, it shouldn't have any effect since it is
    // related to an old connection that is no longer in use.
    closeDeferred.resolve();
    await waitForSteps([]);
    // Server closes the connection, the worker should reconnect.
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT);
    await waitForSteps(["BUS:DISCONNECT", "BUS:RECONNECTING", "BUS:RECONNECT"]);
});

test("fallback on simple worker when shared worker failed to initialize", async () => {
    addBusServiceListeners(["BUS:CONNECT", () => asyncStep("BUS:CONNECT")]);
    // Starting the server first, the following patch would be overwritten otherwise.
    await makeMockServer();
    patchWithCleanup(browser, {
        SharedWorker: class extends browser.SharedWorker {
            constructor() {
                super(...arguments);
                asyncStep("shared-worker-creation");
                setTimeout(() => this.dispatchEvent(new Event("error")));
            }
        },
        Worker: class extends browser.Worker {
            constructor() {
                super(...arguments);

                asyncStep("worker-creation");
            }
        },
    });
    patchWithCleanup(console, {
        warn: (message) => asyncStep(message),
    });
    await makeMockEnv();
    startBusService();
    await waitForSteps([
        "shared-worker-creation",
        "Error while loading SharedWorker, fallback on Worker: ",
        "worker-creation",
        "BUS:CONNECT",
    ]);
});

test("subscribe to single notification", async () => {
    await makeMockEnv();
    startBusService();
    getService("bus_service").addChannel("my_channel");
    await waitForChannels(["my_channel"]);
    getService("bus_service").subscribe("message_type", (payload) =>
        asyncStep(`message - ${JSON.stringify(payload)}`)
    );
    MockServer.env["bus.bus"]._sendone("my_channel", "message_type", { body: "hello", id: 1 });
    await waitForSteps(['message - {"body":"hello","id":1}']);
});

test("do not reconnect when worker version is outdated", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")],
        ["BUS:RECONNECT", () => asyncStep("BUS:RECONNECT")]
    );
    await makeMockEnv();
    startBusService();
    await runAllTimers();
    await waitForSteps(["BUS:CONNECT"]);
    const worker = getWebSocketWorker();
    expect(worker.state).toBe(WORKER_STATE.CONNECTED);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["BUS:DISCONNECT"]);
    await runAllTimers();
    await waitForSteps(["BUS:RECONNECT"]);
    expect(worker.state).toBe(WORKER_STATE.CONNECTED);
    patchWithCleanup(console, { warn: (message) => asyncStep(message) });
    MockServer.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.CLEAN,
        "OUTDATED_VERSION"
    );
    await waitForSteps(["Worker deactivated due to an outdated version.", "BUS:DISCONNECT"]);
    await runAllTimers();
    stepWorkerActions("BUS:START");
    startBusService();
    await runAllTimers();
    await waitForSteps(["BUS:START"]);
    // Verify the worker state instead of the steps as the connect event is
    // asynchronous and may not be fired at this point.
    expect(worker.state).toBe(WORKER_STATE.DISCONNECTED);
});

test("reconnect on demande after clean close code", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")],
        ["BUS:RECONNECT", () => asyncStep("BUS:RECONNECT")]
    );
    await makeMockEnv();
    startBusService();
    await runAllTimers();
    await waitForSteps(["BUS:CONNECT"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["BUS:DISCONNECT"]);
    await runAllTimers();
    await waitForSteps(["BUS:RECONNECT"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.CLEAN);
    await waitForSteps(["BUS:DISCONNECT"]);
    await runAllTimers();
    startBusService();
    await waitForSteps(["BUS:CONNECT"]);
});

test("remove from main tab candidates when version is outdated", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]
    );
    await makeMockEnv();
    patchWithCleanup(console, { warn: (message) => asyncStep(message) });
    getService("multi_tab").bus.addEventListener("no_longer_main_tab", () =>
        asyncStep("no_longer_main_tab")
    );
    startBusService();
    await waitForSteps(["BUS:CONNECT"]);
    expect(await getService("multi_tab").isOnMainTab()).toBe(true);
    MockServer.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.CLEAN,
        "OUTDATED_VERSION"
    );
    await waitForSteps([
        "Worker deactivated due to an outdated version.",
        "BUS:DISCONNECT",
        "no_longer_main_tab",
    ]);
});

test("show notification when version is outdated", async () => {
    browser.location.addEventListener("reload", () => asyncStep("reload"));
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]
    );
    patchWithCleanup(console, { warn: (message) => asyncStep(message) });
    await mountWithCleanup(WebClient);
    await waitForSteps(["BUS:CONNECT"]);
    MockServer.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.CLEAN,
        "OUTDATED_VERSION"
    );
    await waitForSteps(["Worker deactivated due to an outdated version.", "BUS:DISCONNECT"]);
    await runAllTimers();
    await waitFor(".o_notification", {
        contains:
            "Save your work and refresh to get the latest updates and avoid potential issues.",
    });
    await contains(".o_notification button:contains(Refresh)").click();
    await waitForSteps(["reload"]);
});

test("subscribe message is sent first", async () => {
    addBusServiceListeners(["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]);
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
    await makeMockEnv();
    startBusService();
    await runAllTimers();
    await waitForSteps(["subscribe"]);
    getService("bus_service").send("some_event");
    await waitForSteps(["some_event"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.CLEAN);
    await waitForSteps(["BUS:DISCONNECT"]);
    getService("bus_service").send("some_event");
    getService("bus_service").send("some_other_event");
    getService("bus_service").addChannel("channel_1");
    await runAllTimers();
    await waitForSteps([]);
    startBusService();
    await runAllTimers();
    await waitForSteps(["subscribe", "some_event", "some_other_event"]);
});

test("worker state is available from the bus service", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]
    );
    await makeMockEnv();
    startBusService();
    await waitForSteps(["BUS:CONNECT"]);
    expect(getService("bus_service").workerState).toBe(WORKER_STATE.CONNECTED);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.CLEAN);
    await waitForSteps(["BUS:DISCONNECT"]);
    await runAllTimers();
    expect(getService("bus_service").workerState).toBe(WORKER_STATE.DISCONNECTED);
    startBusService();
    await waitForSteps(["BUS:CONNECT"]);
    expect(getService("bus_service").workerState).toBe(WORKER_STATE.CONNECTED);
});

test("channel is kept until deleted as many times as added", async () => {
    onWebsocketEvent("subscribe", (data) =>
        expect.step(`subscribe - [${data.channels.toString()}]`)
    );
    await makeMockEnv();
    const worker = getWebSocketWorker();
    patchWithCleanup(worker, {
        _deleteChannel() {
            super._deleteChannel(...arguments);
            expect.step("delete channel");
        },
        _addChannel(client, channel) {
            super._addChannel(client, channel);
            expect.step(`add channel - ${channel}`);
        },
    });
    startBusService();
    const busService = getService("bus_service");
    await expect.waitForSteps(["subscribe - []"]);
    busService.addChannel("foo");
    await expect.waitForSteps(["add channel - foo", "subscribe - [foo]"]);
    busService.addChannel("foo");
    await expect.waitForSteps(["add channel - foo"]);
    await runAllTimers();
    busService.deleteChannel("foo");
    await expect.waitForSteps(["delete channel"]);
    await runAllTimers();
    await expect.waitForSteps([]);
    busService.deleteChannel("foo");
    await expect.waitForSteps(["delete channel", "subscribe - []"]);
});
