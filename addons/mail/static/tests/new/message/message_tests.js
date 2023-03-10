/** @odoo-module **/

import {
    startServer,
    start,
    click,
    insertText,
    afterNextRender,
    nextAnimationFrame,
} from "@mail/../tests/helpers/test_utils";
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

QUnit.module("message");

QUnit.test("Start edition on click edit", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    assert.containsOnce($, ".o-Message-editable .o-Composer");
    assert.strictEqual($(".o-Message-editable .o-Composer-input").val(), "Hello world");
});

QUnit.test("Cursor is at end of composer input on edit", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "",
    });
    pyEnv["mail.message"].create({
        body: "sattva",
        res_id: channelId,
        model: "mail.channel",
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("i[aria-label='Edit']");
    const textarea = $(".o-Composer-input")[0];
    const contentLength = textarea.value.length;
    assert.strictEqual(textarea.selectionStart, contentLength);
    assert.strictEqual(textarea.selectionEnd, contentLength);
});

QUnit.test("Stop edition on click cancel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    await click(".o-Message a:contains('cancel')");
    assert.containsNone($, ".o-Message-editable .o-Composer");
});

QUnit.test("Stop edition on press escape", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    await afterNextRender(() => triggerHotkey("Escape", false));
    assert.containsNone($, ".o-Message-editable .o-Composer");
});

QUnit.test("Stop edition on click save", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    await click(".o-Message a:contains('save')");
    assert.containsNone($, ".o-Message-editable .o-Composer");
});

QUnit.test("Stop edition on press enter", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    await afterNextRender(() => triggerHotkey("Enter", false));
    assert.containsNone($, ".o-Message-editable .o-Composer");
});

QUnit.test("Stop edition on click away", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    await afterNextRender(() => triggerEvent(document.body, ".o-DiscussSidebar", "click"));
    assert.containsNone($, ".o-Message-editable .o-Composer");
});

QUnit.test("Do not stop edition on click away when clicking on emoji", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    await click(".o-Composer button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji");
    assert.containsOnce($, ".o-Message-editable .o-Composer");
});

QUnit.test("Edit and click save", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    await editInput(document.body, ".o-Message .o-Composer-input", "Goodbye World");
    await click(".o-Message a:contains('save')");
    assert.strictEqual($(".o-Message-body")[0].innerText, "Goodbye World");
});

QUnit.test("Do not call server on save if no changes", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
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
    await click(".o-Message-actions i[aria-label='Edit']");
    await click(".o-Message a:contains('save')");
    assert.verifySteps([]);
});

QUnit.test("Scroll bar to the top when edit starts", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world!".repeat(1000),
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    const $textarea = $(".o-Composer-input");
    assert.ok($textarea[0].scrollHeight > $textarea[0].clientHeight);
    assert.strictEqual($textarea[0].scrollTop, 0);
});

QUnit.test("Other messages are grayed out when replying to another one", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create([
        { body: "Hello world", res_id: channelId, model: "mail.channel" },
        { body: "Goodbye world", res_id: channelId, model: "mail.channel" },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, ".o-Message", 2);
    await click(".o-Message:contains(Hello world) i[aria-label='Reply']");
    assert.doesNotHaveClass($(".o-Message:contains(Hello world)"), "opacity-50");
    assert.hasClass($(".o-Message:contains(Goodbye world)"), "opacity-50");
});

QUnit.test("Parent message body is displayed on replies", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        model: "mail.channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message i[aria-label='Reply']");
    await editInput(document.body, ".o-Composer-input", "FooBarFoo");
    await click(".o-Composer-send");
    assert.containsOnce($, ".o-MessageInReply-message");
    assert.ok($(".o-MessageInReply-message")[0].innerText, "Hello world");
});

QUnit.test(
    "Updating the parent message of a reply also updates the visual of the reply",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "channel1",
        });
        pyEnv["mail.message"].create({
            body: "Hello world",
            res_id: channelId,
            message_type: "comment",
            model: "mail.channel",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("i[aria-label='Reply']");
        await editInput(document.body, ".o-Composer-input", "FooBarFoo");
        await triggerHotkey("Enter", false);
        await click("i[aria-label='Edit']");
        await editInput(document.body, ".o-Message .o-Composer-input", "Goodbye World");
        await triggerHotkey("Enter", false);
        await nextTick();
        assert.strictEqual($(".o-MessageInReply-message")[0].innerText, "Goodbye World");
    }
);

