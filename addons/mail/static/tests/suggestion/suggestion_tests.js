/** @odoo-module **/

import { Composer } from "@mail/composer/composer";
import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

import {
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";

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

QUnit.test('display partner mention suggestions on typing "@"', async (assert) => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const partnerId_2 = pyEnv["res.partner"].create({
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    pyEnv["res.users"].create({ partner_id: partnerId_1 });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestion");

    await insertText(".o-mail-Composer-input", "@");
    assert.containsN($, ".o-mail-Composer-suggestion", 3);
});

QUnit.test(
    'post a first message then display partner mention suggestions on typing "@"',
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId_1 = pyEnv["res.partner"].create({
            email: "testpartner@odoo.com",
            name: "TestPartner",
        });
        const partnerId_2 = pyEnv["res.partner"].create({
            email: "testpartner2@odoo.com",
            name: "TestPartner2",
        });
        pyEnv["res.users"].create({ partner_id: partnerId_1 });
        const channelId = pyEnv["discuss.channel"].create({
            name: "general",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId_1 }),
                Command.create({ partner_id: partnerId_2 }),
            ],
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsNone($, ".o-mail-Composer-suggestion");
        await insertText(".o-mail-Composer-input", "first message");
        triggerHotkey("Enter");
        await nextTick();

        await insertText(".o-mail-Composer-input", "@");
        assert.containsN($, ".o-mail-Composer-suggestion", 3);
    }
);

QUnit.test('display partner mention suggestions on typing "@" in chatter', async (assert) => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    await openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button:contains(Send message)");
    assert.containsNone($, ".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", "@");
    assert.containsOnce($, ".o-mail-Composer-suggestion:contains(Mitchell Admin)");
});

QUnit.test("show other channel member in @ mention", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    assert.containsOnce($, ".o-mail-Composer-suggestion:contains(TestPartner)");
});

QUnit.test("select @ mention insert mention text in composer", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion:contains(TestPartner)");
    assert.strictEqual($(".o-mail-Composer-input").val().trim(), "@TestPartner");
});

QUnit.test('display channel mention suggestions on typing "#"', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    await insertText(".o-mail-Composer-input", "#");
    assert.containsOnce($, ".o-mail-Composer-suggestionList .o-open");
});

QUnit.test("mention a channel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestionList .o-open");
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
    await insertText(".o-mail-Composer-input", "#");
    assert.containsOnce($, ".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual(
        $(".o-mail-Composer-input").val().replace(/\s/, " "),
        "#General ",
        "mentioned channel + additional whitespace afterwards"
    );
});

QUnit.test("Channel suggestions do not crash after rpc returns", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const deferred = makeDeferred();
    const { openDiscuss } = await start({
        async mockRPC(args, params, originalFn) {
            if (params.method === "get_mention_suggestions") {
                const res = await originalFn(args, params);
                assert.step("get_mention_suggestions");
                deferred.resolve();
                return res;
            }
            return originalFn(args, params);
        },
    });
    await openDiscuss(channelId);
    pyEnv["discuss.channel"].create({ name: "foo" });
    insertText(".o-mail-Composer-input", "#");
    await nextTick();
    insertText(".o-mail-Composer-input", "f");
    await deferred;
    assert.verifySteps(["get_mention_suggestions"]);
});
