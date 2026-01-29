/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";
import { nextTick } from "@web/../tests/helpers/utils";

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

QUnit.test("Show send button in mobile", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.SM });
    pyEnv["discuss.channel"].create({ name: "minecraft-wii-u" });
    const { openDiscuss } = await start();
    openDiscuss();
    await click("button", { text: "Channel" });
    await click(".o-mail-NotificationItem", { text: "minecraft-wii-u" });
    await nextTick();
    await contains(".o-mail-Composer button[aria-label='Send']");
    await contains(".o-mail-Composer button[aria-label='Send'] i.fa-paper-plane-o");
});

QUnit.test("Edit message (mobile)", async () => {
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button", { text: "Channel" });
    await click("button", { text: "general" });
    await contains(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await contains(".o-mail-Message-editable .o-mail-Composer-input", { value: "Hello world" });
    await click("button", { text: "Discard editing" });
    await contains(".o-mail-Message-editable .o-mail-Composer", { count: 0 });
    await contains(".o-mail-Message-content", { text: "Hello world" });
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "edited message", { replace: true });
    await nextTick();
    await click(".o-mail-Message .fa-paper-plane-o");
    await contains(".o-mail-Message-content", { text: "edited message" });
});
