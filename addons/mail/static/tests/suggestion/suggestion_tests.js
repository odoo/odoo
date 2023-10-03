/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { Command } from "@mail/../tests/helpers/command";
import { click, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

import {
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";

import { contains } from "@web/../tests/utils";

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

QUnit.test("Suggestions are shown after delimiter was used in text (@)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    assert.containsOnce($, ".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", "NonExistingUser");
    assert.containsNone($, ".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", " ");
    await insertText(".o-mail-Composer-input", "@");
    assert.containsOnce($, ".o-mail-Composer-suggestion:contains(Mitchell Admin)");
});

QUnit.test("Suggestions are shown after delimiter was used in text (#)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    assert.containsOnce($, ".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", "NonExistingChannel");
    assert.containsNone($, ".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", " ");
    await insertText(".o-mail-Composer-input", "#");
    assert.containsOnce($, ".o-mail-Composer-suggestion:contains(General)");
});

QUnit.test("Internal user should be displayed first", async (assert) => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ share: true });
    const partnerIds = pyEnv["res.partner"].create([
        { email: "a@test.com", name: "Person A" },
        { email: "b@test.com", name: "Person B" },
        { email: "c@test.com", name: "Person C", user_ids: [userId] },
        { email: "d@test.com", name: "Person D", user_ids: [userId] },
    ]);
    pyEnv["mail.followers"].create([
        {
            is_active: true,
            partner_id: partnerIds[1], // B
            res_id: pyEnv.currentPartnerId,
            res_model: "res.partner",
        },
        {
            is_active: true,
            partner_id: partnerIds[3], // D
            res_id: pyEnv.currentPartnerId,
            res_model: "res.partner",
        },
    ]);
    const { openFormView } = await start();
    await openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button:contains(Send message)");
    await insertText(".o-mail-Composer-input", "@Person ");
    const suggestions = document.querySelectorAll(".o-mail-Composer-suggestion");
    assert.strictEqual(suggestions[0].textContent, "Person D(d@test.com)");
    assert.strictEqual(suggestions[1].textContent, "Person C(c@test.com)");
    assert.strictEqual(suggestions[2].textContent, "Person B(b@test.com)");
    assert.strictEqual(suggestions[3].textContent, "Person A(a@test.com)");
});

QUnit.test("Current user that is a follower should be considered as such", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ share: true });
    pyEnv["res.partner"].create([
        { email: "a@test.com", name: "Person A" },
        { email: "b@test.com", name: "Person B", user_ids: [userId] },
    ]);
    pyEnv["mail.followers"].create([
        {
            is_active: true,
            partner_id: pyEnv.currentPartnerId,
            res_id: pyEnv.currentPartnerId,
            res_model: "res.partner",
        },
    ]);
    const { openFormView } = await start();
    await openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button:contains(Send message)");
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 3 });
    await contains(".o-mail-Composer-suggestion", {
        text: "Mitchell Admin",
        before: [".o-mail-Composer-suggestion", { text: "Person B(b@test.com)" }],
    });
    await contains(".o-mail-Composer-suggestion", {
        text: "Person B(b@test.com)",
        before: [".o-mail-Composer-suggestion", { text: "Person A(a@test.com)" }],
    });
});
