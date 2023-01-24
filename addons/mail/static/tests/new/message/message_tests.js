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
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { makeDeferred } from "@mail/utils/deferred";

let target;

QUnit.module("message", {
    async beforeEach() {
        target = getFixture();
    },
});

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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    assert.containsOnce(target, ".o-mail-message-editable .o-mail-composer");
    assert.strictEqual(
        target.querySelector(".o-mail-message-editable .o-mail-composer-textarea").value,
        "Hello world"
    );
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
    const textarea = target.querySelector(".o-mail-composer-textarea");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    await click(".o-mail-message a:contains('cancel')");
    assert.containsNone(target, ".o-mail-message-editable .o-mail-composer");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    await afterNextRender(() => triggerHotkey("Escape", false));
    assert.containsNone(target, ".o-mail-message-editable .o-mail-composer");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    await click(".o-mail-message a:contains('save')");
    assert.containsNone(target, ".o-mail-message-editable .o-mail-composer");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    await afterNextRender(() => triggerHotkey("Enter", false));
    assert.containsNone(target, ".o-mail-message-editable .o-mail-composer");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    await afterNextRender(() => triggerEvent(target, ".o-mail-discuss-sidebar", "click"));
    assert.containsNone(target, ".o-mail-message-editable .o-mail-composer");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    await click(".o-mail-composer button[aria-label='Emojis']");
    await click(".o-mail-emoji-picker-content .o-emoji");
    assert.containsOnce(target, ".o-mail-message-editable .o-mail-composer");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    await editInput(target, ".o-mail-message textarea", "Goodbye World");
    await click(".o-mail-message a:contains('save')");
    assert.strictEqual(target.querySelector(".o-mail-message-body").innerText, "Goodbye World");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    await click(".o-mail-message a:contains('save')");
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    const $textarea = $(target).find(".o-mail-composer-textarea");
    assert.ok($textarea[0].scrollHeight > $textarea[0].clientHeight);
    assert.strictEqual($textarea[0].scrollTop, 0);
});

QUnit.test("Other messages are grayed out when replying to another one", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        { body: "Hello world", res_id: channelId, model: "mail.channel" },
        { body: "Goodbye world", res_id: channelId, model: "mail.channel" },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN(target, ".o-mail-message", 2);
    await click(`.o-mail-message[data-message-id='${messageId_1}'] i[aria-label='Reply']`);
    assert.doesNotHaveClass(
        target.querySelector(`.o-mail-message[data-message-id='${messageId_1}']`),
        "opacity-50"
    );
    assert.hasClass(
        target.querySelector(`.o-mail-message[data-message-id='${messageId_2}']`),
        "opacity-50"
    );
});

QUnit.test("Parent message body is displayed on replies", async function (assert) {
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
    await click(".o-mail-message i[aria-label='Reply']");
    await editInput(target, ".o-mail-composer textarea", "FooBarFoo");
    await click(".o-mail-composer-send-button");
    assert.containsOnce(target, ".o-mail-message-in-reply-body");
    assert.ok(target.querySelector(".o-mail-message-in-reply-body").innerText, "Hello world");
});

QUnit.test(
    "Updating the parent message of a reply also updates the visual of the reply",
    async function (assert) {
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
        await editInput(target, ".o-mail-composer textarea", "FooBarFoo");
        await triggerHotkey("Enter", false);
        await click("i[aria-label='Edit']");
        await editInput(target, ".o-mail-message textarea", "Goodbye World");
        await triggerHotkey("Enter", false);
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-mail-message-in-reply-body").innerText,
            "Goodbye World"
        );
    }
);

