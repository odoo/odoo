import { onWebsocketEvent } from "@bus/../tests/mock_websocket";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

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

test("subscribe to known partner presences", async () => {
    onWebsocketEvent("subscribe", (data) => step(`subscribe - [${data.channels}]`));
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({
        name: "Bob",
        user_ids: [Command.create({ name: "bob" })],
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await openDiscuss();
    const expectedPresences = [
        `odoo-presence-res.partner_${serverState.partnerId}`,
        `odoo-presence-res.partner_${serverState.odoobotId}`,
    ];
    await assertSteps([`subscribe - [${expectedPresences.join(",")}]`]);
    await click("[title='Start a conversation']");
    await insertText(".o-discuss-ChannelSelector input", "bob");
    await click(".o-discuss-ChannelSelector-suggestion");
    await triggerHotkey("Enter");
    expectedPresences.push(`odoo-presence-res.partner_${bobPartnerId}`);
    await assertSteps([`subscribe - [${expectedPresences.join(",")}]`]);
});

test("bus subscription is refreshed when channel is joined", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    onWebsocketEvent("subscribe", () => step("subscribe"));
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await assertSteps(["subscribe"]);
    await openDiscuss();
    await assertSteps([]);
    await click(".o-mail-DiscussSidebar [title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "new channel");
    await click(".o-discuss-ChannelSelector-suggestion");
    await assertSteps(["subscribe"]);
});

test("bus subscription is refreshed when channel is left", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    onWebsocketEvent("subscribe", () => step("subscribe"));
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await assertSteps(["subscribe"]);
    await openDiscuss();
    await assertSteps([]);
    await click("[title='Leave Channel']");
    await assertSteps(["subscribe"]);
});
