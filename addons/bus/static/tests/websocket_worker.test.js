import { getWebSocketWorker } from "@bus/../tests/mock_websocket";
import { advanceTime, describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";
import { makeMockServer, MockServer, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { WEBSOCKET_CLOSE_CODES, WebsocketWorker } from "@bus/workers/websocket_worker";

describe.current.tags("headless");

/**
 * @param {ReturnType<getWebSocketWorker>} worker
 * @param {(type: string, message: any) => any} [onBroadcast]
 */
const startWebSocketWorker = async (onBroadcast) => {
    await makeMockServer();
    const worker = getWebSocketWorker();
    if (onBroadcast) {
        patchWithCleanup(worker, {
            broadcast(...args) {
                onBroadcast(...args);
                return super.broadcast(...args);
            },
        });
    }
    worker._start();
    await runAllTimers();
    return worker;
};

test("connect event is broadcasted after calling start", async () => {
    await startWebSocketWorker((type) => {
        if (type !== "BUS:WORKER_STATE_UPDATED") {
            expect.step(`broadcast ${type}`);
        }
    });
    await expect.waitForSteps(["broadcast BUS:CONNECT"]);
});

test("disconnect event is broadcasted", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (type !== "BUS:WORKER_STATE_UPDATED") {
            expect.step(`broadcast ${type}`);
        }
    });
    await expect.waitForSteps(["broadcast BUS:CONNECT"]);
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.CLEAN);
    await runAllTimers();
    await expect.waitForSteps(["broadcast BUS:DISCONNECT"]);
});

test("reconnecting/reconnect event is broadcasted", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (type !== "BUS:WORKER_STATE_UPDATED") {
            expect.step(`broadcast ${type}`);
        }
    });
    await expect.waitForSteps(["broadcast BUS:CONNECT"]);
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await expect.waitForSteps(["broadcast BUS:DISCONNECT", "broadcast BUS:RECONNECTING"]);
    await runAllTimers();
    await expect.waitForSteps(["broadcast BUS:RECONNECT"]);
});

test("notification event is broadcasted", async () => {
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
    await startWebSocketWorker((type, message) => {
        if (type === "BUS:NOTIFICATION") {
            expect(message).toEqual(notifications);
        }
        if (["BUS:CONNECT", "BUS:NOTIFICATION"].includes(type)) {
            expect.step(`broadcast ${type}`);
        }
    });
    await expect.waitForSteps(["broadcast BUS:CONNECT"]);
    for (const serverWs of MockServer.current._websockets) {
        serverWs.send(JSON.stringify(notifications));
    }
    await expect.waitForSteps(["broadcast BUS:NOTIFICATION"]);
});

test("last_id_reset updates worker state", async () => {
    const worker = await startWebSocketWorker();
    worker.lastNotificationId = 50;
    worker.seenNotificationIds.add(5);
    worker.seenNotificationIds.add(40);
    worker.seenNotificationIds.add(50);
    const internalMsg = [{ type: "bus/last_id_reset", internal: true, payload: 10 }];
    for (const serverWs of MockServer.current._websockets) {
        serverWs.send(JSON.stringify(internalMsg));
    }
    await runAllTimers();
    expect(worker.lastNotificationId).toBe(10);
    expect(worker.seenNotificationIds.has(5)).toBe(true);
    expect(worker.seenNotificationIds.has(40)).toBe(false);
    expect(worker.seenNotificationIds.has(50)).toBe(false);
});

test("last_id_reset with zero payload resets to 0, not undefined", async () => {
    const worker = await startWebSocketWorker();
    worker.lastNotificationId = 50;
    const internalMsg = [{ type: "bus/last_id_reset", internal: true, payload: 0 }];
    for (const serverWs of MockServer.current._websockets) {
        serverWs.send(JSON.stringify(internalMsg));
    }
    await runAllTimers();
    expect(worker.lastNotificationId).toBe(0);
});

test("disconnect event is sent when stopping the worker", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (type !== "BUS:WORKER_STATE_UPDATED") {
            expect.step(`broadcast ${type}`);
        }
    });
    await expect.waitForSteps(["broadcast BUS:CONNECT"]);
    worker._stop();
    await runAllTimers();
    await expect.waitForSteps(["broadcast BUS:DISCONNECT"]);
});

test("connection is reset when the connection check gets no answer", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (["BUS:DISCONNECT", "BUS:RECONNECTING", "BUS:RECONNECT"].includes(type)) {
            expect.step(`broadcast ${type}`);
        }
    });
    // the reconnection delay is random: reconnect right after the timeout
    patchWithCleanup(worker, { RECONNECT_JITTER: 0 });
    patchWithCleanup(WebsocketWorker.prototype, { enableCheckInterval: true });
    worker._restartConnectionCheckInterval();
    const staleWebsocket = worker.websocket;
    staleWebsocket.send = () => {};
    await advanceTime(worker.CONNECTION_CHECK_DELAY + worker.CONNECTION_CHECK_PONG_TIMEOUT + 1000);
    await expect.waitForSteps([
        "broadcast BUS:DISCONNECT",
        "broadcast BUS:RECONNECTING",
        "broadcast BUS:RECONNECT",
    ]);
    expect(worker.websocket).not.toBe(staleWebsocket);
    expect(worker.websocket.readyState).toBe(WebSocket.OPEN);
});