QUnit.test("Deleting parent message of a reply should adapt reply visual", async function (assert) {
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
    await editInput(target, ".o-mail-composer textarea", "FooBarFoo");
    await triggerHotkey("Enter", false);
    await click("i[aria-label='Delete']");
    $('button:contains("Delete")').click();
    await nextTick();
    assert.containsOnce(target, ".o-mail-message-in-reply:contains(Original message was deleted)");
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
    await triggerEvent(target, ".o-mail-discuss-sidebar", "click");
    await click("i[aria-label='Add a Reaction']");
    assert.containsOnce(target, ".o-mail-emoji-picker");
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
    await click(".o-emoji[data-codepoints='😅']");
    assert.containsOnce(target, ".o-mail-message-reaction:contains('😅')");
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
    await click(".o-emoji[data-codepoints='😅']");
    await click(".o-mail-message-reaction");
    assert.containsNone(target, ".o-mail-message-reaction:contains('😅')");
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
    assert.containsOnce(target, ".o-mail-message-reaction:contains(2)");

    await click(".o-mail-message-reaction");
    assert.containsOnce(target, ".o-mail-message-reaction:contains('😅')");
    assert.containsOnce(target, ".o-mail-message-reaction:contains(1)");
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
        await click(".o-emoji[data-codepoints='😅']");
        assert.hasAttrValue(
            target.querySelector(".o-mail-message-reaction"),
            "title",
            expectedSummaries[idx]
        );
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
    await click(".o-emoji[data-codepoints='😅']");
    await click("i[aria-label='Add a Reaction']");
    await click(".o-emoji[data-codepoints='😅']");
    assert.containsOnce(target, ".o-mail-message-reaction:contains('😅')");
});

QUnit.test("basic rendering of message", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "<p>body</p>",
        date: "2019-04-20 10:00:00",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce(target, `.o-mail-message[data-message-id=${messageId}]`);
    const $message = $(target).find(`.o-mail-message[data-message-id=${messageId}]`);
    assert.containsOnce($message, ".o-mail-message-sidebar");
    assert.containsOnce($message, ".o-mail-message-sidebar .o-mail-avatar-container img");
    assert.hasAttrValue(
        $message.find(".o-mail-message-sidebar .o-mail-avatar-container img"),
        "data-src",
        `/mail/channel/${channelId}/partner/${partnerId}/avatar_128`
    );
    assert.containsOnce($message, ".o-mail-msg-header");
    assert.containsOnce($message, ".o-mail-msg-header .o-mail-own-name:contains(Demo)");
    assert.containsOnce($message, ".o-mail-msg-header .o-mail-message-date");
    assert.hasAttrValue(
        $message.find(".o-mail-msg-header .o-mail-message-date"),
        "title",
        deserializeDateTime("2019-04-20 10:00:00").toLocaleString(DateTime.DATETIME_SHORT)
    );
    assert.containsOnce($message, ".o-mail-message-actions");
    assert.containsN($message, ".o-mail-message-actions i", 3);
    assert.containsOnce($message, "i[aria-label='Add a Reaction']");
    assert.containsOnce($message, "i[aria-label='Mark as Todo']");
    assert.containsOnce($message, "i[aria-label='Reply']");
    assert.containsOnce($message, ".o-mail-message-content");
    assert.strictEqual($message.find(".o-mail-message-content").text(), "body");
});

QUnit.test("should not be able to reply to temporary/transient messages", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    // these user interactions is to forge a transient message response from channel command "/who"
    await insertText(".o-mail-composer-textarea", "/who");
    await click(".o-mail-composer-send-button");
    assert.containsNone(target, ".o-mail-message i[aria-label='Reply']");
});

QUnit.test(
    "message comment of same author within 1min. should be squashed",
    async function (assert) {
        // messages are squashed when "close", e.g. less than 1 minute has elapsed
        // from messages of same author and same thread. Note that this should
        // be working in non-mailboxes
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "general" });
        const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
        const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
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
        assert.containsN(target, ".o-mail-message", 2);
        assert.containsOnce(target, `.o-mail-message[data-message-id=${messageId_1}]`);
        assert.containsOnce(target, `.o-mail-message[data-message-id=${messageId_2}]`);
        const $message1 = $(target).find(`.o-mail-message[data-message-id=${messageId_1}]`);
        const $message2 = $(target).find(`.o-mail-message[data-message-id=${messageId_2}]`);
        assert.containsOnce($message1, ".o-mail-msg-header");
        assert.containsNone($message2, ".o-mail-msg-header");
        assert.containsNone($message1, ".o-mail-message-sidebar .o-mail-message-date");
        assert.containsNone($message2, ".o-mail-message-sidebar .o-mail-message-date");
        await click($message2);
        assert.containsOnce($message2, ".o-mail-message-sidebar .o-mail-message-date");
    }
);

