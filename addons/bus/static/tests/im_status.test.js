import { AWAY_DELAY } from "@bus/im_status_service";
import { beforeEach, describe, test } from "@odoo/hoot";
import { advanceTime, freezeTime } from "@odoo/hoot-dom";
import {
    asyncStep,
    makeMockEnv,
    MockServer,
    mockService,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { defineBusModels } from "./bus_test_helpers";

defineBusModels();

beforeEach(freezeTime);

describe.current.tags("headless");

test("update presence if IM status changes to offline while this device is online", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });

    await makeMockEnv();
    await waitForSteps(["update_presence"]);
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "offline",
        partner_id: serverState.partnerId,
    });
    await waitForSteps(["update_presence"]);
});

test("update presence if IM status changes to away while this device is online", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });

    localStorage.setItem("presence.lastPresence", Date.now());

    await makeMockEnv();
    await waitForSteps(["update_presence"]);
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await waitForSteps(["update_presence"]);
});

test("do not update presence if IM status changes to away while this device is away", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });

    localStorage.setItem("presence.lastPresence", Date.now() - AWAY_DELAY);

    await makeMockEnv();
    await waitForSteps(["update_presence"]);
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await waitForSteps([]);
});

test("do not update presence if other user's IM status changes to away", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });

    localStorage.setItem("presence.lastPresence", Date.now());

    await makeMockEnv();
    await waitForSteps(["update_presence"]);
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
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

    await makeMockEnv();
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

    await makeMockEnv();
    await waitForSteps([0]);

    await advanceTime(AWAY_DELAY);

    await waitForSteps([AWAY_DELAY]);
});
