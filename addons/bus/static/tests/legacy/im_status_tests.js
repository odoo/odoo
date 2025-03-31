/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";
import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";
import { AWAY_DELAY as ACTUAL_AWAY_DELAY, imStatusService } from "@bus/im_status_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { mockTimeout, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { assertSteps, step } from "@web/../tests/utils";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

// Delays can slighly differ since time is not frozen. Let's tolerate 1000ms
// of difference.
const TOLERANCE = 1000;
const AWAY_DELAY = ACTUAL_AWAY_DELAY + TOLERANCE;
function assertAlmostEqual(a, b) {
    QUnit.assert.ok(Math.abs(a - b) < TOLERANCE, `${a} and ${b} should be almost equal`);
}

QUnit.module("IM status", {
    async beforeEach() {
        addBusServicesToRegistry();
        patchWebsocketWorkerWithCleanup();
        registry.category("services").add("im_status", imStatusService);
        const pyEnv = await startServer();
        patchWithCleanup(user, { partnerId: pyEnv.currentPartner.id });
        registry.category("mock_server").add("res.users/has_group", (route, args) => {
            return args[0] === "base.group_public";
        });
        registerCleanup(() => registry.category("mock_server").remove("res.users/has_group"));
    },
});

QUnit.test(
    "update presence if IM status changes to offline while this device is online",
    async () => {
        const pyEnv = await startServer();
        const env = await makeTestEnv({ activateMockServer: true });
        patchWithCleanup(env.services.bus_service, { send: (type) => step(type) });
        env.services.bus_service.start();
        await assertSteps(["update_presence"]);
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "bus.bus/im_status_updated", {
            im_status: "offline",
            partner_id: pyEnv.currentPartner.id,
        });
        await assertSteps(["update_presence"]);
    }
);

QUnit.test("update presence if IM status changes to away while this device is online", async () => {
    const pyEnv = await startServer();
    const env = await makeTestEnv({ activateMockServer: true });
    patchWithCleanup(env.services.bus_service, { send: (type) => step(type) });
    patchWithCleanup(env.services.presence, { getLastPresence: () => new Date().getTime() });
    env.services.bus_service.start();
    await assertSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: pyEnv.currentPartner.id,
    });
    await assertSteps(["update_presence"]);
});

QUnit.test(
    "do not update presence if IM status changes to away while this device is away",
    async () => {
        const pyEnv = await startServer();
        const env = await makeTestEnv({ activateMockServer: true });
        patchWithCleanup(env.services.bus_service, { send: (type) => step(type) });
        patchWithCleanup(env.services.presence, {
            getLastPresence: () => new Date().getTime() - AWAY_DELAY,
        });
        env.services.bus_service.start();
        await assertSteps(["update_presence"]);
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "bus.bus/im_status_updated", {
            im_status: "away",
            partner_id: pyEnv.currentPartner.id,
        });
        await nextTick();
        await assertSteps([]);
    }
);

QUnit.test("do not update presence if other user's IM status changes to away", async () => {
    const pyEnv = await startServer();
    const env = await makeTestEnv({ activateMockServer: true });
    patchWithCleanup(env.services.bus_service, { send: (type) => step(type) });
    patchWithCleanup(env.services.presence, { getLastPresence: () => new Date().getTime() });
    env.services.bus_service.start();
    await assertSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: pyEnv.publicPartnerId,
    });
    await nextTick();
    await assertSteps([]);
});

QUnit.test("update presence when user comes back from away", async () => {
    const env = await makeTestEnv();
    patchWithCleanup(env.services.bus_service, {
        send: (type, payload) => {
            if (type === "update_presence") {
                assertAlmostEqual(expectedInactivityPeriod, payload.inactivity_period);
                step("update_presence");
            }
        },
    });
    patchWithCleanup(env.services.presence, {
        getLastPresence: () => new Date().getTime() - AWAY_DELAY,
    });
    let expectedInactivityPeriod = AWAY_DELAY;
    env.services.bus_service.start();
    await assertSteps(["update_presence"]);
    const event = new StorageEvent("storage", {
        key: "presence.lastPresence",
        newValue: new Date().getTime(),
    });
    patchWithCleanup(env.services.presence, { getLastPresence: () => new Date().getTime() });
    expectedInactivityPeriod = 0;
    browser.dispatchEvent(event);
    await assertSteps(["update_presence"]);
});

QUnit.test("update presence when user status changes to away", async () => {
    const { advanceTime } = mockTimeout();
    const env = await makeTestEnv();
    let expectedInactivityPeriod = 0;
    patchWithCleanup(env.services.bus_service, {
        send: (type, payload) => {
            if (type === "update_presence") {
                assertAlmostEqual(expectedInactivityPeriod, payload.inactivity_period);
                step("update_presence");
            }
        },
    });
    env.services.bus_service.start();
    await assertSteps(["update_presence"]);
    expectedInactivityPeriod = AWAY_DELAY;
    patchWithCleanup(env.services.presence, {
        getLastPresence: () => new Date().getTime() - AWAY_DELAY,
    });
    advanceTime(AWAY_DELAY);
    await assertSteps(["update_presence"]);
});
