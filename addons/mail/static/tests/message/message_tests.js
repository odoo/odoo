/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { getOrigin } from "@web/core/utils/urls";
import {
    makeDeferred,
    nextTick,
    patchDate,
    patchTimeZone,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";
import { SIZES, patchUiSize } from "../helpers/patch_ui_size";

const { DateTime } = luxon;

QUnit.module("message");

QUnit.test("Start edition on click edit", async () => {
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
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await contains(".o-mail-Message-editable .o-mail-Composer-input", { value: "Hello world" });
});

QUnit.test("Editing message keeps the mentioned channels", async () => {
    const pyEnv = await startServer();
    const channelId1 = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["discuss.channel"].create({
        name: "other",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId1);
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion strong", { text: "#other" });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o_channel_redirect", { count: 1, text: "#other" });
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await contains(".o-mail-Message-editable .o-mail-Composer-input", {
        value: "#other",
    });
    await insertText(".o-mail-Message .o-mail-Composer-input", "#other bye", { replace: true });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-content", { text: "#other bye" });
    await click(".o_channel_redirect", { text: "#other" });
    await contains(".o-mail-Discuss-threadName", { value: "other" });
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
    await click(".o-mail-Message .fa-paper-plane-o");
    await contains(".o-mail-Message-content", { text: "edited message" });
});

QUnit.test("Can edit message comment in chatter", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "original message",
        message_type: "comment",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "edited message", { replace: true });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-content", { text: "edited message" });
});

QUnit.test("Can edit message comment in chatter (mobile)", async () => {
    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "original message",
        message_type: "comment",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await contains("button", { text: "Discard editing" });
    await insertText(".o-mail-Message .o-mail-Composer-input", "edited message", { replace: true });
    await click("button[aria-label='Save editing']");
    await contains(".o-mail-Message-content", { text: "edited message" });
});

QUnit.test("Cursor is at end of composer input on edit", async (assert) => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    const textarea = $(".o-mail-Composer-input")[0];
    const contentLength = textarea.value.length;
    assert.strictEqual(textarea.selectionStart, contentLength);
    assert.strictEqual(textarea.selectionEnd, contentLength);
});

QUnit.test("Stop edition on click cancel", async () => {
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
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-Message a", { text: "cancel" });
    await contains(".o-mail-Message-editable .o-mail-Composer", { count: 0 });
});

QUnit.test("Stop edition on press escape", async () => {
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
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    triggerHotkey("Escape", false);
    await contains(".o-mail-Message-editable .o-mail-Composer", { count: 0 });
});

QUnit.test("Stop edition on click save", async () => {
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
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-editable .o-mail-Composer", { count: 0 });
});

QUnit.test("Stop edition on press enter", async () => {
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
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    triggerHotkey("Enter", false);
    await contains(".o-mail-Message-editable .o-mail-Composer", { count: 0 });
});

QUnit.test("Do not stop edition on click away when clicking on emoji", async () => {
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
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-Composer button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content :nth-child(1 of .o-Emoji)");
    await contains(".o-mail-Message-editable .o-mail-Composer");
});

QUnit.test("Edit and click save", async () => {
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
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "Goodbye World", { replace: true });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-body", { text: "Goodbye World" });
});

QUnit.test("Do not call server on save if no changes", async (assert) => {
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
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/update_content") {
                assert.step("update_content");
            }
        },
    });
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-Message a", { text: "save" });
    assert.verifySteps([]);
});

QUnit.test("Update the link previews when a message is edited", async (assert) => {
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
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/link_preview") {
                assert.step("link_preview");
            }
        },
    });
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "Goodbye World", { replace: true });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message-body", { text: "Goodbye World" });
    assert.verifySteps(["link_preview"]);
});

