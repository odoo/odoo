import {
    SIZES,
    assertSteps,
    click,
    contains,
    defineMailModels,
    hover,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    patchUiSize,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { leave, press, queryFirst } from "@odoo/hoot-dom";
import { Deferred, mockDate, tick } from "@odoo/hoot-mock";
import {
    Command,
    mockService,
    onRpc,
    patchWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { getOrigin, url } from "@web/core/utils/urls";

const { DateTime } = luxon;

describe.current.tags("desktop");
defineMailModels();

test("Start edition on click edit", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await contains(".o-mail-Message .o-mail-Composer-input", { value: "Hello world" });
    await click("a[role='button']", { text: "cancel" });
    await contains(".o-mail-Message .o-mail-Composer-input", { count: 0 });
});

test("Edit message (mobile)", async () => {
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await contains(".o-mail-Message.o-editing .o-mail-Composer-input", { value: "Hello world" });
    await click("button", { text: "Discard editing" });
    await contains(".o-mail-Message.o-editing .o-mail-Composer", { count: 0 });
    await contains(".o-mail-Message-content", { text: "Hello world" });
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "edited message", { replace: true });
    await click(".o-mail-Message .fa-paper-plane-o");
    await contains(".o-mail-Message-content", { text: "edited message (edited)" });
});

test("Editing message keeps the mentioned channels", async () => {
    const pyEnv = await startServer();
    const channelId1 = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["discuss.channel"].create({
        name: "other",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId1);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion strong", { text: "other" });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o_channel_redirect", { count: 1, text: "other" });
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await contains(".o-mail-Message .o-mail-Composer-input", { value: "#other" });
    await insertText(".o-mail-Message .o-mail-Composer-input", "#other bye", { replace: true });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-content", { text: "other bye (edited)" });
    await click(".o_channel_redirect", { text: "other" });
    await contains(".o-mail-Discuss-threadName", { value: "other" });
});

test("Can edit message comment in chatter", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "original message",
        message_type: "comment",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "edited message", { replace: true });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-content", { text: "edited message (edited)" });
});

test("Can edit message comment in chatter (mobile)", async () => {
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "original message",
        message_type: "comment",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await contains("button", { text: "Discard editing" });
    await insertText(".o-mail-Message .o-mail-Composer-input", "edited message", { replace: true });
    await click("button[aria-label='Save editing']");
    await contains(".o-mail-Message-content", { text: "edited message (edited)" });
});

test("Cursor is at end of composer input on edit", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "",
    });
    pyEnv["mail.message"].create({
        body: "sattva",
        res_id: channelId,
        model: "discuss.channel",
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    const textarea = queryFirst(".o-mail-Composer-input");
    const contentLength = textarea.value.length;
    expect(textarea.selectionStart).toBe(contentLength);
    expect(textarea.selectionEnd).toBe(contentLength);
});

test("Stop edition on click cancel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await click(".o-mail-Message a", { text: "cancel" });
    await contains(".o-mail-Message.o-editing .o-mail-Composer", { count: 0 });
});

test("Stop edition on press escape", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    triggerHotkey("Escape", false);
    await contains(".o-mail-Message.o-editing .o-mail-Composer", { count: 0 });
});

test("Stop edition on click save", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message.o-editing .o-mail-Composer", { count: 0 });
});

test("Stop edition on press enter", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    triggerHotkey("Enter", false);
    await contains(".o-mail-Message.o-editing .o-mail-Composer", { count: 0 });
});

test("Do not stop edition on click away when clicking on emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await click(".o-mail-Composer button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content :nth-child(1 of .o-Emoji)");
    await contains(".o-mail-Message.o-editing .o-mail-Composer");
});

test("Edit and click save", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "Goodbye World", { replace: true });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-body", { text: "Goodbye World (edited)" });
});

test("Do not call server on save if no changes", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    onRpcBefore("/mail/message/update_content", () => step("update_content"));
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await click(".o-mail-Message a", { text: "save" });
    await assertSteps([]);
});

