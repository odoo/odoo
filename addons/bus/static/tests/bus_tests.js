/** @odoo-module **/

import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";
import { waitUntilSubscribe } from "@bus/../tests/helpers/websocket_event_deferred";
import { busParametersService } from "@bus/bus_parameters_service";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

QUnit.module("Bus");

QUnit.test("notifications received from the channel", async function (assert) {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const env = await makeTestEnv({ activateMockServer: true });
    await env.services["bus_service"].start();
    env.services["bus_service"].addEventListener("notification", ({ detail: notifications }) => {
        assert.step("notification - " + notifications.map((notif) => notif.payload).toString());
    });
    env.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await nextTick();

    pyEnv["bus.bus"]._sendone("lambda", "notifType", "epsilon");
    await nextTick();

    assert.verifySteps(["notification - beta", "notification - epsilon"]);
});

QUnit.test("notifications not received after stoping the service", async function (assert) {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const firstTabEnv = await makeTestEnv({ activateMockServer: true });
    const secondTabEnv = await makeTestEnv({ activateMockServer: true });
    await firstTabEnv.services["bus_service"].start();
    await secondTabEnv.services["bus_service"].start();

    firstTabEnv.services["bus_service"].addEventListener(
        "notification",
        ({ detail: notifications }) => {
            assert.step(
                "1 - notification - " + notifications.map((notif) => notif.payload).toString()
            );
        }
    );
    firstTabEnv.services["bus_service"].addChannel("lambda");
    secondTabEnv.services["bus_service"].addEventListener(
        "notification",
        ({ detail: notifications }) => {
            assert.step(
                "2 - notification - " + notifications.map((notif) => notif.payload).toString()
            );
        }
    );
    await waitUntilSubscribe("lambda");
    // both tabs should receive the notification
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await nextTick();
    secondTabEnv.services["bus_service"].stop();
    await nextTick();
    // only first tab should receive the notification since the
    // second tab has called the stop method.
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "epsilon");
    await nextTick();

    assert.verifySteps([
        "1 - notification - beta",
        "2 - notification - beta",
        "1 - notification - epsilon",
    ]);
});

QUnit.test("notifications still received after disconnect/reconnect", async function (assert) {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const env = await makeTestEnv({ activateMockServer: true });
    await env.services["bus_service"].start();
    env.services["bus_service"].addEventListener("notification", ({ detail: notifications }) => {
        assert.step("notification - " + notifications.map((notif) => notif.payload).toString());
    });
    env.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    // Give websocket worker a tick to try to restart
    await nextTick();
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "gamma");
    // Give bus service a tick to receive the notification from
    // postMessage.
    await nextTick();

    assert.verifySteps(["notification - beta", "notification - gamma"]);
});

QUnit.test("tabs share message from a channel", async function (assert) {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const steps = [];
    // main
    const mainEnv = await makeTestEnv({ activateMockServer: true });
    mainEnv.services["bus_service"].addEventListener(
        "notification",
        ({ detail: notifications }) => {
            steps.push(
                "main - notification - " + notifications.map((notif) => notif.payload).toString()
            );
        }
    );
    mainEnv.services["bus_service"].addChannel("lambda");

    // slave
    const slaveEnv = await makeTestEnv();
    slaveEnv.services["bus_service"].start();

    slaveEnv.services["bus_service"].addEventListener(
        "notification",
        ({ detail: notifications }) => {
            steps.push(
                "slave - notification - " + notifications.map((notif) => notif.payload).toString()
            );
        }
    );
    await slaveEnv.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    // Wait one tick for the worker `postMessage` to reach the bus_service.
    await nextTick();
    // Wait another tick for the `bus.trigger` to reach the listeners.
    await nextTick();

    assert.deepEqual(steps.sort(), ["main - notification - beta", "slave - notification - beta"]);
});

