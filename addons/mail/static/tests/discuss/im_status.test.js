import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import { BusPlugin } from "@bus/services/bus_plugin";
import { WebsocketWorker } from "@bus/workers/websocket_worker";
import {
    defineMailModels,
    sendPresenceUpdate,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { AWAY_DELAY } from "@mail/core/common/im_status_plugin";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, freezeTime } from "@odoo/hoot-dom";

import { patch } from "@web/core/utils/patch";
import { getService, makeTestApp, serverState } from "@web/../tests/web_test_helpers";

defineMailModels();
beforeEach(freezeTime);
describe.current.tags("headless");

/**
 * Intercepts the "update_presence" messages sent through the bus, and steps
 * `getStep(payload)` for each of them.
 *
 * @param {(payload: { inactivity_period: number }) => any} [getStep]
 */
function stepUpdatePresence(getStep = () => "update_presence") {
    patch(BusPlugin.prototype, {
        send(type, payload) {
            if (type === "update_presence") {
                expect.step(getStep(payload));
                return;
            }
            return super.send(...arguments);
        },
    });
}

test("update presence if IM status changes to offline while this device is online", async () => {
    stepUpdatePresence();
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { im_status: "online" });
    const subscribed = waitUntilSubscribe();
    await start({ waitUntilSubscribe: false });
    await expect.waitForSteps(["update_presence"]);
    sendPresenceUpdate("res.users", serverState.userId, "offline");
    await expect.waitForSteps(["update_presence"]);
    await advanceTime(WebsocketWorker.OUTGOING_BATCH_DELAY);
    await subscribed;
});

test("update presence if IM status changes to away while this device is online", async () => {
    stepUpdatePresence();
    localStorage.setItem("presence.lastPresence", Date.now());
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { im_status: "online" });
    const subscribed = waitUntilSubscribe();
    await start({ waitUntilSubscribe: false });
    await expect.waitForSteps(["update_presence"]);
    sendPresenceUpdate("res.users", serverState.userId, "away");
    await expect.waitForSteps(["update_presence"]);
    await advanceTime(WebsocketWorker.OUTGOING_BATCH_DELAY);
    await subscribed;
});

test("do not update presence if IM status changes to away while this device is away", async () => {
    stepUpdatePresence();
    localStorage.setItem("presence.lastPresence", Date.now() - AWAY_DELAY);
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { im_status: "away" });
    const subscribed = waitUntilSubscribe();
    await start({ waitUntilSubscribe: false });
    await expect.waitForSteps(["update_presence"]);
    sendPresenceUpdate("res.users", serverState.userId, "away");
    await expect.waitForSteps([]);
    await advanceTime(WebsocketWorker.OUTGOING_BATCH_DELAY);
    await subscribed;
});

test("do not update presence if other user's IM status changes to away", async () => {
    stepUpdatePresence();
    localStorage.setItem("presence.lastPresence", Date.now());
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({ name: "bob" });
    const bobUserId = pyEnv["res.users"].create({ partner_id: bobPartnerId, im_status: "online" });
    const subscribed = waitUntilSubscribe();
    await start({ waitUntilSubscribe: false });
    await expect.waitForSteps(["update_presence"]);
    sendPresenceUpdate("res.users", bobUserId, "away");
    await expect.waitForSteps([]);
    await advanceTime(WebsocketWorker.OUTGOING_BATCH_DELAY);
    await subscribed;
});

test("update presence when user comes back from away", async () => {
    stepUpdatePresence((payload) => payload.inactivity_period);
    localStorage.setItem("presence.lastPresence", Date.now() - AWAY_DELAY);
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { im_status: "away" });
    const subscribed = waitUntilSubscribe();
    await start({ waitUntilSubscribe: false });
    await expect.waitForSteps([AWAY_DELAY]);
    localStorage.setItem("presence.lastPresence", Date.now());
    await expect.waitForSteps([0]);
    await advanceTime(WebsocketWorker.OUTGOING_BATCH_DELAY);
    await subscribed;
});

test("update presence when user status changes to away", async () => {
    stepUpdatePresence((payload) => payload.inactivity_period);
    localStorage.setItem("presence.lastPresence", Date.now());
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { im_status: "online" });
    const subscribed = waitUntilSubscribe();
    await start({ waitUntilSubscribe: false });
    await expect.waitForSteps([0]);
    await advanceTime(AWAY_DELAY);
    await expect.waitForSteps([AWAY_DELAY]);
    await subscribed;
});

test("new tab update presence when user comes back from away", async () => {
    // Tabs notify presence with a debounced update, and the im_status plugin skips
    // duplicates. This test ensures a new tab that never sent presence still issues
    // its first update (important when old tabs close and new ones replace them).
    localStorage.setItem("presence.lastPresence", Date.now() - AWAY_DELAY);
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], { im_status: "offline" });
    stepUpdatePresence();
    await makeTestApp({ forceNew: true });
    getService("bus_service").start();
    await expect.waitForSteps(["update_presence"]);
    await makeTestApp({ forceNew: true });
    getService("bus_service").start();
    await expect.waitForSteps([]);
    localStorage.setItem("presence.lastPresence", Date.now()); // Simulate user presence.
    await expect.waitForSteps(["update_presence", "update_presence"]);
});
