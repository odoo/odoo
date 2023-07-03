/** @odoo-module **/

import {
    startServer,
    start,
    click,
    insertText,
    afterNextRender,
    nextAnimationFrame,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

import { deserializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;
import {
    editInput,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { url } from "@web/core/utils/urls";
import { DEBOUNCE_FETCH_SUGGESTION_TIME } from "@mail/discuss_app/channel_selector";

QUnit.module("message");

QUnit.test("Start edition on click edit", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    assert.containsOnce($, ".o-mail-Message-editable .o-mail-Composer");
    assert.strictEqual($(".o-mail-Message-editable .o-mail-Composer-input").val(), "Hello world");
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    const textarea = $(".o-mail-Composer-input")[0];
    const contentLength = textarea.value.length;
    assert.strictEqual(textarea.selectionStart, contentLength);
    assert.strictEqual(textarea.selectionEnd, contentLength);
});

QUnit.test("Stop edition on click cancel", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-Message a:contains('cancel')");
    assert.containsNone($, ".o-mail-Message-editable .o-mail-Composer");
});

QUnit.test("Stop edition on press escape", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await afterNextRender(() => triggerHotkey("Escape", false));
    assert.containsNone($, ".o-mail-Message-editable .o-mail-Composer");
});

QUnit.test("Stop edition on click save", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-Message a:contains('save')");
    assert.containsNone($, ".o-mail-Message-editable .o-mail-Composer");
});

QUnit.test("Stop edition on press enter", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await afterNextRender(() => triggerHotkey("Enter", false));
    assert.containsNone($, ".o-mail-Message-editable .o-mail-Composer");
});

QUnit.test("Do not stop edition on click away when clicking on emoji", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-Composer button[aria-label='Emojis']");
    await click(".o-mail-EmojiPicker-content .o-mail-Emoji");
    assert.containsOnce($, ".o-mail-Message-editable .o-mail-Composer");
});

QUnit.test("Edit and click save", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await editInput(document.body, ".o-mail-Message .o-mail-Composer-input", "Goodbye World");
    await click(".o-mail-Message a:contains('save')");
    assert.strictEqual($(".o-mail-Message-body")[0].innerText, "Goodbye World");
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await click(".o-mail-Message a:contains('save')");
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await editInput(document.body, ".o-mail-Message .o-mail-Composer-input", "Goodbye World");
    await click(".o-mail-Message a:contains('save')");
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    const $textarea = $(".o-mail-Composer-input");
    assert.ok($textarea[0].scrollHeight > $textarea[0].clientHeight);
    assert.strictEqual($textarea[0].scrollTop, 0);
});

QUnit.test("mentions are kept when editing message", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await editInput(document.body, ".o-mail-Message .o-mail-Composer-input", "Hi @Mitchell Admin");
    await click(".o-mail-Message a:contains('save')");
    assert.strictEqual($(".o-mail-Message-body")[0].innerText, "Hi @Mitchell Admin");
    assert.containsOnce($, ".o-mail-Message-body a.o_mail_redirect:contains(@Mitchell Admin)");
});

QUnit.test("can add new mentions when editing message", async (assert) => {
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
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await insertText(".o-mail-Composer-input", " @");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion:contains(TestPartner)");
    await click(".o-mail-Message a:contains('save')");
    assert.strictEqual($(".o-mail-Message-body")[0].innerText, "Hello @TestPartner");
    assert.containsOnce($, ".o-mail-Message-body a.o_mail_redirect:contains(@TestPartner)");
});

QUnit.test("Other messages are grayed out when replying to another one", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsN($, ".o-mail-Message", 2);
    await click(".o-mail-Message:contains(Hello world) [title='Reply']");
    assert.doesNotHaveClass($(".o-mail-Message:contains(Hello world)"), "opacity-50");
    assert.hasClass($(".o-mail-Message:contains(Goodbye world)"), "opacity-50");
});

QUnit.test("Parent message body is displayed on replies", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Reply']");
    await editInput(document.body, ".o-mail-Composer-input", "FooBarFoo");
    await click(".o-mail-Composer-send");
    assert.containsOnce($, ".o-mail-MessageInReply-message");
    assert.ok($(".o-mail-MessageInReply-message")[0].innerText, "Hello world");
});