QUnit.test("redirect to author (open chat)", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-category-item.o-active:contains(General)");
    assert.containsOnce(
        target,
        ".o-mail-discuss-content .o-mail-message .o-mail-avatar-container img"
    );

    await click(".o-mail-discuss-content .o-mail-message .o-mail-avatar-container img");
    assert.containsOnce(target, ".o-mail-category-item.o-active:contains(Demo)");
});

QUnit.test("toggle_star message", async function (assert) {
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
                assert.strictEqual(args.args[0][0], messageId, "should have message Id in args");
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsNone(target, 'button[data-mailbox="starred"] .badge');
    assert.containsOnce(target, ".o-mail-message");
    let $message = $(target).find(".o-mail-message");
    assert.containsOnce($message, "i[aria-label='Mark as Todo']");
    assert.hasClass($message.find("i[aria-label='Mark as Todo']"), "fa-star-o");

    await click("i[aria-label='Mark as Todo']");
    assert.verifySteps(["rpc:toggle_message_starred"]);
    assert.strictEqual($(target).find('button[data-mailbox="starred"] .badge').text(), "1");
    assert.containsOnce(target, ".o-mail-message");
    $message = $(target).find(".o-mail-message");
    assert.hasClass($message.find("i[aria-label='Mark as Todo']"), "fa-star");

    await click("i[aria-label='Mark as Todo']");
    assert.verifySteps(["rpc:toggle_message_starred"]);
    assert.containsNone(target, 'button[data-mailbox="starred"] .badge');
    assert.containsOnce(target, ".o-mail-message");
    $message = $(target).find(".o-mail-message");
    assert.hasClass($message.find("i[aria-label='Mark as Todo']"), "fa-star-o");
});

QUnit.test(
    "Name of message author is only displayed in chat window for partners others than the current user",
    async function (assert) {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ channel_type: "channel" });
        const resPartnerId1 = pyEnv["res.partner"].create({ name: "Not the current user" });
        pyEnv["mail.message"].create([
            {
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
            {
                author_id: resPartnerId1,
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
        ]);
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-notification-item");
        assert.containsOnce(target, ".o-mail-own-name");
        assert.equal(target.querySelector(".o-mail-own-name").textContent, "Not the current user");
    }
);

QUnit.test(
    "Name of message author is not displayed in chat window for channel of type chat",
    async function (assert) {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ channel_type: "chat" });
        const resPartnerId1 = pyEnv["res.partner"].create({ name: "A" });
        pyEnv["mail.message"].create([
            {
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
            {
                author_id: resPartnerId1,
                body: "not empty",
                model: "mail.channel",
                res_id: channelId,
            },
        ]);
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        await click(".o-mail-notification-item");
        assert.containsNone(target, ".o-mail-own-name");
    }
);

QUnit.test("click on message edit button should open edit composer", async function (assert) {
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
    await click(".o-mail-message-actions i[aria-label='Edit']");
    assert.containsOnce(target, ".o-mail-message .o-mail-composer");
});

QUnit.test("Notification Sent", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass(target.querySelector(".o-mail-message-notification i"), "fa-envelope-o");

    await click(".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification-popover");
    assert.containsOnce(target, ".o-mail-message-notification-popover i");
    assert.hasClass(target.querySelector(".o-mail-message-notification-popover i"), "fa-check");
    assert.containsOnce(target, ".o-mail-message-notification-popover-partner-name");
    assert.strictEqual(
        target
            .querySelector(".o-mail-message-notification-popover-partner-name")
            .textContent.trim(),
        "Someone"
    );
});

QUnit.test("Notification Error", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass(target.querySelector(".o-mail-message-notification i"), "fa-envelope");
    click(".o-mail-message-notification").then(() => {});
    await openResendActionDef;
    assert.verifySteps(["do_action"]);
});

QUnit.test(
    'Quick edit (edit from Composer with ArrowUp) ignores empty ("deleted") messages.',
    async function (assert) {
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
        assert.containsOnce(target, ".o-mail-message .o-mail-message-editable");
        assert.strictEqual(
            $(target).find(".o-mail-message .o-mail-composer-textarea").val(),
            "not empty"
        );
    }
);

