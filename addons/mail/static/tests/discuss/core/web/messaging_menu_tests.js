/* @odoo-module */

import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("messaging menu");

QUnit.test('"Start a conversation" item selection opens chat', async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Gandalf" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Chat)");
    await click("button:contains(Start a conversation)");
    await insertText("input[placeholder='Start a conversation']", "Gandalf");
    await click(".o-discuss-ChannelSelector-suggestion");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce($, ".o-mail-ChatWindow-name[title='Gandalf']");
});

QUnit.test('"New channel" item selection opens channel (existing)', async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Gryffindors" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Channel)");
    await click("button:contains(New Channel)");
    await insertText("input[placeholder='Add or join a channel']", "Gryff");
    await click(".o-discuss-ChannelSelector-suggestion");
    assert.containsOnce($, ".o-mail-ChatWindow-name[title='Gryffindors']");
});

QUnit.test('"New channel" item selection opens channel (new)', async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Channel)");
    await click("button:contains(New Channel)");
    await insertText("input[placeholder='Add or join a channel']", "slytherins");
    await click(".o-discuss-ChannelSelector-suggestion");
    assert.containsOnce($, ".o-mail-ChatWindow-name[title='slytherins']");
});

QUnit.test("new message [REQUIRE FOCUS]", async (assert) => {
    await start();
    await click(".o_menu_systray .dropdown-toggle:has(i[aria-label='Messages'])");
    await click('.o-mail-MessagingMenu button:contains("New Message")');
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow .o-discuss-ChannelSelector");
    assert.containsOnce($, ".o-discuss-ChannelSelector input:focus");
});