test("Update the link previews when a message is edited", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    onRpcBefore("/mail/link_preview", (args) => step("link_preview"));
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "http://odoo.com", {
        replace: true,
    });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-body", { text: "http://odoo.com" });
    await assertSteps(["link_preview"]);
});

test("Scroll bar to the top when edit starts", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world!".repeat(1000),
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await contains(".o-mail-Message .o-mail-Composer-input");
    const textarea = document.querySelector(".o-mail-Message .o-mail-Composer-input");
    expect(textarea.scrollHeight).toBeGreaterThan(textarea.clientHeight);
    await contains(".o-mail-Message .o-mail-Composer-input", { scroll: 0 });
});

test("mentions are kept when editing message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello @Mitchell Admin",
        model: "discuss.channel",
        partner_ids: [serverState.partnerId],
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "Hi @Mitchell Admin", {
        replace: true,
    });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message", {
        text: "Hi @Mitchell Admin (edited)",
        contains: ["a.o_mail_redirect", { text: "@Mitchell Admin" }],
    });
});

test("can add new mentions when editing message", async () => {
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
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello",
        model: "discuss.channel",
        partner_ids: [serverState.partnerId],
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", " @");
    await click(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
    await contains(".o-mail-Composer-input", { value: "Hello @TestPartner " });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message", {
        text: "Hello @TestPartner (edited)",
        contains: ["a.o_mail_redirect", { text: "@TestPartner" }],
    });
});

test("Other messages are grayed out when replying to another one", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create([
        { body: "Hello world", res_id: channelId, model: "discuss.channel" },
        { body: "Goodbye world", res_id: channelId, model: "discuss.channel" },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 2 });
    await click(".o-mail-Message [title='Reply']", {
        parent: [".o-mail-Message", { text: "Hello world" }],
    });
    await contains(".o-mail-Message.opacity-50", { text: "Goodbye world" });
    await contains(".o-mail-Message:not(.opacity_50)", { text: "Hello world" });
});

test("Parent message body is displayed on replies", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Reply']");
    await insertText(".o-mail-Composer-input", "FooBarFoo");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-MessageInReply-message", { text: "Hello world" });
});

test("Updating the parent message of a reply also updates the visual of the reply", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
        parent_id: messageId,
    });
    await start();
    await openDiscuss(channelId);
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "Goodbye World", {
        replace: true,
    });
    triggerHotkey("Enter");
    await contains(".o-mail-MessageInReply-message", { text: "Goodbye World (edited)" });
});

test("Deleting parent message of a reply should adapt reply visual", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Reply']");
    await insertText(".o-mail-Composer-input", "FooBarFoo");
    triggerHotkey("Enter", false);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Delete']");
    await click("button", { text: "Confirm" });
    await contains(".o-mail-MessageInReply", { text: "Original message was deleted" });
});

test("Can open emoji picker after edit mode", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await click(".o-mail-Message a", { text: "save" });
    await click("[title='Add a Reaction']");
    await contains(".o-EmojiPicker");
});

test("Can add a reaction", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅1" });
});

test("Can remove a reaction", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await click(".o-mail-MessageReaction");
    await contains(".o-mail-MessageReaction", { count: 0 });
});

