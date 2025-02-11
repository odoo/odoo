/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("mobile");

QUnit.test("auto-select 'Inbox' when discuss had channel as active thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });

    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Channel" });

    await click("button", { text: "Mailboxes" });
    await contains(".o-mail-MessagingMenu-tab.text-primary.fw-bolder", { text: "Mailboxes" });
    await contains("button.active", { text: "Inbox" });
});
