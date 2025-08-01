import { onWebsocketEvent } from "@bus/../tests/mock_websocket";
import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { asyncStep, makeMockEnv, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Member list and Pinned Messages Panel menu are exclusive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // member list open by default
    await click("[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel");
    await contains(".o-discuss-ChannelMemberList", { count: 0 });
});

test("subscribe to presence channels according to store data", async () => {
    const env = await makeMockEnv();
    const store = env.services["mail.store"];
    onWebsocketEvent("subscribe", (data) => expect.step(`subscribe - [${data.channels}]`));
    expect(env.services.bus_service.isActive).toBe(false);
    // Should not subscribe to presences as bus service is not started.
    store["res.partner"].insert({ id: 1, name: "Partner 1" });
    store["res.partner"].insert({ id: 2, name: "Partner 2" });
    await tick();
    expect.waitForSteps([]);
    // Starting the bus should subscribe to known presence channels.
    env.services.bus_service.start();
    await expect.waitForSteps([
        "subscribe - [odoo-presence-res.partner_1,odoo-presence-res.partner_2]",
    ]);
    // Discovering new presence channels should refresh the subscription.
    store["mail.guest"].insert({ id: 1 });
    await expect.waitForSteps([
        "subscribe - [odoo-presence-mail.guest_1,odoo-presence-res.partner_1,odoo-presence-res.partner_2]",
    ]);
    // Updating "im_status_access_token" should refresh the subscription.
    store["mail.guest"].insert({ id: 1, im_status_access_token: "token" });
    await expect.waitForSteps([
        "subscribe - [odoo-presence-mail.guest_1-token,odoo-presence-res.partner_1,odoo-presence-res.partner_2]",
    ]);
});

test("bus subscription is refreshed when channel is joined", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    onWebsocketEvent("subscribe", () => asyncStep("subscribe"));
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await waitForSteps(["subscribe"]);
    await openDiscuss();
    await waitForSteps([]);
    await click("input[placeholder='Search conversations']");
    await insertText("input[placeholder='Search a conversation']", "new channel");
    await waitForSteps(["subscribe"]);
});

test("bus subscription is refreshed when channel is left", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    onWebsocketEvent("subscribe", () => asyncStep("subscribe"));
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await waitForSteps(["subscribe"]);
    await openDiscuss();
    await waitForSteps([]);
    await click("[title='Channel Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await waitForSteps(["subscribe"]);
});
