/** @odoo-module **/

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;
QUnit.module("mobile", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test(
    "auto-select 'Inbox' when discuss had channel as active thread",
    async function (assert) {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "test" });

        patchUiSize({ height: 360, width: 640 });
        const { openDiscuss } = await start();
        await openDiscuss(channelId, { waitUntilMessagesLoaded: false });
        assert.containsOnce(
            target,
            ".o-mail-messaging-menu-tab.text-primary.fw-bolder:contains(Channel)"
        );

        await click("button:contains(Mailboxes)");
        assert.containsOnce(
            target,
            ".o-mail-messaging-menu-tab.text-primary.fw-bolder:contains(Mailboxes)"
        );
        assert.containsOnce(target, "button:contains(Inbox).active");
    }
);