test("Two users reacting with the same emoji", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    pyEnv["mail.message.reaction"].create([
        {
            message_id: messageId,
            content: "😅",
            partner_id: serverState.partnerId,
        },
        {
            message_id: messageId,
            content: "😅",
            partner_id: partnerId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-MessageReaction", { text: "😅2" });
    await click(".o-mail-MessageReaction", { text: "😅1" });
    await contains(".o-mail-MessageReaction", { text: "😅2" });
});

test("Can quickly add a reaction", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅1" });
    await hover(".o-mail-MessageReactions");
    await click("button[title='Add Reaction']");
    await click(".o-Emoji", { text: "😏" });
    await contains(".o-mail-MessageReaction", { text: "😏1" });
});

test("Reaction summary", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "Hello world" });
    const partnerNames = ["Foo", "Bar", "FooBar", "Bob", "Baz"];
    const expectedSummaries = [
        "😅:sweat_smile: reacted by Foo",
        "😅:sweat_smile: reacted by Foo and Bar",
        "😅:sweat_smile: reacted by Foo, Bar, and FooBar",
        "😅:sweat_smile: reacted by Foo, Bar, FooBar, and 1 other",
        "😅:sweat_smile: reacted by Foo, Bar, FooBar, and 2 others",
    ];
    for (const [idx, name] of partnerNames.entries()) {
        const partner_id = pyEnv["res.partner"].create({ name });
        const userId = pyEnv["res.users"].create({ partner_id });
        pyEnv["res.partner"].create({ name, user_ids: [Command.link(userId)] });
        await withUser(userId, async () => {
            await click("[title='Add a Reaction']");
            await click(".o-Emoji", {
                after: ["span", { textContent: "Smileys & Emotion" }],
                text: "😅",
            });
            await contains(".o-mail-MessageReaction", { text: `😅${idx + 1}` });
            await hover(".o-mail-MessageReaction");
            await contains(".o-mail-MessageReactionList-preview", {
                text: `${expectedSummaries[idx]}`,
            });
            await leave(".o-mail-MessageReaction");
        });
    }
});

test("Add the same reaction twice from the emoji picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅1" });
});

test("basic rendering of message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>body</p>",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message .o-mail-Message-content", { text: "body" });
    const partner = pyEnv["res.partner"].search_read([["id", "=", partnerId]])[0];
    await contains(
        `.o-mail-Message .o-mail-Message-sidebar .o-mail-Message-avatarContainer img.cursor-pointer[data-src='${getOrigin()}/web/image/res.partner/${partnerId}/avatar_128?unique=${
            deserializeDateTime(partner.write_date).ts
        }']`
    );
    await contains(".o-mail-Message .o-mail-Message-header .o-mail-Message-author.cursor-pointer", {
        text: "Demo",
    });
    await contains(
        `.o-mail-Message .o-mail-Message-header .o-mail-Message-date[title='${deserializeDateTime(
            "2019-04-20 10:00:00"
        ).toLocaleString(DateTime.DATETIME_SHORT_WITH_SECONDS)}']`
    );
});

test("should not be able to reply to temporary/transient messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    // these user interactions is to forge a transient message response from channel command "/who"
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message [title='Reply']", { count: 0 });
});

test.skip("squashed transient message should not have date in the sidebar", async () => {
    // FIXME: mock timezone not working
    mockDate("2024-03-26 10:00:00", 0);
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Channel 1" });
    pyEnv["mail.message"].create([
        {
            body: "Hello world 1",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "Hello world 2",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message.o-squashed");
    await contains(".o-mail-Message.o-squashed .o-mail-Message-sidebar", {
        text: "11:00", // FIXME: should be 10:00
    });
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { text: "You are alone in this channel." });
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send:enabled");
    await click(":nth-child(2 of .o-mail-Message.o-squashed");
    await tick();
    await contains(":nth-child(2 of .o-mail-Message.o-squashed) .o-mail-Message-sidebar", {
        text: "11:00", // FIXME: should be 10:00
        count: 0,
    });
});

test("message comment of same author within 5min. should be squashed", async () => {
    mockDate("2024-03-26 10:00:00", 0);
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            body: "<p>body1</p>",
            date: "2019-04-20 10:00:00",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: partnerId,
            body: "<p>body2</p>",
            date: "2019-04-20 10:02:30",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message", {
        contains: [
            [".o-mail-Message-content", { text: "body1" }],
            [".o-mail-Message-header"],
            [".o-mail-Message-sidebar", { contains: [".o-mail-Message-date", { count: 0 }] }],
        ],
    });
    await contains(".o-mail-Message", {
        contains: [
            [".o-mail-Message-content", { text: "body2" }],
            [".o-mail-Message-header", { count: 0 }],
            [".o-mail-Message-sidebar", { contains: [".o-mail-Message-date", { count: 0 }] }],
        ],
    });
    await click(".o-mail-Message", { text: "body2" });
    await contains(".o-mail-Message", {
        contains: [
            [".o-mail-Message-content", { text: "body2" }],
            [".o-mail-Message-sidebar .o-mail-Message-date", { text: "10:02 AM" }],
        ],
    });
});