QUnit.test("Deleting parent message of a reply should adapt reply visual", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "mail.channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("i[aria-label='Reply']");
    await editInput(document.body, ".o-Composer-input", "FooBarFoo");
    await triggerHotkey("Enter", false);
    await click("i[aria-label='Delete']");
    $('button:contains("Delete")').click();
    await nextTick();
    assert.containsOnce($, ".o-MessageInReply:contains(Original message was deleted)");
});

QUnit.test("Can open emoji picker after edit mode", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "mail.channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("i[aria-label='Edit']");
    await triggerEvent(document.body, ".o-DiscussSidebar", "click");
    await click("i[aria-label='Add a Reaction']");
    assert.containsOnce($, ".o-EmojiPicker");
});

QUnit.test("Can add a reaction", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "mail.channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("i[aria-label='Add a Reaction']");
    await click(".o-Emoji:contains(😅)");
    assert.containsOnce($, ".o-MessageReaction:contains('😅')");
});

QUnit.test("Can remove a reaction", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "mail.channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("i[aria-label='Add a Reaction']");
    await click(".o-Emoji:contains(😅)");
    await click(".o-MessageReaction");
    assert.containsNone($, ".o-MessageReaction:contains('😅')");
});

QUnit.test("Two users reacting with the same emoji", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "mail.channel",
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
    assert.containsOnce($, ".o-MessageReaction:contains(2)");

    await click(".o-MessageReaction");
    assert.containsOnce($, ".o-MessageReaction:contains('😅')");
    assert.containsOnce($, ".o-MessageReaction:contains(1)");
});

QUnit.test("Reaction summary", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "mail.channel",
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
        await click("i[aria-label='Add a Reaction']");
        await click(".o-Emoji:contains(😅)");
        assert.hasAttrValue($(".o-MessageReaction")[0], "title", expectedSummaries[idx]);
    }
});

QUnit.test("Add the same reaction twice from the emoji picker", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "mail.channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("i[aria-label='Add a Reaction']");
    await click(".o-Emoji:contains(😅)");
    await click("i[aria-label='Add a Reaction']");
    await click(".o-Emoji:contains(😅)");
    assert.containsOnce($, ".o-MessageReaction:contains('😅')");
});

QUnit.test("basic rendering of message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>body</p>",
        date: "2019-04-20 10:00:00",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message:contains(body)");
    const $message = $(".o-Message:contains(body)");
    assert.containsOnce($message, ".o-Message-sidebar");
    assert.containsOnce($message, ".o-Message-sidebar .o-Message-avatarContainer img");
    assert.hasAttrValue(
        $message.find(".o-Message-sidebar .o-Message-avatarContainer img"),
        "data-src",
        `/mail/channel/${channelId}/partner/${partnerId}/avatar_128`
    );
    assert.containsOnce($message, ".o-Message-header");
    assert.containsOnce($message, ".o-Message-header .o-Message-author:contains(Demo)");
    assert.containsOnce($message, ".o-Message-header .o-Message-date");
    assert.hasAttrValue(
        $message.find(".o-Message-header .o-Message-date"),
        "title",
        deserializeDateTime("2019-04-20 10:00:00").toLocaleString(DateTime.DATETIME_SHORT)
    );
    assert.containsOnce($message, ".o-Message-actions");
    assert.containsN($message, ".o-Message-actions i", 3);
    assert.containsOnce($message, "i[aria-label='Add a Reaction']");
    assert.containsOnce($message, "i[aria-label='Mark as Todo']");
    assert.containsOnce($message, "i[aria-label='Reply']");
    assert.containsOnce($message, ".o-Message-content");
    assert.strictEqual($message.find(".o-Message-content").text(), "body");
});

QUnit.test("should not be able to reply to temporary/transient messages", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    // these user interactions is to forge a transient message response from channel command "/who"
    await insertText(".o-Composer-input", "/who");
    await click(".o-Composer-send");
    assert.containsNone($, ".o-Message i[aria-label='Reply']");
});

