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
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, test } from "@odoo/hoot";
import { Deferred, tick } from "@odoo/hoot-mock";
import { Command, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { Composer } from "@mail/core/common/composer";

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

test("can @user in restricted (group_public_id) channels", async () => {
    const pyEnv = await startServer();
    const groupId = pyEnv["res.groups"].create({
        name: "Custom Channel Group",
    });
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { email: "testpartner1@odoo.com", name: "TestPartner1" },
        { email: "testpartner2@odoo.com", name: "TestPartner2" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: partnerId_1, groups_id: [Command.link(groupId)] },
        { partner_id: partnerId_2 },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "Restricted Channel",
        group_public_id: groupId,
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Invite People']");
    await contains(".o-discuss-ChannelInvitation-invitationBox", {
        text: 'Access restricted to group "Custom Channel Group"',
    });
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion strong", { count: 2 });
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
    await click("button[aria-label='Send']:enabled");
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

test("Do not fetch if search more specific and fetch had no result", async () => {
    await startServer();
    onRpc("res.partner", "get_mention_suggestions", () => {
        step("get_mention_suggestions");
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 3 }); // Mitchell Admin, Hermit, Public user
    await contains(".o-mail-Composer-suggestion", { text: "Mitchell Admin" });
    await assertSteps(["get_mention_suggestions"]);
    await insertText(".o-mail-Composer-input", "x");
    await contains(".o-mail-Composer-suggestion", { count: 0 });
    await assertSteps(["get_mention_suggestions"]);
    await insertText(".o-mail-Composer-input", "x");
    await assertSteps([]);
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

test("mention a channel thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    pyEnv["discuss.channel"].create({
        name: "ThreadOne",
        parent_channel_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestion", { count: 2 });
    await contains(".o-mail-Composer-suggestion:eq(0):has(i.fa-hashtag)", { text: "General" });
    await contains(".o-mail-Composer-suggestion:eq(1):has(i.fa-comments-o)", {
        text: "GeneralThreadOne",
    });
    await click(".o-mail-Composer-suggestion:eq(1)");
    await contains(".o-mail-Composer-input", { value: "#General > ThreadOne " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message a.o_channel_redirect:has(i.fa-comments-o)", {
        text: "General > ThreadOne",
    });
    await click("a.o_channel_redirect", { text: "General > ThreadOne" });
    await contains(".o-mail-DiscussSidebar-item.o-active", { text: "ThreadOne" });
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
    await insertText(".o-mail-Composer-input", "#");
    await tick();
    await insertText(".o-mail-Composer-input", "f");
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
    await contains(".o-mail-Composer-suggestion strong", { text: "General" });
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
    await contains(".o-mail-Composer-suggestion", { count: 5 }); // FIXME: should be 3, but +2 extra with Hermit / Public User
    await contains(".o-mail-Composer-suggestion", {
        text: "Mitchell Admin",
        before: [".o-mail-Composer-suggestion", { text: "Person B(b@test.com)" }],
    });
    await contains(".o-mail-Composer-suggestion", {
        text: "Person B(b@test.com)",
        before: [".o-mail-Composer-suggestion", { text: "Person A(a@test.com)" }],
    });
});

test("Mention with @everyone", async () => {
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
    await insertText(".o-mail-Composer-input", "@ever");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "@everyone " });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-bubble.o-orange");
    await contains(".o-mail-Message a:contains('@everyone')");
});

test("Suggestions that begin with the search term should have priority", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create([{ name: "Party Partner" }, { name: "Best Partner" }]);
    await start();
    await openFormView("res.partner", serverState.partnerId);
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
