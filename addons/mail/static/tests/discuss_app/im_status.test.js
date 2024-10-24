import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { AWAY_DELAY as ACTUAL_AWAY_DELAY } from "@mail/core/common/im_status_service";
import { describe, expect, test } from "@odoo/hoot";
import { advanceTime, tick } from "@odoo/hoot-mock";
import { Command, getService, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

describe.current.tags("desktop");
defineMailModels();

// Delays can slighly differ since time is not frozen. Let's tolerate 1000ms
// of difference.
const TOLERANCE = 1000;
const AWAY_DELAY = ACTUAL_AWAY_DELAY + TOLERANCE;
function expectAlmostEqual(a, b) {
    expect(Math.abs(a - b) < TOLERANCE).toBe(true, {
        message: `${a} and ${b} should be almost equal`,
    });
}

test("initially online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");
});

test("initially offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "offline" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Offline']");
});

test("initially away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "away" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Idle']");
});

test("change icon on change partner im_status", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "online" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ImStatus i[title='Online']");
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "offline" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "offline",
    });
    await contains(".o-mail-ImStatus i[title='Offline']");
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "away" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "away",
    });
    await contains(".o-mail-ImStatus i[title='Idle']");
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "online" });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        partner_id: serverState.partnerId,
        im_status: "online",
    });
    await contains(".o-mail-ImStatus i[title='Online']");
});

test("show im status in messaging menu preview of chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem", {
        text: "Demo",
        contains: ["i[aria-label='User is online']"],
    });
});

test("update presence if IM status changes to offline while this device is online", async () => {
    const pyEnv = await startServer();
    await start();
    patchWithCleanup(getService("bus_service"), { send: (type) => step(type) });
    await assertSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "offline",
        partner_id: serverState.partnerId,
    });
    await assertSteps(["update_presence"]);
});

test("update presence if IM status changes to away while this device is online", async () => {
    const pyEnv = await startServer();
    await start();
    patchWithCleanup(getService("bus_service"), { send: (type) => step(type) });
    patchWithCleanup(getService("presence"), { getLastPresence: () => new Date().getTime() });
    await assertSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await assertSteps(["update_presence"]);
});

test("do not update presence if IM status changes to away while this device is away", async () => {
    const pyEnv = await startServer();
    await start();
    patchWithCleanup(getService("bus_service"), { send: (type) => step(type) });
    patchWithCleanup(getService("presence"), {
        getLastPresence: () => new Date().getTime() - AWAY_DELAY,
    });
    await assertSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: serverState.partnerId,
    });
    await tick();
    await assertSteps([]);
});

test("do not update presence if other user's IM status changes to away", async () => {
    const pyEnv = await startServer();
    await start();
    patchWithCleanup(getService("bus_service"), { send: (type) => step(type) });
    patchWithCleanup(getService("presence"), { getLastPresence: () => new Date().getTime() });
    await assertSteps(["update_presence"]);
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "bus.bus/im_status_updated", {
        im_status: "away",
        partner_id: serverState.publicPartnerId,
    });
    await tick();
    await assertSteps([]);
});

test("update presence when user comes back from away", async () => {
    await start();
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
    await start();
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
