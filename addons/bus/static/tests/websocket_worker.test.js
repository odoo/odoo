import { getWebSocketWorker } from "@bus/../tests/mock_websocket";
import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";
import {
    asyncStep,
    makeMockServer,
    MockServer,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";

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
        if (type !== "worker_state_updated") {
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast connect"]);
});

test("disconnect event is broadcasted", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (type !== "worker_state_updated") {
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast connect"]);
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.CLEAN);
    await runAllTimers();
    await waitForSteps(["broadcast disconnect"]);
});

test("reconnecting/reconnect event is broadcasted", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (type !== "worker_state_updated") {
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast connect"]);
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["broadcast disconnect", "broadcast reconnecting"]);
    await runAllTimers();
    await waitForSteps(["broadcast reconnect"]);
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
        if (type === "notification") {
            expect(message).toEqual(notifications);
        }
        if (["connect", "notification"].includes(type)) {
            asyncStep(`broadcast ${type}`);
        }
    });
    await waitForSteps(["broadcast connect"]);
    for (const serverWs of MockServer.current._websockets) {
        serverWs.send(JSON.stringify(notifications));
    }
    await waitForSteps(["broadcast notification"]);
});

test("disconnect event is sent when stopping the worker", async () => {
    const worker = await startWebSocketWorker((type) => {
        if (type !== "worker_state_updated") {
            expect.step(`broadcast ${type}`);
        }
    });
    await expect.waitForSteps(["broadcast connect"]);
    worker._stop();
    await runAllTimers();
    await expect.waitForSteps(["broadcast disconnect"]);
});