test("open author avatar card", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        email: "demo@example.com",
        phone: "+5646548",
    });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    window.pyEnv = pyEnv;
    const [channelId_1] = pyEnv["discuss.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
    ]);
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId_1,
    });
    await start();
    await openDiscuss(channelId_1);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "General" });
    await contains(".o-mail-Discuss-content .o-mail-Message-avatarContainer img");
    await click(".o-mail-Discuss-content .o-mail-Message-avatarContainer img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Demo" });
    await contains(".o_card_user_infos > a", { text: "demo@example.com" });
    await contains(".o_card_user_infos > a", { text: "+5646548" });
});

test("toggle_star message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    onRpc("mail.message", "toggle_message_starred", ({ args }) => {
        step("rpc:toggle_message_starred");
        expect(args[0][0]).toBe(messageId);
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message [title='Mark as Todo']");
    await contains(".o-mail-Message [title='Mark as Todo']" + " i.fa-star-o");
    await contains("button", { text: "Starred", contains: [".badge", { count: 0 }] });
    await click(".o-mail-Message [title='Mark as Todo']");
    await contains("button", { text: "Starred", contains: [".badge", { text: "1" }] });
    await assertSteps(["rpc:toggle_message_starred"]);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message [title='Mark as Todo']" + " i.fa-star");
    await click(".o-mail-Message [title='Mark as Todo']");
    await contains("button", { text: "Starred", contains: [".badge", { count: 0 }] });
    await assertSteps(["rpc:toggle_message_starred"]);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message [title='Mark as Todo']" + " i.fa-star-o");
});

test("Name of message author is only displayed in chat window for partners others than the current user", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "channel" });
    const partnerId = pyEnv["res.partner"].create({ name: "Not the current user" });
    pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: partnerId,
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message-author", { text: "Not the current user" });
});

test("Name of message author is not displayed in chat window for channel of type chat", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const partnerId = pyEnv["res.partner"].create({ name: "A" });
    pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            author_id: partnerId,
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-Message-author", { count: 0 });
});

test("click on message edit button should open edit composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await contains(".o-mail-Message .o-mail-Composer");
});

test("Notification Sent", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([
        {},
        { name: "Someone", partner_share: true },
    ]);
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "email",
        model: "res.partner",
        res_id: threadId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "email",
        res_partner_id: partnerId,
    });
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-notification");
    await contains(".o-mail-Message-notification i");
    expect(".o-mail-Message-notification i:first").toHaveClass("fa-envelope-o");
    await click(".o-mail-Message-notification");
    await contains(".o-mail-MessageNotificationPopover");
    await contains(".o-mail-MessageNotificationPopover i");
    expect(".o-mail-MessageNotificationPopover i:first").toHaveClass("fa-check");
    await contains(".o-mail-MessageNotificationPopover", { text: "Someone" });
});

test("Notification Error", async () => {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv["res.partner"].create([
        {},
        { name: "Someone", partner_share: true },
    ]);
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "email",
        model: "res.partner",
        res_id: threadId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
        res_partner_id: partnerId,
    });
    const openResendActionDef = new Deferred();
    mockService("action", {
        doAction(action, options) {
            if (action?.res_model === "res.partner") {
                return super.doAction(...arguments);
            }
            step("do_action");
            expect(action).toBe("mail.mail_resend_message_action");
            expect(options.additionalContext.mail_message_to_resend).toBe(messageId);
            openResendActionDef.resolve();
        },
    });
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-notification");
    await contains(".o-mail-Message-notification i");
    expect(".o-mail-Message-notification i:first").toHaveClass("fa-envelope");
    await click(".o-mail-Message-notification").then(() => {});
    await openResendActionDef;
    await assertSteps(["do_action"]);
});