QUnit.test("message comment of same author within 1min. should be squashed", async (assert) => {
    // messages are squashed when "close", e.g. less than 1 minute has elapsed
    // from messages of same author and same thread. Note that this should
    // be working in non-mailboxes
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["mail.message"].create([
        {
            author_id: partnerId,
            body: "<p>body1</p>",
            date: "2019-04-20 10:00:00",
            message_type: "comment",
            model: "mail.channel",
            res_id: channelId,
        },
        {
            author_id: partnerId,
            body: "<p>body2</p>",
            date: "2019-04-20 10:00:30",
            message_type: "comment",
            model: "mail.channel",
            res_id: channelId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, ".o-Message", 2);
    assert.containsOnce($, ".o-Message:contains(body1)");
    assert.containsOnce($, ".o-Message:contains(body2)");
    const $message1 = $(".o-Message:contains(body1)");
    const $message2 = $(".o-Message:contains(body2)");
    assert.containsOnce($message1, ".o-Message-header");
    assert.containsNone($message2, ".o-Message-header");
    assert.containsNone($message1, ".o-Message-sidebar .o-Message-date");
    assert.containsNone($message2, ".o-Message-sidebar .o-Message-date");
    await click($message2);
    assert.containsOnce($message2, ".o-Message-sidebar .o-Message-date");
});

QUnit.test("redirect to author (open chat)", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const [channelId_1] = pyEnv["mail.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        },
    ]);
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "mail.channel",
        res_id: channelId_1,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId_1);
    assert.containsOnce($, ".o-DiscussCategoryItem.o-active:contains(General)");
    assert.containsOnce($, ".o-Discuss-content .o-Message-avatarContainer img");

    await click(".o-Discuss-content .o-Message-avatarContainer img");
    assert.containsOnce($, ".o-DiscussCategoryItem.o-active:contains(Demo)");
});

QUnit.test("toggle_star message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
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
    assert.containsOnce($, ".o-Message");
    let $message = $(".o-Message");
    assert.containsOnce($message, "i[aria-label='Mark as Todo']");
    assert.hasClass($message.find("i[aria-label='Mark as Todo']"), "fa-star-o");

    await click("i[aria-label='Mark as Todo']");
    assert.verifySteps(["rpc:toggle_message_starred"]);
    assert.strictEqual($("button:contains(Starred) .badge").text(), "1");
    assert.containsOnce($, ".o-Message");
    $message = $(".o-Message");
    assert.hasClass($message.find("i[aria-label='Mark as Todo']"), "fa-star");

    await click("i[aria-label='Mark as Todo']");
    assert.verifySteps(["rpc:toggle_message_starred"]);
    assert.containsNone($, "button:contains(Starred) .badge");
    assert.containsOnce($, ".o-Message");
    $message = $(".o-Message");
    assert.hasClass($message.find("i[aria-label='Mark as Todo']"), "fa-star-o");
});

QUnit.test(
    "Name of message author is only displayed in chat window for partners others than the current user",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ channel_type: "channel" });
        const partnerId = pyEnv["res.partner"].create({ name: "Not the current user" });
        pyEnv["mail.message"].create([
            {
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
            {
                author_id: partnerId,
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
        ]);
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-NotificationItem");
        assert.containsOnce($, ".o-Message-author");
        assert.equal($(".o-Message-author").text(), "Not the current user");
    }
);

QUnit.test(
    "Name of message author is not displayed in chat window for channel of type chat",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ channel_type: "chat" });
        const partnerId = pyEnv["res.partner"].create({ name: "A" });
        pyEnv["mail.message"].create([
            {
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
            {
                author_id: partnerId,
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
        ]);
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-NotificationItem");
        assert.containsNone($, ".o-Message-author");
    }
);

QUnit.test("click on message edit button should open edit composer", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-Message-actions i[aria-label='Edit']");
    assert.containsOnce($, ".o-Message .o-Composer");
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
    assert.containsOnce($, ".o-Message");
    assert.containsOnce($, ".o-Message-notification");
    assert.containsOnce($, ".o-Message-notification i");
    assert.hasClass($(".o-Message-notification i"), "fa-envelope-o");

    await click(".o-Message-notification");
    assert.containsOnce($, ".o-MessageNotificationPopover");
    assert.containsOnce($, ".o-MessageNotificationPopover i");
    assert.hasClass($(".o-MessageNotificationPopover i"), "fa-check");
    assert.containsOnce($, ".o-MessageNotificationPopover:contains(Someone)");
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
    assert.containsOnce($, ".o-Message");
    assert.containsOnce($, ".o-Message-notification");
    assert.containsOnce($, ".o-Message-notification i");
    assert.hasClass($(".o-Message-notification i"), "fa-envelope");
    click(".o-Message-notification").then(() => {});
    await openResendActionDef;
    assert.verifySteps(["do_action"]);
});