QUnit.test(
    "Editing a message to clear its composer opens message delete dialog.",
    async function (assert) {
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
        await click(".o-mail-message-actions i[aria-label='Edit']");
        await editInput(target, ".o-mail-message-editable .o-mail-composer-textarea", "");
        await afterNextRender(() => triggerHotkey("Enter"));
        assert.containsOnce(
            target,
            ".modal-body p:contains('Are you sure you want to delete this message?')"
        );
    }
);

QUnit.test(
    'message should not be considered as "clicked" after clicking on its author avatar',
    async function (assert) {
        const pyEnv = await startServer();
        const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "<p>Test</p>",
            model: "res.partner",
            res_id: threadId,
        });
        const { openView } = await start();
        await openView({
            res_id: threadId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        await click(".o-mail-message");
        assert.hasClass(target.querySelector(".o-mail-message"), "o-clicked");
        await click(".o-mail-message");
        assert.doesNotHaveClass(target.querySelector(".o-mail-message"), "o-clicked");
        document.querySelector(".o-mail-message-author-avatar").click();
        await nextTick();
        assert.doesNotHaveClass(target.querySelector(".o-mail-message"), "o-clicked");
    }
);

QUnit.test(
    "highlight the message mentioning the current user inside the channel",
    async function (assert) {
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
        assert.hasClass(target.querySelector(".o-mail-message"), "o-highlighted-from-mention");
    }
);

QUnit.test(
    'message should not be considered as "clicked" after clicking on notification failure icon',
    async function (assert) {
        const pyEnv = await startServer();
        const threadId = pyEnv["res.partner"].create({});
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            res_id: threadId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "exception",
            notification_type: "email",
        });
        const { env, openView } = await start();
        await openView({
            res_id: threadId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        patchWithCleanup(env.services.action, {
            // intercept the action: this action is not relevant in the context of this test.
            doAction() {},
        });
        await click(".o-mail-message");
        assert.hasClass(target.querySelector(".o-mail-message"), "o-clicked");
        await click(".o-mail-message");
        assert.doesNotHaveClass(target.querySelector(".o-mail-message"), "o-clicked");
        target.querySelector(".o-mail-message-notification.text-danger").click();
        await nextTick();
        assert.doesNotHaveClass(target.querySelector(".o-mail-message"), "o-clicked");
    }
);

QUnit.test(
    "not highlighting the message if not mentioning the current user inside the channel",
    async function (assert) {
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
        assert.doesNotHaveClass(
            target.querySelector(".o-mail-message"),
            "o-highlighted-from-mention"
        );
    }
);

QUnit.test("allow attachment delete on authored message", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-attachment-image");
    assert.containsOnce(target, ".o-mail-attachment-unlink");

    await click(".o-mail-attachment-unlink");
    assert.containsOnce(target, ".modal-dialog");
    assert.strictEqual(
        target.querySelector(".modal-body").textContent,
        'Do you really want to delete "BLAH"?'
    );

    await click(".modal-footer .btn-primary");
    assert.containsNone(target, ".o-mail-attachment-card");
});

QUnit.test(
    "prevent attachment delete on non-authored message in channels",
    async function (assert) {
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
        assert.containsOnce(target, ".o-mail-attachment-image");
        assert.containsNone(target, ".o-mail-attachment-unlink");
    }
);

QUnit.test("Toggle star should update starred counter on all tabs", async function (assert) {
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
    assert.strictEqual(tab2.target.querySelector(".o-starred-box .badge").textContent, "1");
});

QUnit.test("allow attachment image download on message", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-attachment-image .fa-download");
});

QUnit.test(
    "chat with author should be opened after clicking on their avatar",
    async function (assert) {
        const pyEnv = await startServer();
        const [threadId, partnerId] = pyEnv["res.partner"].create([{}, {}]);
        pyEnv["res.users"].create({ partner_id: partnerId });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "res.partner",
            res_id: threadId,
        });
        const { openFormView } = await start();
        await openFormView("res.partner", threadId);
        assert.containsOnce(document.body, ".o-mail-message-author-avatar");
        assert.hasClass(document.querySelector(".o-mail-message-author-avatar"), "o_redirect");
        await click(".o-mail-message-author-avatar");
        assert.containsOnce(target, ".o-mail-chat-window-content");
        assert.containsOnce(target, `.o-mail-thread[data-thread-id='${threadId}']`);
    }
);