test('Quick edit (edit from Composer with ArrowUp) ignores empty ("deleted") messages.', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "", // empty body
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    triggerHotkey("ArrowUp");
    await contains(".o-mail-Message.o-editing");
    await contains(".o-mail-Message .o-mail-Composer-input", { value: "not empty" });
});

test("Editing a message to clear its composer opens message delete dialog.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message.o-editing .o-mail-Composer-input", "", { replace: true });
    triggerHotkey("Enter");
    await contains(".modal-body p", { text: "Are you sure you want to delete this message?" });
});

test("Clear message body should not open message delete dialog if it has attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
        attachment_ids: [
            pyEnv["ir.attachment"].create({ name: "test.txt", mimetype: "text/plain" }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await insertText(".o-mail-Message.o-editing .o-mail-Composer-input", "", { replace: true });
    triggerHotkey("Enter");
    await contains(".o-mail-Message-textContent", { text: "" });
    // weak test, no guarantee that we waited long enough for the potential dialog to show
    await contains(".modal-body p", {
        text: "Are you sure you want to delete this message?",
        count: 0,
    });
});

test("highlight the message mentioning the current user inside the channel", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ display_name: "Test Partner" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "hello @Admin",
        model: "discuss.channel",
        partner_ids: [serverState.partnerId],
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-bubble.o-orange");
});

test("not highlighting the message if not mentioning the current user inside the channel", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "testPartner",
        email: "testPartner@odoo.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "hello @testPartner",
        model: "discuss.channel",
        partner_ids: [partnerId],
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-bubble:not(.o-orange)");
});

test("allow attachment delete on authored message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            Command.create({
                mimetype: "image/jpeg",
                name: "BLAH",
                res_id: channelId,
                res_model: "discuss.channel",
            }),
        ],
        author_id: serverState.partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-AttachmentImage [title='Actions']");
    await click(".dropdown-item", { text: "Remove" });
    await contains(".modal-dialog .modal-body", { text: 'Do you really want to delete "BLAH"?' });
    await click(".modal-footer .btn-primary");
    await contains(".o-mail-AttachmentCard", { count: 0 });
});

test("prevent attachment delete on non-authored message in channels", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            Command.create({
                mimetype: "image/jpeg",
                name: "BLAH",
                res_id: channelId,
                res_model: "discuss.channel",
            }),
        ],
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentImage");
    await contains(".o-mail-AttachmentImage div[title='Remove']", { count: 0 });
});

test("Toggle star should update starred counter on all tabs", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(undefined, { target: env2 });
    await click(".o-mail-Message [title='Mark as Todo']", { target: env1 });
    await contains("button", {
        target: env2,
        text: "Starred",
        contains: [".badge", { text: "1" }],
    });
});

test("allow attachment image download on message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "Blah.jpg",
        mimetype: "image/jpeg",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-AttachmentImage [title='Actions']");
    await contains(".dropdown-item", { text: "Download" });
});