QUnit.test(
    'Quick edit (edit from Composer with ArrowUp) ignores empty ("deleted") messages.',
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            name: "general",
            channel_type: "channel",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
            message_type: "comment",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "", // empty body
            model: "mail.channel",
            res_id: channelId,
            message_type: "comment",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await afterNextRender(() => triggerHotkey("ArrowUp"));
        assert.containsOnce($, ".o-Message .o-Message-editable");
        assert.strictEqual($(".o-Message .o-Composer-input").val(), "not empty");
    }
);

QUnit.test(
    "Editing a message to clear its composer opens message delete dialog.",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            name: "general",
            channel_type: "channel",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
            message_type: "comment",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click(".o-Message-actions i[aria-label='Edit']");
        await editInput(document.body, ".o-Message-editable .o-Composer-input", "");
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
        const channelId = pyEnv["mail.channel"].create({
            name: "general",
            channel_type: "channel",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
            message_type: "comment",
            attachment_ids: [
                pyEnv["ir.attachment"].create({ name: "test.txt", mimetype: "text/plain" }),
            ],
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click(".o-Message-actions i[aria-label='Edit']");
        await editInput(document.body, ".o-Message-editable .o-Composer-input", "");
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
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "hello @Admin",
            model: "mail.channel",
            partner_ids: [pyEnv.currentPartnerId],
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.hasClass($(".o-Message"), "o-highlighted-from-mention");
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
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "hello @testPartner",
            model: "mail.channel",
            partner_ids: [partnerId],
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.doesNotHaveClass($(".o-Message"), "o-highlighted-from-mention");
    }
);

QUnit.test("allow attachment delete on authored message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            [
                0,
                0,
                {
                    mimetype: "image/jpeg",
                    name: "BLAH",
                    res_id: channelId,
                    res_model: "mail.channel",
                },
            ],
        ],
        author_id: pyEnv.currentPartnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-AttachmentImage");
    assert.containsOnce($, ".o-AttachmentImage div[title='Remove']");

    await click(".o-AttachmentImage div[title='Remove']");
    assert.containsOnce($, ".modal-dialog");
    assert.strictEqual($(".modal-body").text(), 'Do you really want to delete "BLAH"?');

    await click(".modal-footer .btn-primary");
    assert.containsNone($, ".o-AttachmentCard");
});

QUnit.test("prevent attachment delete on non-authored message in channels", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            [
                0,
                0,
                {
                    mimetype: "image/jpeg",
                    name: "BLAH",
                    res_id: channelId,
                    res_model: "mail.channel",
                },
            ],
        ],
        author_id: partnerId,
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-AttachmentImage");
    assert.containsNone($, ".o-AttachmentImage div[title='Remove']");
});

QUnit.test("Toggle star should update starred counter on all tabs", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Hello world",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss();
    await tab1.click("i[aria-label='Mark as Todo']");
    assert.strictEqual($(tab2.target).find("button:contains(Starred) .badge").text(), "1");
});

QUnit.test("allow attachment image download on message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "Blah.jpg",
        mimetype: "image/jpeg",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-AttachmentImage .fa-download");
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
    assert.containsOnce($, ".o-Message-avatar");
    assert.hasClass($(".o-Message-avatar"), "o_redirect");
    await click(".o-Message-avatar");
    assert.containsOnce($, ".o-ChatWindow-content");
    assert.containsOnce($, ".o-ChatWindow-header:contains(Partner_2)");
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
    assert.containsOnce($, ".o-Message span:contains(Demo User)");

    await click(".o-Message span:contains(Demo User)");
    assert.containsOnce($, ".o-ChatWindow");
    assert.containsOnce($, ".o-ChatWindow-header:contains(Demo User)");
});

QUnit.test(
    "chat with author should be opened after clicking on their im status icon",
    async (assert) => {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
            { name: "Partner_1" },
            { name: "Partner_2", im_status: "online" },
        ]);
        pyEnv["res.users"].create({
            im_status: "online",
            partner_id: partnerId_2,
        });
        pyEnv["mail.message"].create({
            author_id: partnerId_2,
            body: "not empty",
            model: "res.partner",
            res_id: partnerId_1,
        });
        const { advanceTime, openFormView } = await start({ hasTimeControl: true });
        await openFormView("res.partner", partnerId_1);
        await afterNextRender(() => advanceTime(50 * 1000)); // next fetch of im_status
        assert.containsOnce($, ".o-ImStatus");
        assert.hasClass($(".o-ImStatus"), "cursor-pointer");

        await click(".o-ImStatus");
        assert.containsOnce($, ".o-ChatWindow");
        assert.containsOnce($, ".o-ChatWindow-header:contains(Partner_2)");
    }
);

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
        assert.strictEqual($(".o-Message-body").text(), "HelloBonjour");
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
        assert.strictEqual($(".o-Message-body").text(), "Hello");
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
    assert.containsOnce($, ".o-Message-body");
    assert.containsOnce($, ".o-Message-body a");

    click(".o-Message-body a").catch(() => {});
    assert.verifySteps(["do-action:openFormView_some.model_250"]);
});