QUnit.test("second tab still receives notifications after main pagehide", async function (assert) {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const steps = [];
    // main
    const mainEnv = await makeTestEnv({ activateMockServer: true });
    mainEnv.services["bus_service"].start();
    mainEnv.services["bus_service"].addEventListener(
        "notification",
        ({ detail: notifications }) => {
            steps.push(
                "main - notification - " + notifications.map((notif) => notif.payload).toString()
            );
        }
    );
    mainEnv.services["bus_service"].addChannel("lambda");

    // second env
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
    secondEnv.services["bus_service"].addEventListener(
        "notification",
        ({ detail: notifications }) => {
            steps.push(
                "slave - notification - " + notifications.map((notif) => notif.payload).toString()
            );
        }
    );
    secondEnv.services["bus_service"].addChannel("lambda");
    await waitUntilSubscribe("lambda");
    pyEnv["bus.bus"]._sendone("lambda", "notifType", "beta");
    await nextTick();

    // simulate unloading main
    window.dispatchEvent(new Event("pagehide"));
    await nextTick();

    pyEnv["bus.bus"]._sendone("lambda", "notifType", "gamma");
    await nextTick();

    assert.deepEqual(steps.sort(), [
        "main - notification - beta",
        "slave - notification - beta",
        "slave - notification - gamma",
    ]);
});

QUnit.test("two tabs calling addChannel simultaneously", async function (assert) {
    addBusServicesToRegistry();
    const channelPatch = () => ({
        addChannel(channel) {
            assert.step("Tab " + this.__tabId__ + ": addChannel " + channel);
            super.addChannel(...arguments);
        },
        deleteChannel(channel) {
            assert.step("Tab " + this.__tabId__ + ": deleteChannel " + channel);
            super.deleteChannel(...arguments);
        },
    });
    const firstTabEnv = await makeTestEnv({ activateMockServer: true });
    const secondTabEnv = await makeTestEnv({ activateMockServer: true });
    firstTabEnv.services["bus_service"].__tabId__ = 1;
    secondTabEnv.services["bus_service"].__tabId__ = 2;
    patchWithCleanup(firstTabEnv.services["bus_service"], channelPatch());
    patchWithCleanup(secondTabEnv.services["bus_service"], channelPatch());
    firstTabEnv.services["bus_service"].addChannel("alpha");
    secondTabEnv.services["bus_service"].addChannel("alpha");
    firstTabEnv.services["bus_service"].addChannel("beta");
    secondTabEnv.services["bus_service"].addChannel("beta");

    await waitUntilSubscribe("alpha", "beta");

    assert.verifySteps([
        "Tab 1: addChannel alpha",
        "Tab 2: addChannel alpha",
        "Tab 1: addChannel beta",
        "Tab 2: addChannel beta",
    ]);
});

QUnit.test("two tabs adding a different channel", async function (assert) {
    addBusServicesToRegistry();
    const pyEnv = await startServer();
    const firstTabEnv = await makeTestEnv({ activateMockServer: true });
    const secondTabEnv = await makeTestEnv({ activateMockServer: true });
    firstTabEnv.services["bus_service"].addEventListener(
        "notification",
        ({ detail: notifications }) => {
            assert.step(
                "first - notification - " + notifications.map((notif) => notif.payload).toString()
            );
        }
    );
    secondTabEnv.services["bus_service"].addEventListener(
        "notification",
        ({ detail: notifications }) => {
            assert.step(
                "second - notification - " + notifications.map((notif) => notif.payload).toString()
            );
        }
    );
    firstTabEnv.services["bus_service"].addChannel("alpha");
    secondTabEnv.services["bus_service"].addChannel("beta");
    await waitUntilSubscribe("alpha", "beta");
    pyEnv["bus.bus"]._sendmany([
        ["alpha", "notifType", "alpha"],
        ["beta", "notifType", "beta"],
    ]);
    await nextTick();

    assert.verifySteps(["first - notification - alpha,beta", "second - notification - alpha,beta"]);
});