QUnit.test("Scroll bar to the top when edit starts", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world!".repeat(1000),
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await contains(".o-mail-Message .o-mail-Composer-input");
    const textarea = document.querySelector(".o-mail-Message .o-mail-Composer-input");
    assert.ok(textarea.scrollHeight > textarea.clientHeight);
    await contains(".o-mail-Message .o-mail-Composer-input", { scroll: 0 });
});

QUnit.test("mentions are kept when editing message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello @Mitchell Admin",
        model: "discuss.channel",
        partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", "Hi @Mitchell Admin", {
        replace: true,
    });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message", {
        text: "Hi @Mitchell Admin",
        contains: ["a.o_mail_redirect", { text: "@Mitchell Admin" }],
    });
});

QUnit.test("can add new mentions when editing message", async () => {
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
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello",
        model: "discuss.channel",
        partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await insertText(".o-mail-Message .o-mail-Composer-input", " @");
    await click(".o-mail-Composer-suggestion strong", { text: "TestPartner" });
    await contains(".o-mail-Composer-input", { value: "Hello @TestPartner " });
    await click(".o-mail-Message a", { text: "save" });
    await contains(".o-mail-Message", {
        text: "Hello @TestPartner",
        contains: ["a.o_mail_redirect", { text: "@TestPartner" }],
    });
});

QUnit.test("Other messages are grayed out when replying to another one", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create([
        { body: "Hello world", res_id: channelId, model: "discuss.channel" },
        { body: "Goodbye world", res_id: channelId, model: "discuss.channel" },
    ]);
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 2 });
    await click("[title='Reply']", {
        parent: [".o-mail-Message", { text: "Hello world" }],
    });
    await contains(".o-mail-Message.opacity-50", { text: "Goodbye world" });
    await contains(".o-mail-Message:not(.opacity_50)", { text: "Hello world" });
});

QUnit.test("Parent message body is displayed on replies", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Reply']");
    await insertText(".o-mail-Composer-input", "FooBarFoo");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-MessageInReply-message", { text: "Hello world" });
});

QUnit.test(
    "Updating the parent message of a reply also updates the visual of the reply",
    async () => {
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
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
        await click(".o-mail-Message [title='Edit']");
        await insertText(".o-mail-Message .o-mail-Composer-input", "Goodbye World", {
            replace: true,
        });
        triggerHotkey("Enter");
        await contains(".o-mail-MessageInReply-message", { text: "Goodbye World" });
    }
);

QUnit.test("Deleting parent message of a reply should adapt reply visual", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Reply']");
    await insertText(".o-mail-Composer-input", "FooBarFoo");
    triggerHotkey("Enter", false);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Delete']");
    await click("button", { text: "Confirm" });
    await contains(".o-mail-MessageInReply", { text: "Original message was deleted" });
});

QUnit.test("Can open emoji picker after edit mode", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-DiscussSidebar");
    await click("[title='Add a Reaction']");
    await contains(".o-EmojiPicker");
});

QUnit.test("Can add a reaction", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅1" });
});

QUnit.test("Can remove a reaction", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await click(".o-mail-MessageReaction");
    await contains(".o-mail-MessageReaction", { count: 0 });
});

QUnit.test("Two users reacting with the same emoji", async () => {
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
            partner_id: pyEnv.currentPartnerId,
        },
        {
            message_id: messageId,
            content: "😅",
            partner_id: partnerId,
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-MessageReaction", { text: "😅2" });
    await click(".o-mail-MessageReaction");
    await contains(".o-mail-MessageReaction", { text: "😅1" });
    await click(".o-mail-MessageReaction");
    await contains(".o-mail-MessageReaction", { text: "😅2" });
});

