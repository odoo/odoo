/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { Command } from "@mail/../tests/helpers/command";
import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("suggestion", {
    async beforeEach() {
        // Simulate real user interactions
        patchWithCleanup(Composer.prototype, {
            isEventTrusted() {
                return true;
            },
        });
    },
});

QUnit.test('display command suggestions on typing "/"', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    await insertText(".o-mail-Composer-input", "/");
    assert.containsOnce($, ".o-mail-Composer-suggestionList .o-open");
});

QUnit.test("use a command for a specific channel type", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
    await insertText(".o-mail-Composer-input", "/");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual(
        $(".o-mail-Composer-input").val().replace(/\s/, " "),
        "/who ",
        "command + additional whitespace afterwards"
    );
});

QUnit.test(
    "command suggestion should only open if command is the first character",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            name: "General",
            channel_type: "channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
        assert.strictEqual($(".o-mail-Composer-input").val(), "");
        await insertText(".o-mail-Composer-input", "bluhbluh ");
        assert.strictEqual($(".o-mail-Composer-input").val(), "bluhbluh ");
        await insertText(".o-mail-Composer-input", "/");
        assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    }
);

QUnit.test("Sort partner suggestions by recent chats", async (assert) => {
    const pyEnv = await startServer();
    const [partner_1, partner_2, partner_3] = pyEnv["res.partner"].create([
        { name: "User 1" },
        { name: "User 2" },
        { name: "User 3" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: partner_1 },
        { partner_id: partner_2 },
        { partner_id: partner_3 },
    ]);
    pyEnv["discuss.channel"].create([
        { name: "General", channel_type: "channel" },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:00",
                    partner_id: pyEnv.currentPartnerId,
                }),
                Command.create({ partner_id: partner_1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:00",
                    partner_id: pyEnv.currentPartnerId,
                }),
                Command.create({ partner_id: partner_2 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2023-01-01 00:00:00",
                    partner_id: pyEnv.currentPartnerId,
                }),
                Command.create({ partner_id: partner_3 }),
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-DiscussCategoryItem:contains('User 2')");
    await insertText(".o-mail-Composer-input", "This is a test");
    await click(".o-mail-Composer-send:not(:disabled)");
    assert.containsOnce($, ".o-mail-Message:contains('This is a test')");
    await click(".o-mail-DiscussCategoryItem:contains('General')");
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "User");
    assert.containsN($, ".o-mail-Composer-suggestion", 3);
    assert.strictEqual($(".o-mail-Composer-suggestion").eq(0).text(), "User 2");
    assert.strictEqual($(".o-mail-Composer-suggestion").eq(1).text(), "User 1");
    assert.strictEqual($(".o-mail-Composer-suggestion").eq(2).text(), "User 3");
});
