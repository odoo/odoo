import { describe, test } from "@odoo/hoot";

import {
    click,
    contains,
    defineMailModels,
    insertText,
    patchUiSize,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("basic rendering", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-ChatWindow-header");
    await contains(".o-mail-ChatWindow-header", { text: "New message" });
    await contains(".o-mail-ChatWindow-header .o-mail-ChatWindow-command", { count: 1 });
    await contains(
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title*='Close Chat Window']"
    );
    await contains("span", { text: "To :" });
    await contains(".o-discuss-ChannelSelector");
});

test("focused on open [REQUIRE FOCUS]", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow .o-discuss-ChannelSelector input:focus");
});

test("close", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await click(".o-mail-ChatWindow-command[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test('open chat from "new message" chat window should open new chat', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create([
        {
            name: "channel-1",
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
            ],
        },
        {
            name: "channel-2",
            channel_member_ids: [
                Command.create({ fold_state: "closed", partner_id: serverState.partnerId }),
            ],
        },
    ]);
    patchUiSize({ width: 1920 });
    await start();
    // open "new message" chat window
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { text: "channel-1" });
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(":nth-child(1 of .o-mail-ChatWindow)", { text: "New message" });
    await contains(".o-mail-ChatWindow .o-discuss-ChannelSelector");
    // open channel-2
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "channel-2" });
    await contains(".o-mail-ChatWindow", { count: 3 });
    await contains(":nth-child(2 of .o-mail-ChatWindow)", { text: "New message" });
    // search for a user in "new message" autocomplete
    await insertText(".o-discuss-ChannelSelector input", "131");
    await click(".o-discuss-ChannelSelector-suggestion a", { text: "Partner 131" });
    await contains(".o-mail-ChatWindow", { count: 0, text: "New message" });
    await contains(":nth-child(1 of .o-mail-ChatWindow)", { text: "Partner 131" });
});

test("new message chat window should close on selecting the user if chat with the user is already open", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
        name: "Partner 131",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await insertText(".o-discuss-ChannelSelector input", "131");
    await click(".o-discuss-ChannelSelector-suggestion a");
    await contains(".o-mail-ChatWindow", { count: 0, text: "New message" });
    await contains(".o-mail-ChatWindow");
});

test("new message autocomplete should automatically select first result", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await insertText(".o-discuss-ChannelSelector input", "131");
    await contains(".o-discuss-ChannelSelector-suggestion a.o-mail-NavigableList-active");
});

test('open chat from "new message" should open chat window', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "folded",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
        name: "John",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await insertText(".o-discuss-ChannelSelector input", "John");
    await click(".o-discuss-ChannelSelector-suggestion a");
    await contains(".o-mail-ChatWindow", { count: 0, text: "New message" });
    await contains(".o-mail-Thread");
});

test("Opening 'new message' twice keeps new message chat window in place", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "folded",
                partner_id: serverState.partnerId,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
        name: "John",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow", { text: "New message" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow", { text: "New message" });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "John" });
    await contains(".o-mail-ChatWindow", { text: "John" });
    await contains(".o-mail-ChatWindow", { text: "New message" });
});
