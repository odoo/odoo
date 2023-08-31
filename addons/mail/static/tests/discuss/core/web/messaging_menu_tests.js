/* @odoo-module */

import { click, contains, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("messaging menu");

QUnit.test('"Start a conversation" item selection opens chat', async () => {
    patchUiSize({ height: 360, width: 640 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Gandalf" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start();
    openDiscuss();
    await click("button", { text: "Chat" });
    await click("button", { text: "Start a conversation" });
    await insertText("input[placeholder='Start a conversation']", "Gandalf");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", 0);
    triggerHotkey("Enter");
    await contains(".o-mail-ChatWindow-name[title='Gandalf']");
});

QUnit.test('"New channel" item selection opens channel (existing)', async () => {
    patchUiSize({ height: 360, width: 640 });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Gryffindors" });
    const { openDiscuss } = await start();
    openDiscuss();
    await click("button", { text: "Channel" });
    await click("button", { text: "New Channel" });
    await insertText("input[placeholder='Add or join a channel']", "Gryff");
    await click(".o-discuss-ChannelSelector-suggestion:eq(0)");
    await contains(".o-discuss-ChannelSelector-suggestion", 0);
    await contains(".o-mail-ChatWindow-name[title='Gryffindors']");
});

QUnit.test('"New channel" item selection opens channel (new)', async () => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    openDiscuss();
    await click("button", { text: "Channel" });
    await click("button", { text: "New Channel" });
    await insertText("input[placeholder='Add or join a channel']", "slytherins");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", 0);
    await contains(".o-mail-ChatWindow-name[title='slytherins']");
});

QUnit.test("new message [REQUIRE FOCUS]", async () => {
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click('.o-mail-MessagingMenu button:contains("New Message")');
    await contains(".o-mail-ChatWindow");
    await contains(".o-mail-ChatWindow .o-discuss-ChannelSelector");
    await contains(".o-discuss-ChannelSelector input:focus");
});
