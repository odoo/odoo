/** @odoo-module **/

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mobile");

QUnit.test("auto-select 'Inbox' when discuss had channel as active thread", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "test" });

    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss(channelId, { waitUntilMessagesLoaded: false });
    assert.containsOnce($, ".o-mail-messaging-menu-tab.text-primary.fw-bolder:contains(Channel)");

    await click("button:contains(Mailboxes)");
    assert.containsOnce($, ".o-mail-messaging-menu-tab.text-primary.fw-bolder:contains(Mailboxes)");
    assert.containsOnce($, "button:contains(Inbox).active");
});
