/* @odoo-module */

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { click, contains, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mobile");

QUnit.test("auto-select 'Inbox' when discuss had channel as active thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });

    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    openDiscuss(channelId, { waitUntilMessagesLoaded: false });
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Channel" });

    await click("button", { text: "Mailboxes" });
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Mailboxes" });
    await contains("button:contains(Inbox).active");
});
