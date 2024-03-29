/** @odoo-module **/

import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";
import {
    waitForBusEvent,
    waitForChannels,
    waitNotifications,
    waitUntilSubscribe,
    waitForWorkerEvent,
} from "@bus/../tests/helpers/websocket_event_deferred";
import { busParametersService } from "@bus/bus_parameters_service";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

QUnit.module("Bus");

QUnit.test("notifications received from the channel", async () => {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const env = await makeTestEnv({ activateMockServer: true });
    env.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "epsilon");
    await waitNotifications([env, "notifType", "beta"], [env, "notifType", "epsilon"]);
});

QUnit.test("notifications not received after stoping the service", async () => {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const firstTabEnv = await makeTestEnv({ activateMockServer: true });
    const secondTabEnv = await makeTestEnv({ activateMockServer: true });
    firstTabEnv.services["bus_service"].start();
    secondTabEnv.services["bus_service"].start();
    firstTabEnv.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
    // both tabs should receive the notification
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications(
        [firstTabEnv, "notifType", "beta"],
        [secondTabEnv, "notifType", "beta"]
    );
    secondTabEnv.services["bus_service"].stop();
    await waitForWorkerEvent("leave");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "epsilon");
    await waitNotifications(
        [firstTabEnv, "notifType", "epsilon"],
        [secondTabEnv, "notifType", "epsilon", { received: false }]
    );
});

QUnit.test("notifications still received after disconnect/reconnect", async () => {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const env = await makeTestEnv({ activateMockServer: true });
    env.services["bus_service"].addChannel("lambda");
    await Promise.all([waitForBusEvent(env, "connect"), waitForChannels(["lambda"])]);
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications([env, "notifType", "beta"]);
    pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForBusEvent(env, "reconnect");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "gamma");
    await waitNotifications([env, "notifType", "gamma"]);
});

QUnit.test("tabs share message from a channel", async () => {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const mainEnv = await makeTestEnv({ activateMockServer: true });
    mainEnv.services["bus_service"].addChannel("lambda");
    const slaveEnv = await makeTestEnv();
    slaveEnv.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await waitNotifications([mainEnv, "notifType", "beta"], [slaveEnv, "notifType", "beta"]);
});

