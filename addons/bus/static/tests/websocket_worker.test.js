import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/mock_websocket";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { asyncStep, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("connect event is broadcasted after calling start", async () => {
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            if (type != "worker_state_updated") {
                asyncStep(`broadcast ${type}`);
            }
        },
    });
    worker._start();
    await waitForSteps(["broadcast connect"]);
});

test("disconnect event is broadcasted", async () => {
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            if (type != "worker_state_updated") {
                asyncStep(`broadcast ${type}`);
            }
        },
    });
    worker._start();
    await waitForSteps(["broadcast connect"]);
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.CLEAN);
    await waitForSteps(["broadcast disconnect"]);
});

test("reconnecting/reconnect event is broadcasted", async () => {
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            if (type != "worker_state_updated") {
                asyncStep(`broadcast ${type}`);
            }
        },
    });
    worker._start();
    await waitForSteps(["broadcast connect"]);
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["broadcast disconnect", "broadcast reconnecting", "broadcast reconnect"]);
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
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type, message) {
            if (type === "notification") {
                expect(message).toEqual(notifications);
            }
            if (["connect", "notification"].includes(type)) {
                asyncStep(`broadcast ${type}`);
            }
        },
    });
    worker._start();
    await waitForSteps(["broadcast connect"]);
    worker.websocket.simulateIncomingMessage(JSON.stringify(notifications));
    await waitForSteps(["broadcast notification"]);
});