test("stopping the worker cancels a pending connection check", async () => {
    patchWithCleanup(WebsocketWorker.prototype, { enableCheckInterval: true });
    const worker = await startWebSocketWorker((type) => {
        if (["BUS:RECONNECTING", "BUS:CONNECT"].includes(type)) {
            expect.step(`broadcast ${type}`);
        }
    });
    await expect.waitForSteps(["broadcast BUS:CONNECT"]);
    worker.websocket.send = (message) => {
        if (message instanceof Uint8Array) {
            expect.step("connection check sent");
        }
    };
    await advanceTime(worker.CONNECTION_CHECK_DELAY + 1000);
    await expect.waitForSteps(["connection check sent"]);
    worker._stop();
    await advanceTime(worker.CONNECTION_CHECK_PONG_TIMEOUT + 1000);
    expect(worker.websocket).toBe(null);
    await expect.waitForSteps([]);
});

test("connection is kept when the connection check is answered", async () => {
    patchWithCleanup(WebsocketWorker.prototype, { enableCheckInterval: true });
    const worker = await startWebSocketWorker((type) => {
        if (type === "BUS:DISCONNECT") {
            expect.step(`broadcast ${type}`);
        }
    });
    patchWithCleanup(worker.websocket, {
        send(message) {
            if (message instanceof Uint8Array) {
                expect.step("connection check answered");
                setTimeout(() =>
                    this.dispatchEvent(new MessageEvent("message", { data: new Uint8Array([0]) }))
                );
            }
        },
    });
    await advanceTime(worker.CONNECTION_CHECK_DELAY + worker.CONNECTION_CHECK_PONG_TIMEOUT + 1000);
    await expect.waitForSteps(["connection check answered"]);
});

test("check connection health during inactivity", async () => {
    const ogSocket = window.WebSocket;
    let waitingForCheck = true;
    const newSocket = function () {
        const ws = new ogSocket(...arguments);
        ws.send = (message) => {
            if (waitingForCheck && message instanceof Uint8Array) {
                expect.step("check_connection_health_sent");
                waitingForCheck = false;
            }
        };
        return ws;
    };
    Object.assign(newSocket, ogSocket);
    patchWithCleanup(window, { WebSocket: newSocket });
    patchWithCleanup(WebsocketWorker.prototype, {
        enableCheckInterval: true,
        _restartConnectionCheckInterval() {
            expect.step("_restartConnectionCheckInterval");
            super._restartConnectionCheckInterval();
        },
    });
    const worker = await startWebSocketWorker((type) => {
        if (type === "BUS:CONNECT") {
            expect.step(`broadcast ${type}`);
        }
    });
    // Restarted on open, then by the first subscription.
    await expect.waitForSteps([
        "broadcast BUS:CONNECT",
        "_restartConnectionCheckInterval",
        "_restartConnectionCheckInterval",
    ]);
    worker.websocket.dispatchEvent(
        new MessageEvent("message", {
            data: JSON.stringify([{ id: 70, message: { type: "foo" } }]),
        })
    );
    await expect.waitForSteps(["_restartConnectionCheckInterval"]);
    worker._sendToServer({ event_name: "foo" });
    await expect.waitForSteps(["_restartConnectionCheckInterval"]);
    await advanceTime(worker.CONNECTION_CHECK_DELAY + 1000);
    await expect.waitForSteps(["check_connection_health_sent"]);
});

test("debounced updates are batched", async () => {
    patchWithCleanup(WebsocketWorker, { OUTGOING_BATCH_DELAY: 120_000 });
    patchWithCleanup(WebsocketWorker.prototype, {
        _sendToServer(message) {
            if (message.event_name === "subscribe") {
                expect.step(`subscribe - ${JSON.stringify(message.data.channels)}`);
            }
            super._sendToServer(message);
        },
    });
    const worker = await startWebSocketWorker((type) => {
        if (type == "BUS:CONNECT") {
            expect.step(type);
        }
    });
    const client = new MessagePort();
    worker.registerClient(client);
    worker._start();
    await expect.waitForSteps(["BUS:CONNECT"]);
    await advanceTime(120_000);
    await expect.waitForSteps(["subscribe - []"]);
    worker._onClientMessage(client, { action: "BUS:ADD_CHANNEL", data: "C1" });
    await advanceTime(120_000);
    await expect.waitForSteps(['subscribe - ["C1"]']);
    // the same channel again => no subscribe
    worker._onClientMessage(client, { action: "BUS:ADD_CHANNEL", data: "C1" });
    await advanceTime(120_000);
    await expect.waitForSteps([]);
    // multiple adds => only one subscribe
    worker._onClientMessage(client, { action: "BUS:ADD_CHANNEL", data: "C2" });
    worker._onClientMessage(client, { action: "BUS:ADD_CHANNEL", data: "C3" });
    await advanceTime(120_000);
    await expect.waitForSteps(['subscribe - ["C1","C2","C3"]']);
});

