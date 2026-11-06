import { getWebSocketWorker } from "@bus/../tests/mock_websocket";
import { advanceTime, describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";
import {
    asyncStep,
    makeMockServer,
    MockServer,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

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
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast BUS:CONNECT"]);
});

test("disconnect event is broadcasted", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (type !== "BUS:WORKER_STATE_UPDATED") {
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast BUS:CONNECT"]);
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.CLEAN);
    await runAllTimers();
    await waitForSteps(["broadcast BUS:DISCONNECT"]);
});

test("reconnecting/reconnect event is broadcasted", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (type !== "BUS:WORKER_STATE_UPDATED") {
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast BUS:CONNECT"]);
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["broadcast BUS:DISCONNECT", "broadcast BUS:RECONNECTING"]);
    await runAllTimers();
    await waitForSteps(["broadcast BUS:RECONNECT"]);
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
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast BUS:CONNECT"]);
    for (const serverWs of MockServer.current._websockets) {
        serverWs.send(JSON.stringify(notifications));
    }
    await waitForSteps(["broadcast BUS:NOTIFICATION"]);
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
            asyncStep(`broadcast ${type}`);
        }
    });
    // the reconnection delay is random: reconnect right after the timeout
    patchWithCleanup(worker, { RECONNECT_JITTER: 0 });
    patchWithCleanup(WebsocketWorker.prototype, { enableCheckInterval: true });
    worker._restartConnectionCheckInterval();
    const staleWebsocket = worker.websocket;
    staleWebsocket.send = () => {};
    await advanceTime(worker.CONNECTION_CHECK_DELAY + worker.CONNECTION_CHECK_PONG_TIMEOUT + 1000);
    await waitForSteps([
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
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast BUS:CONNECT"]);
    worker.websocket.send = (message) => {
        if (message instanceof Uint8Array) {
            asyncStep("connection check sent");
        }
    };
    await advanceTime(worker.CONNECTION_CHECK_DELAY + 1000);
    await waitForSteps(["connection check sent"]);
    worker._stop();
    await advanceTime(worker.CONNECTION_CHECK_PONG_TIMEOUT + 1000);
    expect(worker.websocket).toBe(null);
    await waitForSteps([]);
});

test("connection is kept when the connection check is answered", async () => {
    patchWithCleanup(WebsocketWorker.prototype, { enableCheckInterval: true });
    const worker = await startWebSocketWorker((type) => {
        if (type === "BUS:DISCONNECT") {
            asyncStep(`broadcast ${type}`);
        }
    });
    patchWithCleanup(worker.websocket, {
        send(message) {
            if (message instanceof Uint8Array) {
                asyncStep("connection check answered");
                setTimeout(() =>
                    this.dispatchEvent(new MessageEvent("message", { data: new Uint8Array([0]) }))
                );
            }
        },
    });
    await advanceTime(worker.CONNECTION_CHECK_DELAY + worker.CONNECTION_CHECK_PONG_TIMEOUT + 1000);
    await waitForSteps(["connection check answered"]);
});

test("check connection health during inactivity", async () => {
    const ogSocket = window.WebSocket;
    let waitingForCheck = true;
    patchWithCleanup(window, {
        WebSocket: function () {
            const ws = new ogSocket(...arguments);
            ws.send = (message) => {
                if (waitingForCheck && message instanceof Uint8Array) {
                    expect.step("check_connection_health_sent");
                    waitingForCheck = false;
                }
            };
            return ws;
        },
    });
    patchWithCleanup(WebsocketWorker.prototype, {
        enableCheckInterval: true,
        _restartConnectionCheckInterval() {
            expect.step("_restartConnectionCheckInterval");
            super._restartConnectionCheckInterval();
        },
        _sendToServer(payload) {
            if (payload.event_name === "foo") {
                super._sendToServer(payload);
            }
        },
    });
    const worker = await startWebSocketWorker((type) => {
        if (type === "BUS:CONNECT") {
            expect.step(`broadcast ${type}`);
        }
    });
    await expect.waitForSteps(["broadcast BUS:CONNECT", "_restartConnectionCheckInterval"]);
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