QUnit.test("Reaction summary", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    const partnerNames = ["Foo", "Bar", "FooBar", "Bob"];
    const expectedSummaries = [
        "Foo has reacted with 😅",
        "Foo and Bar have reacted with 😅",
        "Foo, Bar, FooBar have reacted with 😅",
        "Foo, Bar, FooBar and 1 other person have reacted with 😅",
    ];
    for (const [idx, name] of partnerNames.entries()) {
        const userId = pyEnv["res.users"].create({ name });
        pyEnv["res.partner"].create({ name, user_ids: [Command.link(userId)] });
        await pyEnv.withUser(userId, async () => {
            await click("[title='Add a Reaction']");
            await click(".o-Emoji", {
                after: ["span", { textContent: "Smileys & Emotion" }],
                text: "😅",
            });
            await contains(`.o-mail-MessageReaction[title="${expectedSummaries[idx]}"]`);
        });
    }
});

QUnit.test("Add the same reaction twice from the emoji picker", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅1" });
});

QUnit.test("basic rendering of message", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message .o-mail-Message-content", { text: "body" });
    await contains(
        `.o-mail-Message .o-mail-Message-sidebar .o-mail-Message-avatarContainer img.cursor-pointer[data-src='${getOrigin()}/discuss/channel/${channelId}/partner/${partnerId}/avatar_128']`
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

QUnit.test("should not be able to reply to temporary/transient messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    // these user interactions is to forge a transient message response from channel command "/who"
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message [title='Reply']", { count: 0 });
});

QUnit.test("squashed transient message should not have date in the sidebar", async () => {
    patchDate(2024, 2, 26, 10, 0, 0);
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
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message.o-squashed");
    await contains(".o-mail-Message.o-squashed .o-mail-Message-sidebar", {
        text: "10:00",
    });
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { text: "You are alone in this channel." });
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send:enabled");
    await click(":nth-child(2 of .o-mail-Message.o-squashed");
    await nextTick();
    await contains(":nth-child(2 of .o-mail-Message.o-squashed) .o-mail-Message-sidebar", {
        text: "10:00",
        count: 0,
    });
});

QUnit.test("message comment of same author within 1min. should be squashed", async () => {
    // messages are squashed when "close", e.g. less than 1 minute has elapsed
    // from messages of same author and same thread. Note that this should
    // be working in non-mailboxes
    patchTimeZone(0); // so it matches server timezone
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
            date: "2019-04-20 10:00:30",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    const { openDiscuss } = await start();
    openDiscuss(channelId);
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
            [".o-mail-Message-sidebar .o-mail-Message-date", { text: "10:00" }],
        ],
    });
});

QUnit.test("open author avatar card", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
        email: "demo@example.com",
        phone: "+5646548",
    });
    const [channelId_1] = pyEnv["discuss.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
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
    const { openDiscuss } = await start();
    openDiscuss(channelId_1);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "General" });
    await contains(".o-mail-Discuss-content .o-mail-Message-avatarContainer img");

    await click(".o-mail-Discuss-content .o-mail-Message-avatarContainer img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Demo" });
    await contains(".o_card_user_infos > a", { text: "demo@example.com" });
    await contains(".o_card_user_infos > a", { text: "+5646548" });
});

QUnit.test("toggle_star message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (args.method === "toggle_message_starred") {
                assert.step("rpc:toggle_message_starred");
                assert.strictEqual(args.args[0][0], messageId);
            }
        },
    });
    openDiscuss(channelId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message [title='Mark as Todo']");
    await contains(".o-mail-Message [title='Mark as Todo'] i.fa-star-o");
    await contains("button", { text: "Starred", contains: [".badge", { count: 0 }] });
    await click("[title='Mark as Todo']");
    await contains("button", { text: "Starred", contains: [".badge", { text: "1" }] });
    assert.verifySteps(["rpc:toggle_message_starred"]);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message [title='Mark as Todo'] i.fa-star");
    await click("[title='Mark as Todo']");
    await contains("button", { text: "Starred", contains: [".badge", { count: 0 }] });
    assert.verifySteps(["rpc:toggle_message_starred"]);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message [title='Mark as Todo'] i.fa-star-o");
});

