import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";
import { mockDate } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineLivechatModels();

test("Can invite a partner to a livechat channel", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        name: "Visitor 20",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 12:00:00",
            }),
            Command.create({ guest_id: guestId, last_interest_dt: "2021-01-03 12:00:00" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Invite People']");
    await click("input", {
        parent: [".o-discuss-ChannelInvitation-selectable", { text: "James" }],
    });
    await click("button:enabled", { text: "Invite" });
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await click("button[title='Members']");
    await contains(".o-discuss-ChannelMember", { text: "James" });
});

test("Available operators come first", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create({
        name: "Harry",
        im_status: "offline",
        user_ids: [pyEnv["res.users"].create({ name: "Harry" })],
    });
    const ronId = pyEnv["res.partner"].create({
        name: "Ron",
        im_status: "online",
        user_ids: [pyEnv["res.users"].create({ name: "Available operator" })],
    });
    pyEnv["im_livechat.channel"].create({
        available_operator_ids: [Command.create({ partner_id: ronId })],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #1" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #1",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Invite People']");
    await contains(".o-discuss-ChannelInvitation-selectable", { count: 2 });
    await contains(":nth-child(1 of .o-discuss-ChannelInvitation-selectable)", { text: "Ron" });
    await contains(":nth-child(2 of .o-discuss-ChannelInvitation-selectable)", { text: "Harry" });
});

test("Partners invited most frequently by the current user come first", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    pyEnv["res.partner"].create({
        name: "John",
        im_status: "offline",
        user_ids: [pyEnv["res.users"].create({ name: "John" })],
    });
    pyEnv["res.partner"].create({
        name: "Albert",
        im_status: "offline",
        user_ids: [pyEnv["res.users"].create({ name: "Albert" })],
    });
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor #1" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #1",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 12:00:00",
            }),
            Command.create({ guest_id: guestId_1, last_interest_dt: "2021-01-03 12:00:00" }),
        ],
        livechat_operator_id: serverState.partnerId,
    });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor #2" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #2",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 11:00:00",
            }),
            Command.create({ guest_id: guestId_2, last_interest_dt: "2021-01-03 11:00:00" }),
        ],
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "Visitor #1" });
    await click("button[title='Invite People']");
    await click("input", { parent: [".o-discuss-ChannelInvitation-selectable", { text: "John" }] });
    await click("button:enabled", { text: "Invite" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Visitor #2" });
    await click("button[title='Invite People']");
    await contains(".o-discuss-ChannelInvitation-selectable", { count: 2 });
    await contains(":nth-child(1 of .o-discuss-ChannelInvitation-selectable)", { text: "John" });
    await contains(":nth-child(2 of .o-discuss-ChannelInvitation-selectable)", { text: "Albert" });
});
