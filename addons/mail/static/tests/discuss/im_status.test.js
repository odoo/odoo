import { AWAY_DELAY } from "@mail/core/common/im_status_service";
import { defineMailModels, start, startServer } from "@mail/../tests/mail_test_helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, freezeTime } from "@odoo/hoot-dom";

import { registry } from "@web/core/registry";
import {
    asyncStep,
    makeMockEnv,
    mockService,
    patchWithCleanup,
    restoreRegistry,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

defineMailModels();
beforeEach(freezeTime);
describe.current.tags("headless");

test("update presence if IM status changes to offline while this device is online", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
    const pyEnv = await startServer();
    pyEnv["res.partner"].write(serverState.partnerId, { im_status: "online" });
    await start();
    await waitForSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        presence_status: "offline",
        im_status: "offline",
        partner_id: serverState.partnerId,
    });
    await waitForSteps(["update_presence"]);
});

test("update presence if IM status changes to away while this device is online", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
    localStorage.setItem("presence.lastPresence", Date.now());
    const pyEnv = await startServer();
    pyEnv["res.partner"].write(serverState.partnerId, { im_status: "online" });
    await start();
    await waitForSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        presence_status: "away",
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await waitForSteps(["update_presence"]);
});

test("do not update presence if IM status changes to away while this device is away", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
    localStorage.setItem("presence.lastPresence", Date.now() - AWAY_DELAY);
    const pyEnv = await startServer();
    pyEnv["res.partner"].write(serverState.partnerId, { im_status: "away" });
    await start();
    await waitForSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        presence_status: "away",
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await waitForSteps([]);
});

test("do not update presence if other user's IM status changes to away", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
    localStorage.setItem("presence.lastPresence", Date.now());
    const pyEnv = await startServer();
    pyEnv["res.partner"].write(serverState.partnerId, { im_status: "online" });
    await start();
    await waitForSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        presence_status: "away",
        im_status: "away",
        partner_id: serverState.publicPartnerId,
    });
    await waitForSteps([]);
});

test("update presence when user comes back from away", async () => {
    mockService("bus_service", {
        send: (type, payload) => {
            if (type === "update_presence") {
                asyncStep(payload.inactivity_period);
            }
        },
    });
    localStorage.setItem("presence.lastPresence", Date.now() - AWAY_DELAY);
    const pyEnv = await startServer();
    pyEnv["res.partner"].write(serverState.partnerId, { im_status: "away" });
    await start();
    await waitForSteps([AWAY_DELAY]);
    localStorage.setItem("presence.lastPresence", Date.now());
    await waitForSteps([0]);
});

test("update presence when user status changes to away", async () => {
    mockService("bus_service", {
        send: (type, payload) => {
            if (type === "update_presence") {
                asyncStep(payload.inactivity_period);
            }
        },
    });
    localStorage.setItem("presence.lastPresence", Date.now());
    const pyEnv = await startServer();
    pyEnv["res.partner"].write(serverState.partnerId, { im_status: "online" });
    await start();
    await waitForSteps([0]);
    await advanceTime(AWAY_DELAY);
    await waitForSteps([AWAY_DELAY]);
});

test("new tab update presence when user comes back from away", async () => {
    // Tabs notify presence with a debounced update, and the status service skips
    // duplicates. This test ensures a new tab that never sent presence still issues
    // its first update (important when old tabs close and new ones replace them).
    localStorage.setItem("presence.lastPresence", Date.now() - AWAY_DELAY);
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "offline" });
    const tabEnv_1 = await makeMockEnv();
    patchWithCleanup(tabEnv_1.services.bus_service, {
        send: (type) => {
            if (type === "update_presence") {
                expect.step("update_presence");
            }
        },
    });
    tabEnv_1.services.bus_service.start();
    await expect.waitForSteps(["update_presence"]);
    restoreRegistry(registry);
    const tabEnv_2 = await makeMockEnv(null, { makeNew: true });
    patchWithCleanup(tabEnv_2.services.bus_service, {
        send: (type) => {
            if (type === "update_presence") {
                expect.step("update_presence");
            }
        },
    });
    tabEnv_2.services.bus_service.start();
    await expect.waitForSteps([]);
    localStorage.setItem("presence.lastPresence", Date.now()); // Simulate user presence.
    await expect.waitForSteps(["update_presence", "update_presence"]);
});