test("Can download all files of a message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const [attachmentId_1, attachmentId_2, attachmentId_3] = pyEnv["ir.attachment"].create([
        { name: "test.png", mimetype: "image/png" },
        { name: "Blah.png", mimetype: "image/png" },
        { name: "shut.png", mimetype: "image/png" },
    ]);
    pyEnv["mail.message"].create([
        {
            attachment_ids: [attachmentId_1, attachmentId_2],
            body: "<p>Test</p>",
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        },
        {
            attachment_ids: [attachmentId_3],
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await contains("[title='Download Files']");
    await click(":nth-child(2 of .o-mail-Message) [title='Expand']");
    await contains("[title='Download Files']", { count: 0 });
});

test("Can remove files of message individually", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const [attachmentId_1, attachmentId_2, attachmentId_3, attachmentId_4] = pyEnv[
        "ir.attachment"
    ].create([
        { name: "attachment1.txt", mimetype: "text/plain" },
        { name: "attachment2.txt", mimetype: "text/plain" },
        { name: "attachment3.txt", mimetype: "text/plain" },
        { name: "attachment4.txt", mimetype: "text/plain" },
    ]);
    pyEnv["mail.message"].create([
        {
            attachment_ids: [attachmentId_1, attachmentId_2],
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        },
        {
            attachment_ids: [attachmentId_3],
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        },
        {
            attachment_ids: [attachmentId_4],
            body: "<p>Test</p>",
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(
        ":nth-child(1 of .o-mail-Message) :nth-child(1 of .o-mail-AttachmentCard) [title='Remove']"
    );
    await contains(
        ":nth-child(1 of .o-mail-Message) :nth-child(2 of .o-mail-AttachmentCard) [title='Remove']"
    );
    await contains(":nth-child(2 of .o-mail-Message) .o-mail-AttachmentCard [title='Remove']", {
        count: 0,
    });
    await contains(":nth-child(3 of .o-mail-Message) .o-mail-AttachmentCard [title='Remove']");
});

test("avatar card from author should be opened after clicking on their avatar", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Partner_1" },
        { name: "Partner_2", email: "partner2@mail.com", phone: "+15968415" },
    ]);
    pyEnv["res.users"].create({
        partner_id: partnerId_2,
        name: "Partner_2",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId_2,
        body: "not empty",
        model: "res.partner",
        res_id: partnerId_1,
    });
    await start();
    await openFormView("res.partner", partnerId_1);
    await contains(".o-mail-Message-avatar");
    expect(".o-mail-Message-avatarContainer:first").toHaveClass("cursor-pointer");
    await click(".o-mail-Message-avatar");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Partner_2" });
    await contains(".o_card_user_infos > a", { text: "partner2@mail.com" });
    await contains(".o_card_user_infos > a", { text: "+15968415" });
});

test("avatar card from author should be opened after clicking on their name", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        email: "demo@example.com",
        phone: "+5646548",
    });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-author", { text: "Demo" });
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Demo" });
    await contains(".o_card_user_infos > a", { text: "demo@example.com" });
    await contains(".o_card_user_infos > a", { text: "+5646548" });
});

test("subtype description should be displayed if it is different than body", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    const subtypeId = pyEnv["mail.message.subtype"].create({ description: "Bonjour" });
    pyEnv["mail.message"].create({
        body: "<p>Hello</p>",
        model: "res.partner",
        res_id: threadId,
        subtype_id: subtypeId,
    });
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Message-body", { text: "HelloBonjour" });
});

test("subtype description should not be displayed if it is similar to body", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    const subtypeId = pyEnv["mail.message.subtype"].create({ description: "hello" });
    pyEnv["mail.message"].create({
        body: "<p>Hello</p>",
        model: "res.partner",
        res_id: threadId,
        subtype_id: subtypeId,
    });
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Message-body", { text: "Hello" });
});

test("data-oe-id & data-oe-model link redirection on click", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        body: '<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>',
        model: "res.partner",
        res_id: partnerId,
    });
    mockService("action", {
        doAction(action) {
            if (action?.res_model === "res.partner") {
                return super.doAction(...arguments);
            }
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.res_model).toBe("some.model");
            expect(action.res_id).toBe(250);
            step("do-action:openFormView_some.model_250");
        },
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-body a");
    await assertSteps(["do-action:openFormView_some.model_250"]);
});

test("Chat with partner should be opened after clicking on their mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Test Partner",
        email: "testpartner@odoo.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@Te");
    await click(".o-mail-Composer-suggestion strong", { text: "Test Partner" });
    await contains(".o-mail-Composer-input", { value: "@Test Partner " });
    await click(".o-mail-Composer-send:enabled");
    await click(".o_mail_redirect");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    await contains(".o-mail-ChatWindow", { text: "Test Partner" });
});

test("Channel should be opened after clicking on its mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["discuss.channel"].create({ name: "my-channel" });
    await start();
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion strong", { text: "my-channel" });
    await click(".o-mail-Composer-send:enabled");
    await click(".o_channel_redirect");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    await contains(".o-mail-ChatWindow", { text: "my-channel" });
});