QUnit.test("second tab still receives notifications after main pagehide", async () => {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const mainEnv = await makeTestEnv({ activateMockServer: true });
    mainEnv.services["bus_service"].addChannel("lambda");
    // prevent second tab from receiving pagehide event.
    patchWithCleanup(browser, {
        addEventListener(eventName, callback) {
            if (eventName === "pagehide") {
                return;
            }
            super.addEventListener(eventName, callback);
        },
    });
    const secondEnv = await makeTestEnv({ activateMockServer: true });
    secondEnv.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
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

QUnit.test("two tabs adding a different channel", async () => {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const firstTabEnv = await makeTestEnv({ activateMockServer: true });
    const secondTabEnv = await makeTestEnv({ activateMockServer: true });
    firstTabEnv.services["bus_service"].addChannel("alpha");
    secondTabEnv.services["bus_service"].addChannel("beta");
    await waitUntilSubscribe("alpha", "beta");
    pyEnv["bus.bus"]._sendmany([
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

QUnit.test("channel management from multiple tabs", async (assert) => {
    await startServer();
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            assert.step(`${event_name} - [${data.channels.toString()}]`);
            super._sendToServer(...arguments);
        },
    });
    const firstTabEnv = await makeTestEnv({ activateMockServer: true });
    const secTabEnv = await makeTestEnv({ activateMockServer: true });
    firstTabEnv.services["bus_service"].addChannel("channel1");
    await waitForChannels(["channel1"]);
    // this should not trigger a subscription since the channel1 was
    // aleady known.
    secTabEnv.services["bus_service"].addChannel("channel1");
    await waitForChannels(["channel1"]);
    // removing channel1 from first tab should not trigger
    // re-subscription since the second tab still listens to this
    // channel.
    firstTabEnv.services["bus_service"].deleteChannel("channel1");
    await waitForChannels(["channel1"], { operation: "delete" });
    // this should trigger a subscription since the channel2 was not
    // known.
    secTabEnv.services["bus_service"].addChannel("channel2");
    await waitUntilSubscribe("channel2");
    assert.verifySteps(["subscribe - [channel1]", "subscribe - [channel1,channel2]"]);
});

QUnit.test("channels subscription after disconnection", async (assert) => {
    await startServer();
    addBusServicesToRegistry();
    const worker = patchWebsocketWorkerWithCleanup();
    const env = await makeTestEnv({ activateMockServer: true });
    env.services["bus_service"].start();
    await waitUntilSubscribe();
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT);
    await Promise.all([waitForBusEvent(env, "reconnect"), waitUntilSubscribe()]);
    assert.ok(
        true,
        "No error means waitUntilSubscribe resolves twice thus two subscriptions were triggered as expected"
    );
});

QUnit.test("Last notification id is passed to the worker on service start", async (assert) => {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    let updateLastNotificationDeferred = makeDeferred();
    patchWebsocketWorkerWithCleanup({
        _onClientMessage(_, { action, data }) {
            if (action === "initialize_connection") {
                assert.step(`${action} - ${data["lastNotificationId"]}`);
                updateLastNotificationDeferred.resolve();
            }
            return super._onClientMessage(...arguments);
        },
    });
    const env1 = await makeTestEnv();
    env1.services["bus_service"].start();
    env1.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
    await updateLastNotificationDeferred;
    // First bus service has never received notifications thus the
    // default is 0.
    assert.verifySteps(["initialize_connection - 0"]);
    pyEnv["bus.bus"]._sendmany([
        ["lambda", "notifType", "beta"],
        ["lambda", "notifType", "beta"],
    ]);
    await waitForBusEvent(env1, "notification");
    updateLastNotificationDeferred = makeDeferred();
    const env2 = await makeTestEnv();
    await env2.services["bus_service"].start();
    await updateLastNotificationDeferred;
    // Second bus service sends the last known notification id.
    assert.verifySteps([`initialize_connection - 2`]);
});

QUnit.test("Websocket disconnects upon user log out", async () => {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup();
    // first tab connects to the worker with user logged.
    patchWithCleanup(session, { user_id: 1 });
    const firstTabEnv = await makeTestEnv();
    firstTabEnv.services["bus_service"].start();
    await waitForBusEvent(firstTabEnv, "connect");
    // second tab connects to the worker after disconnection: user_id
    // is now false.
    patchWithCleanup(session, { user_id: false });
    const env2 = await makeTestEnv();
    env2.services["bus_service"].start();
    await waitForBusEvent(firstTabEnv, "disconnect");
});

QUnit.test("Websocket reconnects upon user log in", async () => {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup();
    // first tab connects to the worker with no user logged.
    patchWithCleanup(session, { user_id: false });
    const firstTabEnv = await makeTestEnv();
    firstTabEnv.services["bus_service"].start();
    await waitForBusEvent(firstTabEnv, "connect");
    // second tab connects to the worker after connection: user_id
    // is now set.
    patchWithCleanup(session, { user_id: 1 });
    const secondTabEnv = await makeTestEnv();
    secondTabEnv.services["bus_service"].start();
    await Promise.all([
        waitForBusEvent(firstTabEnv, "disconnect"),
        waitForBusEvent(firstTabEnv, "connect"),
    ]);
});

QUnit.test("WebSocket connects with URL corresponding to given serverURL", async (assert) => {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup();
    const serverURL = "http://random-website.com";
    patchWithCleanup(busParametersService, {
        start() {
            return {
                ...super.start(...arguments),
                serverURL,
            };
        },
    });
    const websocketCreatedDeferred = makeDeferred();
    patchWithCleanup(window, {
        WebSocket: function (url) {
            assert.step(url);
            websocketCreatedDeferred.resolve();
            return new EventTarget();
        },
    });
    const env = await makeTestEnv();
    env.services["bus_service"].start();
    await websocketCreatedDeferred;
    assert.verifySteps([`${serverURL.replace("http", "ws")}/websocket`]);
});

QUnit.test("Disconnect on offline, re-connect on online", async () => {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup();
    const env = await makeTestEnv();
    await env.services["bus_service"].start();
    await waitForBusEvent(env, "connect");
    window.dispatchEvent(new Event("offline"));
    await waitForBusEvent(env, "disconnect");
    window.dispatchEvent(new Event("online"));
    await waitForBusEvent(env, "connect");
});

QUnit.test("No disconnect on change offline/online when bus inactive", async () => {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup();
    const env = await makeTestEnv();
    window.dispatchEvent(new Event("offline"));
    await waitForBusEvent(env, "disconnect", { received: false });
    window.dispatchEvent(new Event("online"));
    await waitForBusEvent(env, "connect", { received: false });
});

QUnit.test("Can reconnect after late close event", async (assert) => {
    addBusServicesToRegistry();
    let subscribeSent = 0;
    const closeDeferred = makeDeferred();
    const worker = patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name }) {
            if (event_name === "subscribe") {
                subscribeSent++;
            }
        },
    });
    const pyEnv = await startServer();
    const env = await makeTestEnv();
    env.services["bus_service"].start();
    await waitForBusEvent(env, "connect");
    patchWithCleanup(worker.websocket, {
        close(code = WEBSOCKET_CLOSE_CODES.CLEAN, reason) {
            this.readyState = 2;
            if (code === WEBSOCKET_CLOSE_CODES.CLEAN) {
                closeDeferred.then(() => {
                    // Simulate that the connection could not be closed cleanly.
                    super.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE, reason);
                });
            } else {
                super.close(code, reason);
            }
        },
    });
    // Connection will be closed when passing offline. But the close event
    // will be delayed to come after the next open event. The connection
    // will thus be in the closing state in the meantime.
    window.dispatchEvent(new Event("offline"));
    // Worker reconnects upon the reception of the online event.
    window.dispatchEvent(new Event("online"));
    await waitForBusEvent(env, "disconnect");
    await waitForBusEvent(env, "connect");
    // Trigger the close event, it shouldn't have any effect since it is
    // related to an old connection that is no longer in use.
    closeDeferred.resolve();
    await waitForBusEvent(env, "disconnect", { received: false });
    // Server closes the connection, the worker should reconnect.
    pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT);
    await waitForBusEvent(env, "reconnecting");
    await waitForBusEvent(env, "reconnect");
    // 3 connections were opened, so 3 subscriptions are expected.
    assert.strictEqual(subscribeSent, 3);
});