QUnit.test(
    "Updating the parent message of a reply also updates the visual of the reply",
    async (assert) => {
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
        await openDiscuss(channelId);
        await click("[title='Reply']");
        await editInput(document.body, ".o-mail-Composer-input", "FooBarFoo");
        await triggerHotkey("Enter", false);
        await click(".o-mail-Message [title='Expand']");
        await click(".o-mail-Message [title='Edit']");
        await editInput(document.body, ".o-mail-Message .o-mail-Composer-input", "Goodbye World");
        await triggerHotkey("Enter", false);
        await waitUntil(".o-mail-MessageInReply-message:contains(Goodbye World)");
        assert.strictEqual($(".o-mail-MessageInReply-message")[0].innerText, "Goodbye World");
    }
);

QUnit.test("Deleting parent message of a reply should adapt reply visual", async (assert) => {
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
    await openDiscuss(channelId);
    await click("[title='Reply']");
    await editInput(document.body, ".o-mail-Composer-input", "FooBarFoo");
    await triggerHotkey("Enter", false);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Delete']");
    await click("button:contains(Confirm)");
    assert.containsOnce($, ".o-mail-MessageInReply:contains(Original message was deleted)");
});

QUnit.test("Can open emoji picker after edit mode", async (assert) => {
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
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    await triggerEvent(document.body, ".o-mail-DiscussSidebar", "click");
    await click("[title='Add a Reaction']");
    assert.containsOnce($, ".o-mail-EmojiPicker");
});

QUnit.test("Can add a reaction", async (assert) => {
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
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-mail-Emoji:contains(😅)");
    assert.containsOnce($, ".o-mail-MessageReaction:contains('😅')");
});

QUnit.test("Can remove a reaction", async (assert) => {
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
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-mail-Emoji:contains(😅)");
    await click(".o-mail-MessageReaction");
    assert.containsNone($, ".o-mail-MessageReaction:contains('😅')");
});

QUnit.test("Two users reacting with the same emoji", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-MessageReaction:contains(2)");

    await click(".o-mail-MessageReaction");
    assert.containsOnce($, ".o-mail-MessageReaction:contains('😅')");
    assert.containsOnce($, ".o-mail-MessageReaction:contains(1)");
});

QUnit.test("Reaction summary", async (assert) => {
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
    await openDiscuss(channelId);
    const partnerNames = ["Foo", "Bar", "FooBar", "Bob"];
    const expectedSummaries = [
        "Foo has reacted with 😅",
        "Foo and Bar have reacted with 😅",
        "Foo, Bar, FooBar have reacted with 😅",
        "Foo, Bar, FooBar and 1 other person have reacted with 😅",
    ];
    for (const [idx, name] of partnerNames.entries()) {
        const partnerId = pyEnv["res.partner"].create({ name });
        pyEnv.currentPartnerId = partnerId;
        await click("[title='Add a Reaction']");
        await click(".o-mail-Emoji:contains(😅)");
        assert.hasAttrValue($(".o-mail-MessageReaction")[0], "title", expectedSummaries[idx]);
    }
});

QUnit.test("Add the same reaction twice from the emoji picker", async (assert) => {
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
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await click(".o-mail-Emoji:contains(😅)");
    await click("[title='Add a Reaction']");
    await click(".o-mail-Emoji:contains(😅)");
    assert.containsOnce($, ".o-mail-MessageReaction:contains('😅')");
});

QUnit.test("basic rendering of message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>body</p>",
        date: "2019-04-20 10:00:00",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Message:contains(body)");
    const $message = $(".o-mail-Message:contains(body)");
    assert.containsOnce($message, ".o-mail-Message-sidebar");
    assert.containsOnce($message, ".o-mail-Message-sidebar .o-mail-Message-avatarContainer img");
    assert.hasAttrValue(
        $message.find(".o-mail-Message-sidebar .o-mail-Message-avatarContainer img"),
        "data-src",
        url(`/discuss/channel/${channelId}/partner/${partnerId}/avatar_128`)
    );
    assert.containsOnce($message, ".o-mail-Message-header");
    assert.containsOnce($message, ".o-mail-Message-header .o-mail-Message-author:contains(Demo)");
    assert.containsOnce($message, ".o-mail-Message-header .o-mail-Message-date");
    assert.hasAttrValue(
        $message.find(".o-mail-Message-header .o-mail-Message-date"),
        "title",
        deserializeDateTime("2019-04-20 10:00:00").toLocaleString(DateTime.DATETIME_SHORT)
    );
    assert.containsOnce($message, ".o-mail-Message-content");
    assert.strictEqual($message.find(".o-mail-Message-content").text(), "body");
});