QUnit.test("channel management from multiple tabs", async function (assert) {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            assert.step(`${event_name} - [${data.channels.toString()}]`);
            super._sendToServer(...arguments);
        },
    });

    const firstTabEnv = await makeTestEnv();
    const secTabEnv = await makeTestEnv();
    firstTabEnv.services["bus_service"].addChannel("channel1");
    await nextTick();
    // this should not trigger a subscription since the channel1 was
    // aleady known.
    secTabEnv.services["bus_service"].addChannel("channel1");
    await nextTick();
    // removing channel1 from first tab should not trigger
    // re-subscription since the second tab still listens to this
    // channel.
    firstTabEnv.services["bus_service"].deleteChannel("channel1");
    await nextTick();
    // this should trigger a subscription since the channel2 was not
    // known.
    secTabEnv.services["bus_service"].addChannel("channel2");
    await nextTick();

    assert.verifySteps(["subscribe - [channel1]", "subscribe - [channel1,channel2]"]);
});

QUnit.test("channels subscription after disconnection", async function (assert) {
    addBusServicesToRegistry();
    const worker = patchWebsocketWorkerWithCleanup();
    const env = await makeTestEnv({ activateMockServer: true });
    env.services["bus_service"].start();
    await waitUntilSubscribe();
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT);
    await waitUntilSubscribe();
    assert.ok(
        true,
        "No error means waitUntilSubscribe resolves twice thus two subscriptions were triggered as expected"
    );
});

QUnit.test(
    "Last notification id is passed to the worker on service start",
    async function (assert) {
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
        // let the bus service store the last notification id.
        await nextTick();

        updateLastNotificationDeferred = makeDeferred();
        const env2 = await makeTestEnv();
        await env2.services["bus_service"].start();
        await updateLastNotificationDeferred;
        // Second bus service sends the last known notification id.
        assert.verifySteps([`initialize_connection - 2`]);
    }
);

QUnit.test("Websocket disconnects upon user log out", async function (assert) {
    addBusServicesToRegistry();
    // first tab connects to the worker with user logged.
    patchWithCleanup(session, {
        user_id: 1,
    });
    const connectionInitializedDeferred = makeDeferred();
    let connectionOpenedDeferred = makeDeferred();
    patchWebsocketWorkerWithCleanup({
        _initializeConnection(client, data) {
            super._initializeConnection(client, data);
            connectionInitializedDeferred.resolve();
        },
    });

    const firstTabEnv = await makeTestEnv();
    await firstTabEnv.services["bus_service"].start();
    firstTabEnv.services["bus_service"].addEventListener("connect", () => {
        if (session.user_id) {
            assert.step("connect");
        }
        connectionOpenedDeferred.resolve();
        connectionOpenedDeferred = makeDeferred();
    });
    firstTabEnv.services["bus_service"].addEventListener("disconnect", () => {
        assert.step("disconnect");
    });
    await connectionInitializedDeferred;
    await connectionOpenedDeferred;

    // second tab connects to the worker after disconnection: user_id
    // is now false.
    patchWithCleanup(session, {
        user_id: false,
    });
    const env2 = await makeTestEnv();
    await env2.services["bus_service"].start();

    assert.verifySteps(["connect", "disconnect"]);
});

QUnit.test("Websocket reconnects upon user log in", async function (assert) {
    addBusServicesToRegistry();
    // first tab connects to the worker with no user logged.
    patchWithCleanup(session, {
        user_id: false,
    });
    const connectionInitializedDeferred = makeDeferred();
    let websocketConnectedDeferred = makeDeferred();
    patchWebsocketWorkerWithCleanup({
        _initializeConnection(client, data) {
            super._initializeConnection(client, data);
            connectionInitializedDeferred.resolve();
        },
    });

    const firstTabEnv = await makeTestEnv();
    await firstTabEnv.services["bus_service"].start();
    firstTabEnv.services["bus_service"].addEventListener("connect", () => {
        assert.step("connect");
        websocketConnectedDeferred.resolve();
        websocketConnectedDeferred = makeDeferred();
    });
    firstTabEnv.services["bus_service"].addEventListener("disconnect", () => {
        assert.step("disconnect");
    });
    await connectionInitializedDeferred;
    await websocketConnectedDeferred;

    // second tab connects to the worker after connection: user_id
    // is now set.
    patchWithCleanup(session, {
        user_id: 1,
    });
    const env = await makeTestEnv();
    await env.services["bus_service"].start();
    await websocketConnectedDeferred;
    assert.verifySteps(["connect", "disconnect", "connect"]);
});