QUnit.test(
    "Name of message author is only displayed in chat window for partners others than the current user",
    async () => {
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
    }
);

QUnit.test(
    "Name of message author is not displayed in chat window for channel of type chat",
    async () => {
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
    }
);

QUnit.test("click on message edit button should open edit composer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await contains(".o-mail-Message .o-mail-Composer");
});

QUnit.test("Notification Sent", async (assert) => {
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
    const { openView } = await start();
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-notification");
    await contains(".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-envelope-o");

    await click(".o-mail-Message-notification");
    await contains(".o-mail-MessageNotificationPopover");
    await contains(".o-mail-MessageNotificationPopover i");
    assert.hasClass($(".o-mail-MessageNotificationPopover i"), "fa-check");
    await contains(".o-mail-MessageNotificationPopover", { text: "Someone" });
});

QUnit.test("Notification Error", async (assert) => {
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
    const openResendActionDef = makeDeferred();
    const { env, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "mail.mail_resend_message_action");
            assert.strictEqual(options.additionalContext.mail_message_to_resend, messageId);
            openResendActionDef.resolve();
        },
    });
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-notification");
    await contains(".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-envelope");
    click(".o-mail-Message-notification").then(() => {});
    await openResendActionDef;
    assert.verifySteps(["do_action"]);
});

QUnit.test(
    'Quick edit (edit from Composer with ArrowUp) ignores empty ("deleted") messages.',
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            name: "general",
            channel_type: "channel",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "", // empty body
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Message");
        triggerHotkey("ArrowUp");
        await contains(".o-mail-Message .o-mail-Message-editable");
        await contains(".o-mail-Message .o-mail-Composer-input", { value: "not empty" });
    }
);

QUnit.test("Editing a message to clear its composer opens message delete dialog.", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await insertText(".o-mail-Message-editable .o-mail-Composer-input", "", { replace: true });
    triggerHotkey("Enter");
    await contains(".modal-body p", { text: "Are you sure you want to delete this message?" });
});

QUnit.test(
    "Clear message body should not open message delete dialog if it has attachments",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            name: "general",
            channel_type: "channel",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
            attachment_ids: [
                pyEnv["ir.attachment"].create({ name: "test.txt", mimetype: "text/plain" }),
            ],
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await click(".o-mail-Message [title='Expand']");
        await click(".o-mail-Message [title='Edit']");
        await insertText(".o-mail-Message-editable .o-mail-Composer-input", "", { replace: true });
        triggerHotkey("Enter");
        await contains(".o-mail-Message-textContent", { text: "" });
        // weak test, no guarantee that we waited long enough for the potential dialog to show
        await contains(".modal-body p", {
            text: "Are you sure you want to delete this message?",
            count: 0,
        });
    }
);

QUnit.test("highlight the message mentioning the current user inside the channel", async () => {
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
        partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message-bubble.bg-warning-light");
});

QUnit.test(
    "not highlighting the message if not mentioning the current user inside the channel",
    async () => {
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
            author_id: pyEnv.currentPartnerId,
            body: "hello @testPartner",
            model: "discuss.channel",
            partner_ids: [partnerId],
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Message-bubble:not(.bg-warning-light)");
    }
);

QUnit.test("allow attachment delete on authored message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            [
                0,
                0,
                {
                    mimetype: "image/jpeg",
                    name: "BLAH",
                    res_id: channelId,
                    res_model: "discuss.channel",
                },
            ],
        ],
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-AttachmentImage div[title='Remove']");
    await contains(".modal-dialog .modal-body", { text: 'Do you really want to delete "BLAH"?' });
    await click(".modal-footer .btn-primary");
    await contains(".o-mail-AttachmentCard", { count: 0 });
});

QUnit.test("Toggle star should update starred counter on all tabs", async () => {
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
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss();
    await click(".o-mail-Message [title='Mark as Todo']", { target: tab1.target });
    await contains("button", {
        target: tab2.target,
        text: "Starred",
        contains: [".badge", { text: "1" }],
    });
});