QUnit.test("should not be able to reply to temporary/transient messages", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    // these user interactions is to forge a transient message response from channel command "/who"
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer-send");
    assert.containsNone($, ".o-mail-Message [title='Reply']");
});

QUnit.test("message comment of same author within 1min. should be squashed", async (assert) => {
    // messages are squashed when "close", e.g. less than 1 minute has elapsed
    // from messages of same author and same thread. Note that this should
    // be working in non-mailboxes
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
    await openDiscuss(channelId);
    assert.containsN($, ".o-mail-Message", 2);
    assert.containsOnce($, ".o-mail-Message:contains(body1)");
    assert.containsOnce($, ".o-mail-Message:contains(body2)");
    const $message1 = $(".o-mail-Message:contains(body1)");
    const $message2 = $(".o-mail-Message:contains(body2)");
    assert.containsOnce($message1, ".o-mail-Message-header");
    assert.containsNone($message2, ".o-mail-Message-header");
    assert.containsNone($message1, ".o-mail-Message-sidebar .o-mail-Message-date");
    assert.containsNone($message2, ".o-mail-Message-sidebar .o-mail-Message-date");
    await click($message2);
    assert.containsOnce($message2, ".o-mail-Message-sidebar .o-mail-Message-date");
});

QUnit.test("redirect to author (open chat)", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
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
    await openDiscuss(channelId_1);
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active:contains(General)");
    assert.containsOnce($, ".o-mail-Discuss-content .o-mail-Message-avatarContainer img");

    await click(".o-mail-Discuss-content .o-mail-Message-avatarContainer img");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active:contains(Demo)");
});

QUnit.test("open chat from avatar should not work on self-authored messages", async (assert) => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [Command.create({ partner_id: pyEnv.currentPartnerId })],
            channel_type: "chat",
        },
    ]);
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.doesNotHaveClass($(".o-mail-Message-avatar"), "cursor-pointer");
    assert.doesNotHaveClass($(".o-mail-Message-author"), "cursor-pointer");

    // try to click on self, to test it doesn't work
    click(".o-mail-Message-avatar").catch(() => {});
    await nextAnimationFrame();
    assert.containsNone($, ".o-mail-DiscussCategoryItem.o-active:contains(Mitchell Admin)");
    assert.containsNone($, ".breadcrumb:contains(Mitchell Admin)"); // should not open form view neither
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
    await openDiscuss(channelId);
    assert.containsNone($, "button:contains(Starred) .badge");
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message [title='Mark as Todo']");
    assert.hasClass($(".o-mail-Message [title='Mark as Todo'] i"), "fa-star-o");

    await click("[title='Mark as Todo']");
    assert.verifySteps(["rpc:toggle_message_starred"]);
    assert.strictEqual($("button:contains(Starred) .badge").text(), "1");
    assert.containsOnce($, ".o-mail-Message");
    assert.hasClass($(".o-mail-Message [title='Mark as Todo'] i"), "fa-star");

    await click("[title='Mark as Todo']");
    assert.verifySteps(["rpc:toggle_message_starred"]);
    assert.containsNone($, "button:contains(Starred) .badge");
    assert.containsOnce($, ".o-mail-Message");
    assert.hasClass($(".o-mail-Message [title='Mark as Todo'] i"), "fa-star-o");
});

QUnit.test(
    "Name of message author is only displayed in chat window for partners others than the current user",
    async (assert) => {
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
        assert.containsOnce($, ".o-mail-Message-author");
        assert.equal($(".o-mail-Message-author").text(), "Not the current user");
    }
);

QUnit.test(
    "Name of message author is not displayed in chat window for channel of type chat",
    async (assert) => {
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
        assert.containsNone($, ".o-mail-Message-author");
    }
);