QUnit.test("Fallback on simple worker when shared worker failed to initialize", async (assert) => {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup();
    const originalSharedWorker = browser.SharedWorker;
    const originalWorker = browser.Worker;
    patchWithCleanup(browser, {
        SharedWorker: function (url, options) {
            assert.step("shared-worker creation");
            const sw = new originalSharedWorker(url, options);
            // Simulate error during shared worker creation.
            setTimeout(() => sw.dispatchEvent(new Event("error")));
            return sw;
        },
        Worker: function (url, options) {
            assert.step("worker creation");
            return new originalWorker(url, options);
        },
    });
    patchWithCleanup(window.console, {
        warn(message) {
            assert.step(message);
        },
    });
    const env = await makeTestEnv();
    env.services["bus_service"].start();
    await waitForBusEvent(env, "connect");
    assert.verifySteps([
        "shared-worker creation",
        'Error while loading "bus_service" SharedWorker, fallback on Worker.',
        "worker creation",
    ]);
});

QUnit.test("subscribe to single notification", async (assert) => {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const env = await makeTestEnv({ activateMockServer: true });
    env.services["bus_service"].start();
    const messageReceivedDeferred = makeDeferred();
    env.services["bus_service"].subscribe("message", (payload) => {
        assert.deepEqual({ body: "hello", id: 1 }, payload);
        assert.step("message");
        messageReceivedDeferred.resolve();
    });
    await waitUntilSubscribe();
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "message", {
        body: "hello",
        id: 1,
    });
    await messageReceivedDeferred;
    assert.verifySteps(["message"]);
});