QUnit.test("allow attachment image download on message", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-AttachmentImage .fa-download");
});

QUnit.test("Can download all files of a message", async () => {
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
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await contains("[title='Download Files']");
    await click(":nth-child(2 of .o-mail-Message) [title='Expand']");
    await contains("[title='Download Files']", { count: 0 });
});

QUnit.test("Can remove files of message individually", async () => {
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
    const { openDiscuss } = await start();
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

QUnit.test(
    "avatar card from author should be opened after clicking on their avatar",
    async (assert) => {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
            { name: "Partner_1" },
            { name: "Partner_2" },
        ]);
        pyEnv["res.users"].create({
            partner_id: partnerId_2,
            name: "Partner_2",
            email: "partner2@mail.com",
            phone: "+15968415",
        });
        pyEnv["mail.message"].create({
            author_id: partnerId_2,
            body: "not empty",
            model: "res.partner",
            res_id: partnerId_1,
        });
        const { openFormView } = await start();
        await openFormView("res.partner", partnerId_1);
        await contains(".o-mail-Message-avatar");
        assert.hasClass($(".o-mail-Message-avatarContainer"), "cursor-pointer");
        await click(".o-mail-Message-avatar");
        await contains(".o_avatar_card");
        await contains(".o_card_user_infos > span", { text: "Partner_2" });
        await contains(".o_card_user_infos > a", { text: "partner2@mail.com" });
        await contains(".o_card_user_infos > a", { text: "+15968415" });
    }
);

QUnit.test("avatar card from author should be opened after clicking on their name", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
        email: "demo@example.com",
        phone: "+5646548",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-author", { text: "Demo" });
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Demo" });
    await contains(".o_card_user_infos > a", { text: "demo@example.com" });
    await contains(".o_card_user_infos > a", { text: "+5646548" });
});

QUnit.test("subtype description should be displayed if it is different than body", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    const subtypeId = pyEnv["mail.message.subtype"].create({ description: "Bonjour" });
    pyEnv["mail.message"].create({
        body: "<p>Hello</p>",
        model: "res.partner",
        res_id: threadId,
        subtype_id: subtypeId,
    });
    const { openFormView } = await start();
    openFormView("res.partner", threadId);
    await contains(".o-mail-Message-body", { text: "HelloBonjour" });
});

QUnit.test("subtype description should not be displayed if it is similar to body", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    const subtypeId = pyEnv["mail.message.subtype"].create({ description: "hello" });
    pyEnv["mail.message"].create({
        body: "<p>Hello</p>",
        model: "res.partner",
        res_id: threadId,
        subtype_id: subtypeId,
    });
    const { openFormView } = await start();
    openFormView("res.partner", threadId);
    await contains(".o-mail-Message-body", { text: "Hello" });
});

QUnit.test("data-oe-id & data-oe-model link redirection on click", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        body: '<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>',
        model: "res.partner",
        res_id: partnerId,
    });
    const { env, openFormView } = await start();
    openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.res_model, "some.model");
            assert.strictEqual(action.res_id, 250);
            assert.step("do-action:openFormView_some.model_250");
        },
    });
    await click(".o-mail-Message-body a");
    assert.verifySteps(["do-action:openFormView_some.model_250"]);
});

QUnit.test("Chat with partner should be opened after clicking on their mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Test Partner",
        email: "testpartner@odoo.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@Te");
    await click(".o-mail-Composer-suggestion strong", { text: "Test Partner" });
    await contains(".o-mail-Composer-input", { value: "@Test Partner " });
    await click(".o-mail-Composer-send:enabled");
    await click(".o_mail_redirect");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    await contains(".o-mail-ChatWindow", { text: "Test Partner" });
});