QUnit.test("click on message edit button should open edit composer", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await click(".o-mail-Message [title='Edit']");
    assert.containsOnce($, ".o-mail-Message .o-mail-Composer");
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
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-envelope-o");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover i");
    assert.hasClass($(".o-mail-MessageNotificationPopover i"), "fa-check");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover:contains(Someone)");
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
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
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
        await openDiscuss(channelId);
        await afterNextRender(() => triggerHotkey("ArrowUp"));
        assert.containsOnce($, ".o-mail-Message .o-mail-Message-editable");
        assert.strictEqual($(".o-mail-Message .o-mail-Composer-input").val(), "not empty");
    }
);

QUnit.test(
    "Editing a message to clear its composer opens message delete dialog.",
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
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click(".o-mail-Message [title='Expand']");
        await click(".o-mail-Message [title='Edit']");
        await editInput(document.body, ".o-mail-Message-editable .o-mail-Composer-input", "");
        await afterNextRender(() => triggerHotkey("Enter"));
        assert.containsOnce(
            $,
            ".modal-body p:contains('Are you sure you want to delete this message?')"
        );
    }
);

QUnit.test(
    "Clear message body should not open message delete dialog if it has attachments",
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
            attachment_ids: [
                pyEnv["ir.attachment"].create({ name: "test.txt", mimetype: "text/plain" }),
            ],
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click(".o-mail-Message [title='Expand']");
        await click(".o-mail-Message [title='Edit']");
        await editInput(document.body, ".o-mail-Message-editable .o-mail-Composer-input", "");
        await afterNextRender(() => triggerHotkey("Enter"));
        assert.containsNone(
            $,
            ".modal-body p:contains('Are you sure you want to delete this message?')"
        );
    }
);

QUnit.test(
    "highlight the message mentioning the current user inside the channel",
    async (assert) => {
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
        await openDiscuss(channelId);
        assert.hasClass($(".o-mail-Message-bubble"), "bg-warning-light");
    }
);

QUnit.test(
    "not highlighting the message if not mentioning the current user inside the channel",
    async (assert) => {
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
        await openDiscuss(channelId);
        assert.doesNotHaveClass($(".o-mail-Message-bubble"), "bg-warning-light");
    }
);

QUnit.test("allow attachment delete on authored message", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-AttachmentImage");
    assert.containsOnce($, ".o-mail-AttachmentImage div[title='Remove']");

    await click(".o-mail-AttachmentImage div[title='Remove']");
    assert.containsOnce($, ".modal-dialog");
    assert.strictEqual($(".modal-body").text(), 'Do you really want to delete "BLAH"?');

    await click(".modal-footer .btn-primary");
    assert.containsNone($, ".o-mail-AttachmentCard");
});

QUnit.test("prevent attachment delete on non-authored message in channels", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
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
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-AttachmentImage");
    assert.containsNone($, ".o-mail-AttachmentImage div[title='Remove']");
});

QUnit.test("Toggle star should update starred counter on all tabs", async (assert) => {
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
    await tab1.click(".o-mail-Message [title='Mark as Todo']");
    assert.strictEqual($(tab2.target).find("button:contains(Starred) .badge").text(), "1");
});

QUnit.test("allow attachment image download on message", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-AttachmentImage .fa-download");
});

QUnit.test("chat with author should be opened after clicking on their avatar", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Partner_1" },
        { name: "Partner_2" },
    ]);
    pyEnv["res.users"].create({ partner_id: partnerId_2 });
    pyEnv["mail.message"].create({
        author_id: partnerId_2,
        body: "not empty",
        model: "res.partner",
        res_id: partnerId_1,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId_1);
    assert.containsOnce($, ".o-mail-Message-avatar");
    assert.hasClass($(".o-mail-Message-avatar"), "o_redirect");
    await click(".o-mail-Message-avatar");
    assert.containsOnce($, ".o-mail-ChatWindow-content");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Partner_2)");
});

QUnit.test("chat with author should be opened after clicking on their name", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message span:contains(Demo User)");

    await click(".o-mail-Message span:contains(Demo User)");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Demo User)");
});

QUnit.test(
    "subtype description should be displayed if it is different than body",
    async (assert) => {
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
        await openFormView("res.partner", threadId);
        assert.strictEqual($(".o-mail-Message-body").text(), "HelloBonjour");
    }
);

QUnit.test(
    "subtype description should not be displayed if it is similar to body",
    async (assert) => {
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
        await openFormView("res.partner", threadId);
        assert.strictEqual($(".o-mail-Message-body").text(), "Hello");
    }
);