test("delete all attachments of message without content should no longer display the message", async () => {
    const pyEnv = await startServer();
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Delete']");
    await click("button", { text: "Confirm" });
    await contains(".o-mail-Message", { count: 0 });
});

test("delete all attachments of a message with some text content should still keep it displayed", async () => {
    const pyEnv = await startServer();
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "Some content",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
    await click(".o-mail-AttachmentCard button[title='Remove']");
    await click(".modal button", { text: "Ok" });
    await contains(".o-mail-Message");
});

test("message with subtype should be displayed (and not considered as empty)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const subtypeId = pyEnv["mail.message.subtype"].create({ description: "Task created" });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        subtype_id: subtypeId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-content", { text: "Task created" });
});

test("message considered empty", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create([
        {
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "<p></p>",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "<p><br/></p>",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "<p><br></p>",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "<p>\n</p>",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "<p>\r\n\r\n</p>",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: "<p>   </p>  ",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            body: '<span class="o-mail-Message-edited"></span>',
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "The conversation is empty." });
    await contains(".o-mail-Message", { count: 0 });
});

test("message with html not to be considered empty", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "<img src=''>",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
});

test("message with body 'test' should not be considered empty", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "test",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message");
});

test("Can reply to chatter messages from history", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "Hello World!",
        message_type: "comment",
        model: "res.partner",
        res_id: serverState.partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        is_read: true,
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_history");
    await contains(".o-mail-Message [title='Reply']");
    await click(".o-mail-Message [title='Reply']");
    await contains("button[title='Full composer']");
});

test("Can't reply to user notifications", async () => {
    // User notifications are specific to a user
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "Dear Mitchell Admin, you have received a new rank",
        message_type: "user_notification",
        model: "res.partner",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        is_read: true,
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss("mail.box_history");
    await contains(".o-mail-Message-actions");
    await contains(".o-mail-Message-actions [title='Reply']", { count: 0 });
});

test("Mark as unread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        name: "General",
    });
    const messageId = pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        body: "Hello World!",
    });
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], {
        seen_message_id: messageId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Mark as Unread']");
    await contains(".o-mail-Thread-newMessage");
    await contains(".o-mail-DiscussSidebarChannel .badge", { text: "1" });
});

test("Avatar of unknown author for email message", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create({
        body: "<p>Want to know features and benefits of using the new software.</p>",
        email_from: "md@oilcompany.fr",
        message_type: "email",
        subject: "Need Details",
        model: "res.partner",
        res_id: serverState.partnerId,
        author_id: null,
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-Message-avatar[data-src*='mail/static/src/img/email_icon.png']");
});

test("Show email_from of message without author for email message", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create({
        author_id: null,
        body: "<p>Want to know features and benefits of using the new software.</p>",
        email_from: "md@oilcompany.fr",
        message_type: "email",
        subject: "Need Details",
        model: "res.partner",
        res_id: serverState.partnerId,
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-Message-author", { text: "md@oilcompany.fr" });
});

test("Avatar of unknown author for not email message", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create({
        body: "<p>Want to know features and benefits of using the new software.</p>",
        email_from: "md@oilcompany.fr",
        message_type: "comment",
        subject: "Need Details",
        model: "res.partner",
        res_id: serverState.partnerId,
        author_id: null,
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-Message-avatar[data-src*='/mail/static/src/img/smiley/avatar.jpg']");
});

test("Show email_from of message without author for not email message", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create({
        author_id: null,
        body: "<p>Want to know features and benefits of using the new software.</p>",
        email_from: "md@oilcompany.fr",
        message_type: "comment",
        subject: "Need Details",
        model: "res.partner",
        res_id: serverState.partnerId,
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-Message-author", { text: "md@oilcompany.fr" });
});

test("Message should display attachments in order", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
        attachment_ids: [
            pyEnv["ir.attachment"].create({ name: "A.txt", mimetype: "text/plain" }),
            pyEnv["ir.attachment"].create({ name: "B.txt", mimetype: "text/plain" }),
            pyEnv["ir.attachment"].create({ name: "C.txt", mimetype: "text/plain" }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(":nth-child(1 of .o-mail-AttachmentCard)", { text: "A.txt" });
    await contains(":nth-child(2 of .o-mail-AttachmentCard)", { text: "B.txt" });
    await contains(":nth-child(3 of .o-mail-AttachmentCard)", { text: "C.txt" });
});

test("Can edit a message only containing an attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "Blah.jpg",
        mimetype: "image/jpeg",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        author_id: serverState.partnerId,
        body: "",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Edit']");
    await contains(".o-mail-Message.o-editing .o-mail-Composer-input");
});

test("Click on view reactions shows the reactions on the message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅1" });
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='View Reactions']");
    await contains(".o-mail-MessageReactionMenu", { text: "😅1" });
});