/**
 * @param {WebsocketWorker} worker
 * @param {string[]} channels
 * @param {(message: { type: string, data: any }) => void} [postMessage]
 */
const addFakeClient = (worker, channels, postMessage = () => {}) => {
    const client = { postMessage };
    worker.channelsByClient.set(client, channels);
    return client;
};

test("stale tab does not change the connection data", async () => {
    const worker = await startWebSocketWorker();
    const client = addFakeClient(worker, ["C1"], ({ type }) => expect.step(type));
    const initData = { db: "db1", lastNotificationId: 1, uid: 1, websocketURL: "ws://new" };
    worker._initializeConnection(client, { ...initData, startTs: 2000 });
    await expect.waitForSteps(["BUS:WORKER_STATE_UPDATED", "BUS:INITIALIZED"]);
    worker.active = false;
    worker._initializeConnection(client, {
        db: "db2",
        lastNotificationId: 1,
        uid: 2,
        websocketURL: "ws://old",
        startTs: 1000,
    });
    await expect.waitForSteps(["BUS:WORKER_STATE_UPDATED", "BUS:INITIALIZED", "BUS:OUTDATED"]);
    expect(worker.websocketURL).toBe("ws://new");
    expect(worker.currentUID).toBe(1);
    expect(worker.currentDB).toBe("db1");
    expect(worker.channelsByClient.get(client)).toEqual(["C1"]);
});

test("uid is adopted after session expiry without a reset", async () => {
    const worker = await startWebSocketWorker();
    const client = addFakeClient(worker, ["C1"]);
    const initData = { db: "db1", lastNotificationId: 1, websocketURL: "ws://bus" };
    worker._initializeConnection(client, { ...initData, uid: 1, startTs: 1000 });
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.SESSION_EXPIRED);
    await runAllTimers();
    expect(worker.currentUID).toBe(null);
    worker._initializeConnection(client, { ...initData, uid: 2, startTs: 2000 });
    expect(worker.currentUID).toBe(2);
    expect(worker.channelsByClient.get(client)).toEqual(["C1"]);
    worker._initializeConnection(client, { ...initData, uid: 3, startTs: 3000 });
    expect(worker.currentUID).toBe(3);
    expect(worker.channelsByClient.get(client)).toEqual([]);
});

test("database change resets the channels once", async () => {
    const worker = await startWebSocketWorker();
    const client = addFakeClient(worker, ["C1"]);
    const initData = { lastNotificationId: 1, websocketURL: "ws://bus" };
    worker._initializeConnection(client, { ...initData, db: "db1", uid: 1, startTs: 1000 });
    expect(worker.channelsByClient.get(client)).toEqual(["C1"]);
    worker._initializeConnection(client, { ...initData, db: "db2", uid: undefined, startTs: 2000 });
    expect(worker.currentDB).toBe("db2");
    expect(worker.currentUID).toBe(null);
    expect(worker.channelsByClient.get(client)).toEqual([]);
    worker.channelsByClient.set(client, ["C2"]);
    worker._initializeConnection(client, { ...initData, db: "db2", uid: 5, startTs: 3000 });
    expect(worker.currentUID).toBe(5);
    expect(worker.channelsByClient.get(client)).toEqual(["C2"]);
});

test("message sent before the first subscription survives a reconnection", async () => {
    patchWithCleanup(WebSocket.prototype, {
        send(data) {
            if (typeof data === "string") {
                expect.step(`sent ${JSON.parse(data).event_name}`);
            }
            return super.send(...arguments);
        },
    });
    const worker = await startWebSocketWorker((type) => {
        if (["BUS:RECONNECTING", "BUS:RECONNECT"].includes(type)) {
            expect.step(type);
        }
    });
    await expect.waitForSteps(["sent subscribe"]);
    const reconnect = async () => {
        worker.websocket.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
        await expect.waitForSteps(["BUS:RECONNECTING"]);
        await runAllTimers();
        await expect.waitForSteps(["BUS:RECONNECT"]);
    };
    const updateChannels = worker._debouncedUpdateChannels;
    worker._debouncedUpdateChannels = () => {};
    await reconnect();
    // The new websocket is open, but did not subscribe yet.
    worker._sendToServer({ event_name: "foo" });
    await reconnect();
    worker._debouncedUpdateChannels = updateChannels;
    worker._scheduleUpdateChannels();
    await runAllTimers();
    await expect.waitForSteps(["sent subscribe", "sent foo"]);
});