QUnit.test("data-oe-id & data-oe-model link redirection on click", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        body: '<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>',
        model: "res.partner",
        res_id: partnerId,
    });
    const { env, openFormView } = await start();
    await openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.res_model, "some.model");
            assert.strictEqual(action.res_id, 250);
            assert.step("do-action:openFormView_some.model_250");
        },
    });
    assert.containsOnce($, ".o-mail-Message-body");
    assert.containsOnce($, ".o-mail-Message-body a");

    click(".o-mail-Message-body a").catch(() => {});
    assert.verifySteps(["do-action:openFormView_some.model_250"]);
});

QUnit.test("Chat with partner should be opened after clicking on their mention", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Test Partner",
        email: "testpartner@odoo.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { advanceTime, openFormView } = await start({ hasTimeControl: true });
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "T");
    await insertText(".o-mail-Composer-input", "e");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion:contains(Test Partner)");
    await click(".o-mail-Composer-send");
    await click(".o_mail_redirect");
    assert.containsOnce($, ".o-mail-ChatWindow-content");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Test Partner)");
});

QUnit.test(
    "open chat with author on avatar click should be disabled when currently chatting with the author",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "test" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            name: "test",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Message-avatar");
        assert.doesNotHaveClass($(".o-mail-Message-avatar"), "o_redirect");

        click(".o-mail-Message-avatar").catch(() => {});
        await nextAnimationFrame();
        assert.containsNone($, ".o-mail-ChatWindow");
    }
);

QUnit.test("Channel should be opened after clicking on its mention", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["discuss.channel"].create({ name: "my-channel" });
    const { advanceTime, openFormView } = await start({ hasTimeControl: true });
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    await insertText(".o-mail-Composer-input", "#");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await nextTick();
    await click(".o-mail-Composer-suggestion:contains(my-channel)");
    await click(".o-mail-Composer-send");
    await click(".o_channel_redirect");
    assert.containsOnce($, ".o-mail-ChatWindow-content");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(my-channel)");
});

QUnit.test(
    "delete all attachments of message without content should no longer display the message",
    async (assert) => {
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
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Message");

        await click(".o-mail-AttachmentCard button[title='Remove']");
        await click(".modal button:contains(Ok)");
        assert.containsNone($, ".o-mail-Message");
    }
);

QUnit.test(
    "delete all attachments of a message with some text content should still keep it displayed",
    async (assert) => {
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
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Message");

        await click(".o-mail-AttachmentCard button[title='Remove']");
        await click(".modal button:contains(Ok)");
        assert.containsOnce($, ".o-mail-Message");
    }
);

QUnit.test(
    "message with subtype should be displayed (and not considered as empty)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        const subtypeId = pyEnv["mail.message.subtype"].create({ description: "Task created" });
        pyEnv["mail.message"].create({
            model: "discuss.channel",
            res_id: channelId,
            subtype_id: subtypeId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Message");
        assert.containsOnce($, ".o-mail-Message:contains(Task created)");
    }
);

QUnit.test("message considered empty", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Message");
});

QUnit.test("message with html not to be considered empty", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "<img src=''>",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Message");
});

QUnit.test("message with body 'test' should not be considered empty", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "test",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Message");
});

QUnit.test("Can reply to chatter messages from history", async (assert) => {
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
    await openDiscuss("mail.box_history");
    assert.containsOnce($, ".o-mail-Message [title='Reply']");
});

QUnit.test("Mark as unread", async (assert) => {
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
    await openDiscuss(channelId);
    await click("[title='Expand']");
    await click("[title='Mark as Unread']");
    assert.containsOnce($, ".o-mail-Thread-newMessage");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem .badge:contains(1)");
});

QUnit.test("Avatar of unknown author", async (assert) => {
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
    await openFormView("res.partner", pyEnv.currentPartnerId);
    assert.containsOnce(
        $,
        ".o-mail-Message-avatar[data-src*='mail/static/src/img/email_icon.png']"
    );
});

QUnit.test("Show email_from of message without author", async (assert) => {
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
    await openFormView("res.partner", pyEnv.currentPartnerId);
    assert.containsOnce($, ".o-mail-Message-header:contains(md@oilcompany.fr)");
});