test("Reactions are ordered by id", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
        reaction_ids: [
            pyEnv["mail.message.reaction"].create({
                content: "🔰",
                partner_id: serverState.partnerId,
            }),
            pyEnv["mail.message.reaction"].create({
                content: "🔢",
                partner_id: serverState.partnerId,
            }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-MessageReaction:eq(0)", { text: "🔰" });
    await contains(".o-mail-MessageReaction:eq(1)", { text: "🔢" });
});

test("discuss - bigger font size when there is only emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "🥳");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body", { text: "🥳" });
    await insertText(".o-mail-Composer-input", "not only emoji!! 😅");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body", { text: "not only emoji!! 😅" });
    const [emojiMessage, textMessage] = document.querySelectorAll(".o-mail-Message-body");
    expect(
        parseFloat(getComputedStyle(emojiMessage).getPropertyValue("font-size"))
    ).toBeGreaterThan(parseFloat(getComputedStyle(textMessage).getPropertyValue("font-size")));
});

test("chatter - font size unchanged when there is only emoji", async () => {
    await startServer();
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click(".o-mail-Chatter-sendMessage");
    await insertText(".o-mail-Composer-input", "🥳");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body", { text: "🥳" });
    await click(".o-mail-Chatter-sendMessage");
    await insertText(".o-mail-Composer-input", "not only emoji!! 😅");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body", { text: "not only emoji!! 😅" });
    const [emojiMessage, textMessage] = document.querySelectorAll(".o-mail-Message-body");
    expect(parseFloat(getComputedStyle(emojiMessage).getPropertyValue("font-size"))).toBe(
        parseFloat(getComputedStyle(textMessage).getPropertyValue("font-size"))
    );
});

test("Delete starred message decrements starred counter once", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create([
        {
            author_id: serverState.partnerId,
            body: "delete me",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            starred_partner_ids: [serverState.partnerId],
        },
        {
            author_id: serverState.partnerId,
            body: "Hello World!",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            starred_partner_ids: [serverState.partnerId],
        },
        {
            author_id: serverState.partnerId,
            body: "test",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
            starred_partner_ids: [serverState.partnerId],
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains("button", { count: 1, text: "Starred3" });
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await click(".o-mail-Message-moreMenu [title='Delete']");
    await click("button", { text: "Confirm" });
    await contains("button", { count: 1, text: "Starred2" });
});

test("Copy Message Link", async () => {
    patchWithCleanup(browser.navigator.clipboard, {
        writeText(text) {
            step(text);
            super.writeText(text);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "channel1" });
    const [, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "Message without type",
            res_id: channelId,
            model: "discuss.channel",
        },
        {
            body: "Hello world",
            res_id: channelId,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message:eq(0) [title='Expand']");
    await contains("[title='Copy Link']", { count: 0 });
    await click(".o-mail-Message:eq(1) [title='Expand']");
    await click("[title='Copy Link']");
    await assertSteps([url(`/mail/message/${messageId_2}`)]);
    await press(["ctrl", "v"]);
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { text: url(`/mail/message/${messageId_2}`) });
});