QUnit.test("Channel should be opened after clicking on its mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["discuss.channel"].create({ name: "my-channel" });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion strong", { text: "#my-channel" });
    await click(".o-mail-Composer-send:enabled");
    await click(".o_channel_redirect");
    await contains(".o-mail-ChatWindow .o-mail-Thread");
    await contains(".o-mail-ChatWindow", { text: "my-channel" });
});

QUnit.test(
    "delete all attachments of message without content should no longer display the message",
    async () => {
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
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Message");

        await click("[title='Expand']");
        await click("[title='Delete']");
        await click("button", { text: "Confirm" });
        await contains(".o-mail-Message", { count: 0 });
    }
);

QUnit.test(
    "delete all attachments of a message with some text content should still keep it displayed",
    async () => {
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
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Message");

        await click(".o-mail-AttachmentCard button[title='Remove']");
        await click(".modal button", { text: "Ok" });
        await contains(".o-mail-Message");
    }
);

QUnit.test("message with subtype should be displayed (and not considered as empty)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const subtypeId = pyEnv["mail.message.subtype"].create({ description: "Task created" });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        subtype_id: subtypeId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message-content", { text: "Task created" });
});

QUnit.test("message considered empty", async () => {
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
    ]);
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Thread", { text: "There are no messages in this conversation." });
    await contains(".o-mail-Message", { count: 0 });
});

QUnit.test("message with html not to be considered empty", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "<img src=''>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message");
});

QUnit.test("message with body 'test' should not be considered empty", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "test",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message");
});

QUnit.test("Can reply to chatter messages from history", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "Hello World!",
        message_type: "comment",
        model: "res.partner",
        res_id: pyEnv.currentPartnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        is_read: true,
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss("mail.box_history");
    await contains(".o-mail-Message [title='Reply']");
    await click("[title='Reply']");
    await contains("button[title='Full composer']");
});

QUnit.test("Mark as unread", async () => {
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
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], {
        seen_message_id: messageId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Expand']");
    await click("[title='Mark as Unread']");
    await contains(".o-mail-Thread-newMessage");
    await contains(".o-mail-DiscussSidebarChannel .badge", { text: "1" });
});

QUnit.test("Avatar of unknown author", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create({
        body: "<p>Want to know features and benefits of using the new software.</p>",
        email_from: "md@oilcompany.fr",
        message_type: "email",
        subject: "Need Details",
        model: "res.partner",
        res_id: pyEnv.currentPartnerId,
        author_id: null,
    });
    const { openFormView } = await start();
    openFormView("res.partner", pyEnv.currentPartnerId);
    await contains(".o-mail-Message-avatar[data-src*='mail/static/src/img/email_icon.png']");
});

QUnit.test("Show email_from of message without author", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create({
        author_id: null,
        body: "<p>Want to know features and benefits of using the new software.</p>",
        email_from: "md@oilcompany.fr",
        message_type: "email",
        subject: "Need Details",
        model: "res.partner",
        res_id: pyEnv.currentPartnerId,
    });
    const { openFormView } = await start();
    openFormView("res.partner", pyEnv.currentPartnerId);
    await contains(".o-mail-Message-author", { text: "md@oilcompany.fr" });
});

QUnit.test("Message should display attachments in order", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(":nth-child(1 of .o-mail-AttachmentCard)", { text: "A.txt" });
    await contains(":nth-child(2 of .o-mail-AttachmentCard)", { text: "B.txt" });
    await contains(":nth-child(3 of .o-mail-AttachmentCard)", { text: "C.txt" });
});

QUnit.test("Can edit a message only containing an attachment", async () => {
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
        author_id: pyEnv.currentPartnerId,
        body: "",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await contains(".o-mail-Message-editable .o-mail-Composer-input");
});

QUnit.test("Click on view reactions shows the reactions on the message", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-MessageReaction", { text: "😅1" });
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='View Reactions']");
    await contains(".o-mail-MessageReactionMenu", { text: "😅1" });
});
