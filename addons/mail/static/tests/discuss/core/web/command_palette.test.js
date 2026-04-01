import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("can open DM from @username in command palette", async () => {
    const pyEnv = await startServer();
    const marioUid = pyEnv["res.users"].create({ name: "Mario" });
    pyEnv["res.partner"].create({ name: "Mario", user_ids: [marioUid] });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await insertText("input[placeholder='Search a conversation']", "Mario");
    await click(".o_command.focused:has(.oi-user)", { text: "Mario" });
    await contains(".o-mail-ChatWindow", { text: "Mario" });
});

test("can open channel from @channel_name in command palette", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-02 10:00:00", // same last interest to sort by id
            }),
        ],
    });
    pyEnv["discuss.channel"].create({
        name: "project",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-02 10:00:00", // same last interest to sort by id
            }),
        ],
    });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await contains(".o_command", { count: 6 });
    await contains(".o_command:eq(0):has(.fa-hashtag)", { text: "project" });
    await contains(".o_command:eq(1):has(.fa-hashtag)", { text: "general" });
    await contains(".o_command:has(.oi-user)", { text: "OdooBot" });
    await contains(".o_command:has(.oi-user)", { text: "Mitchell Admin" }); // self-conversation
    await contains(".o_command", { text: "Create Channel" });
    await contains(".o_command", { text: "Create Chat" });
    await click(".o_command.focused:has(.fa-hashtag)", { text: "project" });
    await contains(".o-mail-ChatWindow", { text: "project" });
});

test("Conversation mentions in the command palette with @", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        model: "discuss.channel",
        res_id: channelId,
        body: "@Mitchell Admin",
        needaction: true,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@", { replace: true });
    await contains(".o_command_palette .o_command_category", {
        contains: [
            ["span.fw-bold", { text: "Mentions" }],
            [".o_command.focused .o_command_name", { text: "Mitchell Admin and Mario" }],
        ],
    });
    // can also make self conversation
    await contains(".o_command_palette .o_command_category", {
        contains: [[".o_command_name", { text: "Mitchell Admin" }]],
    });
    await click(".o_command.focused");
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin and Mario" });
});

test("Max 3 most recent conversations in command palette of Discuss", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "channel_1" });
    pyEnv["discuss.channel"].create({ name: "channel_2" });
    pyEnv["discuss.channel"].create({ name: "channel_3" });
    pyEnv["discuss.channel"].create({ name: "channel_4" });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@", { replace: true });
    await contains(".o_command_palette .o_command_category", {
        contains: [
            ["span.fw-bold", { text: "Recent" }],
            [".o_command", { count: 3 }],
        ],
    });
});

test("only partners with dedicated users will be displayed in command palette", async () => {
    const pyEnv = await startServer();
    const demoUid = pyEnv["res.users"].create({ name: "Demo" });
    pyEnv["res.partner"].create({ name: "Demo", user_ids: [demoUid] });
    pyEnv["res.partner"].create({ name: "Portal" });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await contains(".o_command_name", { count: 5 });
    await contains(".o_command_name", { text: "Demo" });
    await contains(".o_command_name", { text: "OdooBot" });
    await contains(".o_command_name", { text: "Mitchell Admin" }); // self-conversation
    await contains(".o_command_name", { text: "Create Channel" });
    await contains(".o_command_name", { text: "Create Chat" });
    await contains(".o_command_name", { text: "Portal", count: 0 });
});

test("hide conversations in recent if they have mentions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: serverState.odoobotId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        model: "discuss.channel",
        res_id: channelId,
        body: "@OdooBot",
    });
    await start();
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@", { replace: true });
    await contains(".o_command_category span.fw-bold", { text: "Mentions" });
    await contains(".o_command_palette .o_command_category .o_command_name", {
        text: "OdooBot",
        count: 1,
    });
});

test("Ctrl-K opens @ command palette in discuss app", async () => {
    await start();
    await openDiscuss();
    triggerHotkey("control+k");
    await contains(".o_command_palette_search", { text: "@" });
});

test("Can create group chat from ctrl-k without any user selected", async () => {
    await start();
    await openDiscuss();
    triggerHotkey("control+k");
    await click(".o_command_name:contains(Create Chat)");
    await click(".modal-footer > .btn:contains(Create Group Chat)");
    await contains(".o-mail-DiscussSidebarChannel-itemName", { text: "Mitchell Admin" });
});