QUnit.test(
    "chat with author should be opened after clicking on their name",
    async function (assert) {
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
        assert.containsOnce(target, ".o-mail-message span:contains(Demo User)");

        await click(".o-mail-message span:contains(Demo User)");
        assert.containsOnce(target, ".o-mail-chat-window");
        assert.containsOnce(target, `.o-mail-thread[data-thread-id=${partnerId}]`);
    }
);

QUnit.test(
    "chat with author should be opened after clicking on their im status icon",
    async function (assert) {
        const pyEnv = await startServer();
        const [threadId, partnerId] = pyEnv["res.partner"].create([{}, { im_status: "online" }]);
        pyEnv["res.users"].create({
            im_status: "online",
            partner_id: partnerId,
        });
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            model: "res.partner",
            res_id: threadId,
        });
        const { advanceTime, openFormView } = await start({ hasTimeControl: true });
        await openFormView("res.partner", threadId);
        await afterNextRender(() => advanceTime(50 * 1000)); // next fetch of im_status
        assert.containsOnce(target, ".o-mail-partner-im-status");
        assert.hasClass(target.querySelector(".o-mail-partner-im-status"), "cursor-pointer");

        await click(".o-mail-partner-im-status");
        assert.containsOnce(target, ".o-mail-chat-window");
        assert.containsOnce(target, `.o-mail-thread[data-thread-id=${threadId}]`);
    }
);

QUnit.test(
    "subtype description should be displayed if it is different than body",
    async function (assert) {
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
        assert.strictEqual($(target).find(".o-mail-message-body").text(), "HelloBonjour");
    }
);

QUnit.test(
    "subtype description should not be displayed if it is similar to body",
    async function (assert) {
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
        assert.strictEqual($(target).find(".o-mail-message-body").text(), "Hello");
    }
);

QUnit.test("data-oe-id & data-oe-model link redirection on click", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.message"].create({
        body: `<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>`,
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
    assert.containsOnce(target, ".o-mail-message-body");
    assert.containsOnce(target.querySelector(".o-mail-message-body"), "a");

    click(".o-mail-message-body a").catch(() => {});
    assert.verifySteps(["do-action:openFormView_some.model_250"]);
});

QUnit.test(
    "Chat with partner should be opened after clicking on their mention",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            name: "Test Partner",
            email: "testpartner@odoo.com",
        });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const { openFormView } = await start();
        await openFormView("res.partner", partnerId);
        await click("button:contains(Send message)");
        await insertText(".o-mail-composer-textarea", "@");
        await insertText(".o-mail-composer-textarea", "T");
        await insertText(".o-mail-composer-textarea", "e");
        await click(".o-composer-suggestion:contains(Test Partner)");
        await click(".o-mail-composer-send-button");
        await click(".o_mail_redirect");
        assert.containsOnce(target, ".o-mail-chat-window-content");
        assert.containsOnce(target, ".o-mail-chat-window-header:contains(Test Partner)");
    }
);

QUnit.test(
    "open chat with author on avatar click should be disabled when currently chatting with the author",
    async function (assert) {
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
        assert.containsOnce(target, ".o-mail-message-author-avatar");
        assert.doesNotHaveClass(
            target.querySelector(".o-mail-message-author-avatar"),
            "o_redirect"
        );

        click(".o-mail-message-author-avatar").catch(() => {});
        await nextAnimationFrame();
        assert.containsNone(target, ".o-mail-chat-window");
    }
);

QUnit.test("Channel should be opened after clicking on its mention", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.channel"].create({ name: "my-channel" });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    await insertText(".o-mail-composer-textarea", "#");
    await click(".o-composer-suggestion:contains(my-channel)");
    await click(".o-mail-composer-send-button");
    await click(".o_channel_redirect");
    assert.containsOnce(target, ".o-mail-chat-window-content");
    assert.containsOnce(target, ".o-mail-chat-window-header:contains(my-channel)");
});
