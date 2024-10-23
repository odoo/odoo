import { AWAY_DELAY as ACTUAL_AWAY_DELAY } from "@bus/im_status_service";
import { test, expect } from "@odoo/hoot";
import {
    assertSteps,
    getService,
    makeMockEnv,
    makeMockServer,
    patchWithCleanup,
    serverState,
    step,
} from "@web/../tests/web_test_helpers";
import { defineBusModels } from "./bus_test_helpers";
import { advanceTime, tick } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";

defineBusModels();

// Delays can slighly differ since time is not frozen. Let's tolerate 1000ms
// of difference.
const TOLERANCE = 1000;
const AWAY_DELAY = ACTUAL_AWAY_DELAY + TOLERANCE;
function expectAlmostEqual(a, b) {
    expect(Math.abs(a - b) < TOLERANCE).toBe(true, {
        message: `${a} and ${b} should be almost equal`,
    });
}

test("update presence if IM status changes to offline while this device is online", async () => {
    const { env } = await makeMockServer();
    await makeMockEnv();
    patchWithCleanup(getService("bus_service"), { send: (type) => step(type) });
    await assertSteps(["update_presence"]);
    env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "offline",
        partner_id: serverState.partnerId,
    });
    await assertSteps(["update_presence"]);
});

test("update presence if IM status changes to away while this device is online", async () => {
    const { env } = await makeMockServer();
    await makeMockEnv();
    patchWithCleanup(getService("bus_service"), { send: (type) => step(type) });
    patchWithCleanup(getService("presence"), { getLastPresence: () => new Date().getTime() });
    await assertSteps(["update_presence"]);
    env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await assertSteps(["update_presence"]);
});

test("do not update presence if IM status changes to away while this device is away", async () => {
    const { env } = await makeMockServer();
    await makeMockEnv();
    patchWithCleanup(getService("bus_service"), { send: (type) => step(type) });
    patchWithCleanup(getService("presence"), {
        getLastPresence: () => new Date().getTime() - AWAY_DELAY,
    });
    await assertSteps(["update_presence"]);
    env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await tick();
    await assertSteps([]);
});

test("do not update presence if other user's IM status changes to away", async () => {
    const { env } = await makeMockServer();
    await makeMockEnv();
    patchWithCleanup(getService("bus_service"), { send: (type) => step(type) });
    patchWithCleanup(getService("presence"), { getLastPresence: () => new Date().getTime() });
    await assertSteps(["update_presence"]);
    env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: serverState.publicPartnerId,
    });
    await tick();
    await assertSteps([]);
});

test("update presence when user comes back from away", async () => {
    await makeMockEnv();
    patchWithCleanup(getService("bus_service"), {
        send: (type, payload) => {
            if (type === "update_presence") {
                expectAlmostEqual(expectedInactivityPeriod, payload.inactivity_period);
                step("update_presence");
            }
        },
    });
    patchWithCleanup(getService("presence"), {
        getLastPresence: () => new Date().getTime() - AWAY_DELAY,
    });
    let expectedInactivityPeriod = AWAY_DELAY;
    await assertSteps(["update_presence"]);
    const event = new StorageEvent("storage", {
        key: "presence.lastPresence",
        newValue: new Date().getTime(),
    });
    patchWithCleanup(getService("presence"), { getLastPresence: () => new Date().getTime() });
    expectedInactivityPeriod = 0;
    browser.dispatchEvent(event);
    await assertSteps(["update_presence"]);
});

test("update presence when user status changes to away", async () => {
    await makeMockEnv();
    let expectedInactivityPeriod = 0;
    patchWithCleanup(getService("bus_service"), {
        send: (type, payload) => {
            if (type === "update_presence") {
                expectAlmostEqual(expectedInactivityPeriod, payload.inactivity_period);
                step("update_presence");
            }
        },
    });
    await assertSteps(["update_presence"]);
    expectedInactivityPeriod = AWAY_DELAY;
    patchWithCleanup(getService("presence"), {
        getLastPresence: () => new Date().getTime() - AWAY_DELAY,
    });
    advanceTime(AWAY_DELAY);
    await assertSteps(["update_presence"]);
});
