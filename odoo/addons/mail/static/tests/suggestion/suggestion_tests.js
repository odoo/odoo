/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Composer } from "@mail/core/common/composer";
import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

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
        await click("button:enabled", { text: "Send" });
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

QUnit.test("Internal user should be displayed first", async () => {
    const pyEnv = await startServer();
    const [user1Id, user2Id] = pyEnv["res.users"].create([{ share: true }, { share: true }]);
    const partnerIds = pyEnv["res.partner"].create([
        { name: "Person A" },
        { name: "Person B" },
        { name: "Person C", user_ids: [user1Id] },
        { name: "Person D", user_ids: [user2Id] },
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
    openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@Person ");
    await contains(":nth-child(1 of .o-mail-Composer-suggestion) strong", { text: "Person D" });
    await contains(":nth-child(2 of .o-mail-Composer-suggestion) strong", { text: "Person C" });
    await contains(":nth-child(3 of .o-mail-Composer-suggestion) strong", { text: "Person B" });
    await contains(":nth-child(4 of .o-mail-Composer-suggestion) strong", { text: "Person A" });
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
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 4 });
    await contains(".o-mail-Composer-suggestion", {
        text: "Mitchell Admin",
        before: [".o-mail-Composer-suggestion", { text: "Person B(b@test.com)" }],
    });
    await contains(".o-mail-Composer-suggestion", {
        text: "Person B(b@test.com)",
        before: [".o-mail-Composer-suggestion", { text: "OdooBot" }],
    });
    await contains(".o-mail-Composer-suggestion", {
        text: "OdooBot",
        before: [".o-mail-Composer-suggestion", { text: "Person A(a@test.com)" }],
    });
});

QUnit.test("Suggestions that begin with the search term should have priority", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create([{ name: "Party Partner" }, { name: "Best Partner" }]);
    const { openFormView } = await start();
    openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", {
        text: "Best Partner",
        before: [".o-mail-Composer-suggestion", { text: "Party Partner" }],
    });
    await insertText(".o-mail-Composer-input", "part");
    await contains(".o-mail-Composer-suggestion", {
        text: "Party Partner",
        before: [".o-mail-Composer-suggestion", { text: "Best Partner" }],
    });
});
