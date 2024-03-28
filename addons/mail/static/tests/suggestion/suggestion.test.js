import { describe, beforeEach, test } from "@odoo/hoot";

import { Composer } from "@mail/core/common/composer";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    openFormView,
    start,
    startServer,
    step,
} from "../mail_test_helpers";
import { Command, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { Deferred, tick } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    // Simulate real user interactions
    patchWithCleanup(Composer.prototype, {
        isEventTrusted() {
            return true;
        },
    });
});

test('display partner mention suggestions on typing "@"', async () => {
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
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion strong", { count: 3 });
});

test('post a first message then display partner mention suggestions on typing "@"', async () => {
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
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
            Command.create({ partner_id: partnerId_2 }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await insertText(".o-mail-Composer-input", "first message");
    await click("button:enabled", { text: "Send" });
    await contains(".o-mail-Message");
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion strong", { count: 3 });
});

test('display partner mention suggestions on typing "@" in chatter', async () => {
    await startServer();
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion strong", { text: "Mitchell Admin" });
});

test("show other channel member in @ mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
});

test("select @ mention insert mention text in composer", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
    await contains(".o-mail-Composer-input", { value: "@TestPartner " });
});

test("select @ mention closes suggestions", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
});

test('display channel mention suggestions on typing "#"', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestionList .o-open");
});

test("mention a channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General " });
});

test("Channel suggestions do not crash after rpc returns", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const deferred = new Deferred();
    onRpc("discuss.channel", "get_mention_suggestions", () => {
        step("get_mention_suggestions");
        deferred.resolve();
    });
    await start();
    await openDiscuss(channelId);
    pyEnv["discuss.channel"].create({ name: "foo" });
    insertText(".o-mail-Composer-input", "#");
    await tick();
    insertText(".o-mail-Composer-input", "f");
    await deferred;
    await assertSteps(["get_mention_suggestions"]);
});

test("Suggestions are shown after delimiter was used in text (@)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", "NonExistingUser");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " @");
    await contains(".o-mail-Composer-suggestion strong", { text: "Mitchell Admin" });
});

test("Suggestions are shown after delimiter was used in text (#)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", "NonExistingChannel");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " #");
    await contains(".o-mail-Composer-suggestion strong", { text: "#General" });
});

test("display partner mention when typing more than 2 words if they match", async () => {
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
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@My ");
    await contains(".o-mail-Composer-suggestion strong", { count: 3 });
    await insertText(".o-mail-Composer-input", "Test ");
    await contains(".o-mail-Composer-suggestion strong", { count: 2 });
    await insertText(".o-mail-Composer-input", "Partner");
    await contains(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-suggestion strong", { text: "My Test Partner" });
});

test("Internal user should be displayed first", async () => {
    const pyEnv = await startServer();
    const [user1Id, user2Id] = pyEnv["res.users"].create([{}, {}]);
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
            res_id: serverState.partnerId,
            res_model: "res.partner",
        },
        {
            is_active: true,
            partner_id: partnerIds[3], // D
            res_id: serverState.partnerId,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@Person ");
    await contains(":nth-child(1 of .o-mail-Composer-suggestion) strong", { text: "Person D" });
    await contains(":nth-child(2 of .o-mail-Composer-suggestion) strong", { text: "Person C" });
    await contains(":nth-child(3 of .o-mail-Composer-suggestion) strong", { text: "Person B" });
    await contains(":nth-child(4 of .o-mail-Composer-suggestion) strong", { text: "Person A" });
});

test("Current user that is a follower should be considered as such", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({});
    pyEnv["res.partner"].create([
        { email: "a@test.com", name: "Person A" },
        { email: "b@test.com", name: "Person B", user_ids: [userId] },
    ]);
    pyEnv["mail.followers"].create([
        {
            is_active: true,
            partner_id: serverState.partnerId,
            res_id: serverState.partnerId,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 6 }); // FIXME: should be 4, but +2 extra with Hermit / Public User
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