QUnit.test("WebSocket connects with URL corresponding to given serverURL", async function (assert) {
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

QUnit.test("Disconnect on offline, re-connect on online", async function (assert) {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup();
    let websocketConnectedDeferred = makeDeferred();
    const env = await makeTestEnv();
    env.services["bus_service"].addEventListener("connect", () => {
        assert.step("connect");
        websocketConnectedDeferred.resolve();
        websocketConnectedDeferred = makeDeferred();
    });
    env.services["bus_service"].addEventListener("disconnect", () => assert.step("disconnect"));
    await env.services["bus_service"].start();
    await websocketConnectedDeferred;
    window.dispatchEvent(new Event("offline"));
    await nextTick();
    window.dispatchEvent(new Event("online"));
    await websocketConnectedDeferred;
    assert.verifySteps(["connect", "disconnect", "connect"]);
});

QUnit.test("No disconnect on change offline/online when bus inactive", async function (assert) {
    addBusServicesToRegistry();
    patchWebsocketWorkerWithCleanup();
    const env = await makeTestEnv();
    env.services["bus_service"].addEventListener("connect", () => assert.step("connect"));
    env.services["bus_service"].addEventListener("disconnect", () => assert.step("disconnect"));
    window.dispatchEvent(new Event("offline"));
    await nextTick();
    window.dispatchEvent(new Event("online"));
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("Can reconnect after late close event", async function (assert) {
    addBusServicesToRegistry();
    let subscribeSent = 0;
    const closeDeferred = makeDeferred();
    let openDeferred = makeDeferred();
    const worker = patchWebsocketWorkerWithCleanup({
        _onWebsocketOpen() {
            super._onWebsocketOpen();
            openDeferred.resolve();
        },
        _sendToServer({ event_name }) {
            if (event_name === "subscribe") {
                subscribeSent++;
            }
        },
    });
    const pyEnv = await startServer();
    const env = await makeTestEnv();
    env.services["bus_service"].start();
    await openDeferred;
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
    env.services["bus_service"].addEventListener("connect", () => assert.step("connect"));
    env.services["bus_service"].addEventListener("disconnect", () => assert.step("disconnect"));
    env.services["bus_service"].addEventListener("reconnecting", () => assert.step("reconnecting"));
    env.services["bus_service"].addEventListener("reconnect", () => assert.step("reconnect"));
    // Connection will be closed when passing offline. But the close event
    // will be delayed to come after the next open event. The connection
    // will thus be in the closing state in the meantime.
    window.dispatchEvent(new Event("offline"));
    await nextTick();
    openDeferred = makeDeferred();
    // Worker reconnects upon the reception of the online event.
    window.dispatchEvent(new Event("online"));
    await openDeferred;
    closeDeferred.resolve();
    // Trigger the close event, it shouldn't have any effect since it is
    // related to an old connection that is no longer in use.
    await nextTick();
    openDeferred = makeDeferred();
    // Server closes the connection, the worker should reconnect.
    pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT);
    await openDeferred;
    await nextTick();
    // 3 connections were opened, so 3 subscriptions are expected.
    assert.strictEqual(subscribeSent, 3);
    assert.verifySteps([
        "connect",
        "disconnect",
        "connect",
        "disconnect",
        "reconnecting",
        "reconnect",
    ]);
});

QUnit.test(
    "Fallback on simple worker when shared worker failed to initialize",
    async function (assert) {
        addBusServicesToRegistry();
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
        await env.services["bus_service"].start();
        assert.verifySteps([
            "shared-worker creation",
            'Error while loading "bus_service" SharedWorker, fallback on Worker.',
            "worker creation",
        ]);
    }
);

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
