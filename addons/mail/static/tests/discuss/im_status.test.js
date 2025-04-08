import { defineMailModels, start, startServer } from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, test } from "@odoo/hoot";
import { advanceTime, freezeTime } from "@odoo/hoot-dom";
import { asyncStep, mockService, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

import { AWAY_DELAY } from "@mail/core/common/im_status_service";

defineMailModels();
beforeEach(freezeTime);
describe.current.tags("headless");

test("update presence if IM status changes to offline while this device is online", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
    const pyEnv = await startServer();
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
    await start();
    await waitForSteps([0]);
    await advanceTime(AWAY_DELAY);
    await waitForSteps([AWAY_DELAY]);
});
