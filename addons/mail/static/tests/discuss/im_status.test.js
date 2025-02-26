import { AWAY_DELAY } from "@mail/core/common/im_status_service";
import { defineMailModels, start, startServer } from "@mail/../tests/mail_test_helpers";

import { beforeEach, describe, test } from "@odoo/hoot";
import { advanceTime, freezeTime } from "@odoo/hoot-dom";
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js
import {
    asyncStep,
    makeMockEnv,
    makeMockServer,
    mockService,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { defineBusModels } from "./bus_test_helpers";
=======
import {
    asyncStep,
    makeMockEnv,
    MockServer,
    mockService,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { defineBusModels } from "./bus_test_helpers";
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js

import { asyncStep, mockService, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

defineMailModels();
beforeEach(freezeTime);
describe.current.tags("headless");

test("update presence if IM status changes to offline while this device is online", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
    const pyEnv = await startServer();
    await start();
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js

    const { env } = await makeMockServer();
    await makeMockEnv();
=======

    await makeMockEnv();
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js
    await waitForSteps(["update_presence"]);
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js
    env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
=======
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js
        im_status: "offline",
        partner_id: serverState.partnerId,
    });
    await waitForSteps(["update_presence"]);
});

test("update presence if IM status changes to away while this device is online", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
    localStorage.setItem("presence.lastPresence", Date.now());
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
    const pyEnv = await startServer();
    await start();
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js

    const { env } = await makeMockServer();
    await makeMockEnv();
=======

    await makeMockEnv();
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js
    await waitForSteps(["update_presence"]);
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js
    env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
=======
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await waitForSteps(["update_presence"]);
});

test("do not update presence if IM status changes to away while this device is away", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
    localStorage.setItem("presence.lastPresence", Date.now() - AWAY_DELAY);
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
    const pyEnv = await startServer();
    await start();
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js

    const { env } = await makeMockServer();
    await makeMockEnv();
=======

    await makeMockEnv();
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js
    await waitForSteps(["update_presence"]);
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js
    env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
=======
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await waitForSteps([]);
});

test("do not update presence if other user's IM status changes to away", async () => {
    mockService("bus_service", { send: (type) => asyncStep(type) });
    localStorage.setItem("presence.lastPresence", Date.now());
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
    const pyEnv = await startServer();
    await start();
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js

    const { env } = await makeMockServer();
    await makeMockEnv();
=======

    await makeMockEnv();
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js
    await waitForSteps(["update_presence"]);
<<<<<<< saas-18.2:addons/mail/static/tests/discuss/im_status.test.js
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
||||||| 612b42687237e534b5f06359652b858afe6a51e3:addons/bus/static/tests/im_status.test.js
    env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
=======
    MockServer.env["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
>>>>>>> fe09b7843f7fbcad3356d70d1150689e2b1e74d7:addons/bus/static/tests/im_status.test.js
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
