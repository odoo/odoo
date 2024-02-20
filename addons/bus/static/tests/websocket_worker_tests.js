/** @odoo-module */

import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { Deferred } from "@web/core/utils/concurrency";

QUnit.module("Websocket Worker");

QUnit.test("connect event is broadcasted after calling start", async function (assert) {
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            assert.step(`broadcast ${type}`);
        },
    });
    worker._start();
    // Wait for the websocket to connect.
    await nextTick();
    assert.verifySteps(["broadcast connect"]);
});

QUnit.test("disconnect event is broadcasted", async function (assert) {
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            assert.step(`broadcast ${type}`);
        },
    });
    worker._start();
    // Wait for the websocket to connect.
    await nextTick();
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.CLEAN);
    // Wait for the websocket to disconnect.
    await nextTick();

    assert.verifySteps(["broadcast connect", "broadcast disconnect"]);
});

QUnit.test("reconnecting/reconnect event is broadcasted", async function (assert) {
    // Patch setTimeout in order for the worker to reconnect immediatly.
    patchWithCleanup(window, {
        setTimeout: (fn) => fn(),
    });
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            assert.step(`broadcast ${type}`);
        },
    });
    worker._start();
    // Wait for the websocket to connect.
    await nextTick();
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    // Wait for the disconnect/reconnecting/reconnect events.
    await nextTick();

    assert.verifySteps([
        "broadcast connect",
        "broadcast disconnect",
        "broadcast reconnecting",
        "broadcast reconnect",
    ]);
});

QUnit.test("notification event is broadcasted", async function (assert) {
    const notifications = [
        {
            id: 70,
            message: {
                type: "bundle_changed",
                payload: {
                    server_version: "15.5alpha1+e",
                },
            },
        },
    ];
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type, message) {
            if (type === "notification") {
                assert.step(`broadcast ${type}`);
                assert.deepEqual(message, notifications);
            }
        },
    });
    worker._start();
    // Wait for the websocket to connect.
    await nextTick();

    worker.websocket.dispatchEvent(
        new MessageEvent("message", {
            data: JSON.stringify(notifications),
        })
    );

    assert.verifySteps(["broadcast notification"]);
});

QUnit.test("notifications are batched by the mock server", async (assert) => {
    const notificationsReceivedDeferred = new Deferred();
    const pyEnv = await startServer();
    await makeTestEnv({ activateMockServer: true });
    patchWebsocketWorkerWithCleanup({
        broadcast(type, message) {
            if (type === "notification") {
                notificationsReceivedDeferred.resolve(message);
            }
        },
    });
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "bus.event", { foo: 1 });
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "bus.event", { bar: 2 });
    const notifications = await notificationsReceivedDeferred;
    const messages = notifications.map(({ message }) => message);
    assert.strictEqual(messages.length, 2);
    assert.strictEqual(messages[0].payload.foo, 1);
    assert.strictEqual(messages[1].payload.bar, 2);
});
