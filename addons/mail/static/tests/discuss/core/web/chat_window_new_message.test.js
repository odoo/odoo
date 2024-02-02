/** @odoo-module */

import { expect, test } from "@odoo/hoot";

import {
    CHAT_WINDOW_END_GAP_WIDTH,
    CHAT_WINDOW_INBETWEEN_WIDTH,
    CHAT_WINDOW_WIDTH,
} from "@mail/core/common/chat_window_service";
import {
    click,
    contains,
    insertText,
    patchUiSize,
    start,
    startServer,
} from "../../../mail_test_helpers";
import { Command, constants } from "@web/../tests/web_test_helpers";

test.skip("basic rendering", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-ChatWindow-header");
    await contains(".o-mail-ChatWindow-header", { text: "New message" });
    await contains(".o-mail-ChatWindow-header .o-mail-ChatWindow-command", { count: 2 });
    await contains(".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Fold']");
    await contains(
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Close Chat Window']"
    );
    await contains("span", { text: "To :" });
    await contains(".o-discuss-ChannelSelector");
});

test.skip("focused on open [REQUIRE FOCUS]", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow .o-discuss-ChannelSelector input:focus");
});

test.skip("close", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await click(".o-mail-ChatWindow-command[title='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
});

test.skip("fold", async () => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-discuss-ChannelSelector");
    await click(".o-mail-ChatWindow-command[title='Fold']");
    await contains(".o-mail-ChatWindow .o-discuss-ChannelSelector", { count: 0 });
    await click(".o-mail-ChatWindow-command[title='Open']");
    await contains(".o-discuss-ChannelSelector");
});

test.skip('open chat from "new message" chat window should open chat in place of this "new message" chat window', async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create([
        {
            name: "channel-1",
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: constants.PARTNER_ID }),
            ],
        },
        {
            name: "channel-2",
            channel_member_ids: [
                Command.create({ fold_state: "closed", partner_id: constants.PARTNER_ID }),
            ],
        },
    ]);
    patchUiSize({ width: 1920 });
    expect(
        CHAT_WINDOW_END_GAP_WIDTH * 2 + CHAT_WINDOW_WIDTH * 3 + CHAT_WINDOW_INBETWEEN_WIDTH * 2
    ).toBeLessThan(1920, {
        message: "should have enough space to open 3 chat windows simultaneously",
    });
    await start();
    // open "new message" chat window
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-ChatWindow", { text: "channel-1" });
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(":nth-child(2 of .o-mail-ChatWindow)", { text: "New message" });
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
    await contains(":nth-child(2 of .o-mail-ChatWindow)", { text: "Partner 131" });
});

test.skip("new message chat window should close on selecting the user if chat with the user is already open", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                fold_state: "open",
                partner_id: constants.PARTNER_ID,
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

test.skip("new message autocomplete should automatically select first result", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 131" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await insertText(".o-discuss-ChannelSelector input", "131");
    await contains(".o-discuss-ChannelSelector-suggestion a.o-mail-NavigableList-active");
});