QUnit.test("Chat with partner should be opened after clicking on their mention", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Test Partner",
        email: "testpartner@odoo.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    await insertText(".o-Composer-input", "@");
    await insertText(".o-Composer-input", "T");
    await insertText(".o-Composer-input", "e");
    await click(".o-composer-suggestion:contains(Test Partner)");
    await click(".o-Composer-send");
    await click(".o_mail_redirect");
    assert.containsOnce($, ".o-ChatWindow-content");
    assert.containsOnce($, ".o-ChatWindow-header:contains(Test Partner)");
});

QUnit.test(
    "open chat with author on avatar click should be disabled when currently chatting with the author",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "test" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["mail.channel"].create({
            name: "test",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message-avatar");
        assert.doesNotHaveClass($(".o-Message-avatar"), "o_redirect");

        click(".o-Message-avatar").catch(() => {});
        await nextAnimationFrame();
        assert.containsNone($, ".o-ChatWindow");
    }
);

QUnit.test("Channel should be opened after clicking on its mention", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.channel"].create({ name: "my-channel" });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    await insertText(".o-Composer-input", "#");
    await click(".o-composer-suggestion:contains(my-channel)");
    await click(".o-Composer-send");
    await click(".o_channel_redirect");
    assert.containsOnce($, ".o-ChatWindow-content");
    assert.containsOnce($, ".o-ChatWindow-header:contains(my-channel)");
});

QUnit.test(
    "delete all attachments of message without content should no longer display the message",
    async (assert) => {
        const pyEnv = await startServer();
        const attachmentId = pyEnv["ir.attachment"].create({
            mimetype: "text/plain",
            name: "Blah.txt",
        });
        const channelId = pyEnv["mail.channel"].create({ name: "General" });
        pyEnv["mail.message"].create({
            attachment_ids: [attachmentId],
            message_type: "comment",
            model: "mail.channel",
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message");

        await click(".o-AttachmentCard button[title='Remove']");
        await click(".modal button:contains(Ok)");
        assert.containsNone($, ".o-Message");
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
        const channelId = pyEnv["mail.channel"].create({ name: "General" });
        pyEnv["mail.message"].create({
            attachment_ids: [attachmentId],
            body: "Some content",
            message_type: "comment",
            model: "mail.channel",
            res_id: channelId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message");

        await click(".o-AttachmentCard button[title='Remove']");
        await click(".modal button:contains(Ok)");
        assert.containsOnce($, ".o-Message");
    }
);

QUnit.test(
    "message with subtype should be displayed (and not considered as empty)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "General" });
        const subtypeId = pyEnv["mail.message.subtype"].create({ description: "Task created" });
        pyEnv["mail.message"].create({
            model: "mail.channel",
            res_id: channelId,
            subtype_id: subtypeId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Message");
        assert.containsOnce($, ".o-Message:contains(Task created)");
    }
);

QUnit.test("message considered empty", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    pyEnv["mail.message"].create([
        {
            model: "mail.channel",
            res_id: channelId,
        },
        {
            body: "",
            model: "mail.channel",
            res_id: channelId,
        },
        {
            body: "<p></p>",
            model: "mail.channel",
            res_id: channelId,
        },
        {
            body: "<p><br/></p>",
            model: "mail.channel",
            res_id: channelId,
        },
        {
            body: "<p><br></p>",
            model: "mail.channel",
            res_id: channelId,
        },
        {
            body: "<p>\n</p>",
            model: "mail.channel",
            res_id: channelId,
        },
        {
            body: "<p>\r\n\r\n</p>",
            model: "mail.channel",
            res_id: channelId,
        },
        {
            body: "<p>   </p>  ",
            model: "mail.channel",
            res_id: channelId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-Message");
});

QUnit.test("message with html not to be considered empty", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "<img src=''>",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message");
});

QUnit.test("message with body 'test' should not be considered empty", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "test",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message");
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
    assert.containsOnce($, ".o-Message-actions [title='Reply']");
});
