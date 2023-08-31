/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { Command } from "@mail/../tests/helpers/command";
import { click, contains, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

import { makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

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

QUnit.test('display partner mention suggestions on typing "@"', async () => {
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
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion strong", { count: 3 });
});

QUnit.test(
    'post a first message then display partner mention suggestions on typing "@"',
    async () => {
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
        openDiscuss(channelId);
        await contains(".o-mail-Composer-input");
        await insertText(".o-mail-Composer-input", "first message");
        await click("button:contains(Send):not(:disabled)");
        await contains(".o-mail-Message");
        await insertText(".o-mail-Composer-input", "@");
        await contains(".o-mail-Composer-suggestion strong", { count: 3 });
    }
);

QUnit.test('display partner mention suggestions on typing "@" in chatter', async () => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion strong", { text: "Mitchell Admin" });
});

QUnit.test("show other channel member in @ mention", async () => {
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
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
});

QUnit.test("select @ mention insert mention text in composer", async () => {
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
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
    await contains(".o-mail-Composer-input", { value: "@TestPartner " });
});

QUnit.test("select @ mention closes suggestions", async () => {
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
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
});

QUnit.test('display channel mention suggestions on typing "#"', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestionList .o-open");
});

QUnit.test("mention a channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General " });
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
    openDiscuss(channelId);
    pyEnv["discuss.channel"].create({ name: "foo" });
    insertText(".o-mail-Composer-input", "#");
    await nextTick();
    insertText(".o-mail-Composer-input", "f");
    await deferred;
    assert.verifySteps(["get_mention_suggestions"]);
});

QUnit.test("Suggestions are shown after delimiter was used in text (@)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", "NonExistingUser");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " @");
    await contains(".o-mail-Composer-suggestion strong", { text: "Mitchell Admin" });
});

QUnit.test("Suggestions are shown after delimiter was used in text (#)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", "NonExistingChannel");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " #");
    await contains(".o-mail-Composer-suggestion strong", { text: "#General" });
});

QUnit.test("display partner mention when typing more than 2 words if they match", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create([
        {
            email: "test1@example.com",
            name: "My Best Partner",
        },
        {
            email: "test2@example.com",
            name: "My Test User",
        },
        {
            email: "test3@example.com",
            name: "My Test Partner",
        },
    ]);
    const { openFormView } = await start();
    openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@My ");
    await contains(".o-mail-Composer-suggestion strong", { count: 3 });
    await insertText(".o-mail-Composer-input", "Test ");
    await contains(".o-mail-Composer-suggestion strong", { count: 2 });
    await insertText(".o-mail-Composer-input", "Partner");
    await contains(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-suggestion strong", { text: "My Test Partner" });
});
