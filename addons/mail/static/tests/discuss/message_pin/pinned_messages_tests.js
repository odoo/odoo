/** @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("pinned messages");

QUnit.test("Pin message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Pinned messages']");
    assert.containsOnce(
        $,
        ".o-discuss-PinnedMessagesPanel:contains(This channel doesn't have any pinned messages.)"
    );
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item:contains(Pin)");
    await click(".modal-footer button:contains(Confirm)");
    assert.containsOnce($, ".o-discuss-PinnedMessagesPanel .o-mail-Message:contains(Hello world)");
});

QUnit.test("Unpin message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Pinned messages']");
    assert.containsOnce($, ".o-discuss-PinnedMessagesPanel .o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item:contains(Unpin)");
    await click(".modal-footer button:contains(Confirm)");
    assert.containsNone($, ".o-discuss-PinnedMessagesPanel .o-mail-Message");
});

QUnit.test("Deleted messages are not pinned", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Pinned messages']");
    assert.containsOnce($, ".o-discuss-PinnedMessagesPanel .o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item:contains(Delete)");
    await click("button:contains(Confirm)");
    assert.containsNone($, ".o-discuss-PinnedMessagesPanel .o-mail-Message");
});

QUnit.test("Open pinned panel from notification", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message:eq(0) [title='Expand']");
    await click(".dropdown-item:contains(Pin)");
    await click(".modal-footer button:contains(Confirm)");
    assert.containsNone($, ".o-discuss-PinnedMessagesPanel");
    await click(".o_mail_notification a:contains(See all pinned messages)");
    assert.containsOnce($, ".o-discuss-PinnedMessagesPanel");
});

QUnit.test("Jump to message", async (assert) => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return this._super(true);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-04-03 08:15:04",
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header button[title='Pinned messages']");
    await click(".o-discuss-PinnedMessagesPanel button:contains(Jump)");
    await nextTick();
    assert.isVisible($(".o-mail-Message:contains(Hello world!)"));
});

QUnit.test("Jump to message from notification", async (assert) => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return this._super(true);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message:eq(0) [title='Expand']");
    await click(".dropdown-item:contains(Pin)");
    await click(".modal-footer button:contains(Confirm)");
    await click(".o_mail_notification a:contains(message)");
    await nextTick();
    assert.isVisible($(".o-mail-Message:contains(Hello world!)"));
});
