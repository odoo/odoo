import { describe, beforeEach, expect, test } from "@odoo/hoot";

import { Composer } from "@mail/core/common/composer";
import {
    SIZES,
    click,
    contains,
    createFile,
    defineMailModels,
    dragenterFiles,
    dropFiles,
    inputFiles,
    insertText,
    onRpcBefore,
    openDiscuss,
    openFormView,
    pasteFiles,
    patchUiSize,
    scroll,
    start,
    startServer,
    triggerHotkey,
} from "../mail_test_helpers";
import { Command, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { Deferred, tick } from "@odoo/hoot-mock";
import { withUser } from "@web/../tests/_framework/mock_server/mock_server";

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

test("composer text input: basic rendering when posting a message", async () => {
    await startServer();
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "Send message" });
    await contains("textarea.o-mail-Composer-input[placeholder='Send a message to followers…']");
});

test("composer text input: basic rendering when logging note", async () => {
    await startServer();
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "Log note" });
    await contains("textarea.o-mail-Composer-input[placeholder='Log an internal note…']");
});

test("composer text input: basic rendering when linked thread is a discuss.channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "dofus-disco" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer");
    await contains("textarea.o-mail-Composer-input");
});

test("composer text input placeholder should contain channel name when thread does not have specific correspondent", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    await start();
    await openDiscuss(channelId);
    await contains("textarea.o-mail-Composer-input[placeholder='Message #General…']");
});

test("add an emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "swamp-safari" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😤" });
    await contains(".o-mail-Composer-input", { value: "😤" });
});

test("Exiting emoji picker brings the focus back to the Composer textarea [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-mail-Composer-input:not(:focus)");
    triggerHotkey("Escape");
    await contains(".o-mail-Composer-input:focus");
});

test("add an emoji after some text", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "beyblade-room" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Blabla");
    await contains(".o-mail-Composer-input", { value: "Blabla" });
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "🤑" });
    await contains(".o-mail-Composer-input", { value: "Blabla🤑" });
});

test("add emoji replaces (keyboard) text selection [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Blabla");
    await contains(".o-mail-Composer-input", { value: "Blabla" });
    // simulate selection of all the content by keyboard
    document
        .querySelector(".o-mail-Composer-input")
        .setSelectionRange(0, document.querySelector(".o-mail-Composer-input").value.length);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "🤠" });
    await contains(".o-mail-Composer-input", { value: "🤠" });
});

test("Cursor is positioned after emoji after adding it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Blabla");
    const textarea = document.querySelector(".o-mail-Composer-input");
    textarea.setSelectionRange(2, 2);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "🤠" });
    const expectedPos = 2 + "🤠".length;
    expect(textarea.selectionStart).toBe(expectedPos);
    expect(textarea.selectionEnd).toBe(expectedPos);
});

test("selected text is not replaced after cancelling the selection", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Blabla");
    await contains(".o-mail-Composer-input", { value: "Blabla" });
    // simulate selection of all the content by keyboard
    document
        .querySelector(".o-mail-Composer-input")
        .setSelectionRange(0, document.querySelector(".o-mail-Composer-input").value.length);
    await click(".o-mail-Discuss-content");
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "🤠" });
    await contains(".o-mail-Composer-input", { value: "Blabla🤠" });
});

test("Selection is kept when changing channel and going back to original channel", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        { name: "channel1" },
        { name: "channel2" },
    ]);
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Foo");
    // simulate selection of all the content by keyboard
    const textarea = $(".o-mail-Composer-input")[0];
    textarea.setSelectionRange(0, textarea.value.length);
    await tick();
    await click(":nth-child(2 of .o-mail-DiscussSidebarChannel)");
    await click(":nth-child(1 of .o-mail-DiscussSidebarChannel)");
    expect(textarea.selectionStart).toBe(0);
    expect(textarea.selectionEnd).toBe(textarea.value.length);
});

test("click on emoji button, select emoji, then re-click on button should show emoji picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-skateboarding" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "👺" });
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker");
});

test("keep emoji picker scroll value when re-opening it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-carsurfing" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await scroll(".o-EmojiPicker-content", 150);
    await click("button[aria-label='Emojis']");
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 150 });
});

test("reset emoji picker scroll value after an emoji is picked", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-fingerskating" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await scroll(".o-EmojiPicker-content", 150);
    await click(".o-Emoji", { text: "😎" });
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
});

test("keep emoji picker scroll value independent if two or more different emoji pickers are used", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-jaywalking" });
    await start();
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "This is a message",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await openDiscuss(channelId);
    await click("[title='Add a Reaction']");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 150);
    await click("button[aria-label='Emojis']");
    await contains(".o-mail-PickerContent .o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 200);
    await click("[title='Add a Reaction']");
    await contains(".o-EmojiPicker-content", { scroll: 150 });
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 200 });
});

test("composer text input cleared on message post", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "au-secours-aidez-moi" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test message");
    await contains(".o-mail-Composer-input", { value: "test message" });
    await click(".o-mail-Composer-send:not([disabled])");
    await contains(".o-mail-Message");
    await contains(".o-mail-Composer-input", { value: "" });
});

test("send message only once when button send is clicked twice quickly", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "nether-picnic" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test message");
    await click(".o-mail-Composer-send:enabled");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
});

test('send button on discuss.channel should have "Send" as label', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "minecraft-wii-u" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-send:disabled", { text: "Send" });
});

test("Show send button in mobile", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.SM });
    pyEnv["discuss.channel"].create({ name: "minecraft-wii-u" });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Inbox" });
    await click("button", { text: "Channel" });
    await click(".o-mail-NotificationItem", { text: "minecraft-wii-u" });
    await contains(".o-mail-Composer button[aria-label='Send']");
    await contains(".o-mail-Composer button[aria-label='Send'] i.fa-paper-plane-o");
});

test("composer textarea content is retained when changing channel then going back", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        { name: "minigolf-galaxy-iv" },
        { name: "epic-shrek-lovers" },
    ]);
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "According to all known laws of aviation,");
    await click("span", { text: "epic-shrek-lovers" });
    await contains("textarea.o-mail-Composer-input[placeholder='Message #epic-shrek-lovers…']");
    await contains(".o-mail-Composer-input", { value: "" });
    await click("span", { text: "minigolf-galaxy-iv" });
    await contains("textarea.o-mail-Composer-input[placeholder='Message #minigolf-galaxy-iv…']", {
        value: "According to all known laws of aviation,",
    });
});

test("add an emoji after a partner mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "@Te");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "@TestPartner " });
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😊" });
    await contains(".o-mail-Composer-input", { value: "@TestPartner 😊" });
});

test("mention a channel after some text", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "bluhbluh ");
    await contains(".o-mail-Composer-input", { value: "bluhbluh " });
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "bluhbluh #General " });
});

test("add an emoji after a channel mention", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#General " });
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😊" });
    await contains(".o-mail-Composer-input", { value: "#General 😊" });
});

test("pending mentions are kept when toggling composer", async () => {
    await startServer();
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion strong", { text: "Mitchell Admin" });
    await contains(".o-mail-Composer-input", { value: "@Mitchell Admin " });
    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer-input", { count: 0 });
    await click("button", { text: "Send message" });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message-body a.o_mail_redirect", { text: "@Mitchell Admin" });
});

test("composer suggestion should match with input selection", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "Luigi",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestion", { text: "#Mario Party" });
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "#Mario Party " });
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { text: "Luigi" });
    $(".o-mail-Composer-input")[0].setSelectionRange(3, 3);
    await contains(".o-mail-Composer-suggestion", { text: "#Mario Party" });
    const textarea = $(".o-mail-Composer-input")[0];
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    await contains(".o-mail-Composer-suggestion", { text: "Luigi" });
});

test('do not post message on channel with "SHIFT-Enter" keyboard shortcut', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Test");
    await contains(".o-mail-Message", { count: 0 });
    triggerHotkey("shift+Enter");
    await tick(); // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", { count: 0 });
});

test('post message on channel with "Enter" keyboard shortcut', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Test");
    await contains(".o-mail-Message", { count: 0 });
    triggerHotkey("Enter");
    await contains(".o-mail-Message");
});

test.skip("leave command on channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "general" });
    await insertText(".o-mail-Composer-input", "/leave");
    await contains(".o-mail-Composer-suggestion strong", { count: 1 });
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", { value: "/leave " });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "general" });
    await contains(".o-mail-Discuss", { text: "No conversation selected." });
    await contains(".o_notification", { text: "You unsubscribed from general." });
});

test("Can handle leave notification from unknown member", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Dobby" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dobby", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const env = await start();
    await openDiscuss(channelId);
    await withUser(userId, () =>
        env.services.orm.call("discuss.channel", "action_unfollow", [channelId])
    );
    await click("button[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { text: "Mitchell Admin" });
    await contains(".o-discuss-ChannelMember", { count: 0, text: "Dobby" });
});

test("leave command on chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck Norris" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Chuck Norris" });
    await insertText(".o-mail-Composer-input", "/leave");
    await contains(".o-mail-Composer-suggestion strong", { count: 1 });
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", { value: "/leave " });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Chuck Norris" });
    await contains(".o-mail-Discuss h4.text-muted", { text: "No conversation selected." });
    await contains(".o_notification", { text: "You unpinned your conversation with Chuck Norris" });
});

test("Can post suggestions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#general");
    await contains(".o-mail-Composer-suggestion strong", { count: 1 });
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", { value: "#general " });
    triggerHotkey("Enter");
    await contains(".o-mail-Message .o_channel_redirect");
});

test("composer text input placeholder should contain correspondent name when thread has exactly one correspondent", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains("textarea.o-mail-Composer-input[placeholder='Message Marc Demo…']");
});

test("quick edit last self-message from UP arrow", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Test",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-content", { text: "Test" });
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
    triggerHotkey("ArrowUp");
    await contains(".o-mail-Message .o-mail-Composer");
    triggerHotkey("Escape");
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
    await contains(".o-mail-Composer-input:focus");
    // non-empty composer should not trigger quick edit
    await insertText(".o-mail-Composer-input", "Shrek");
    triggerHotkey("ArrowUp");
    // Navigable List relies on useEffect, which behaves with 2 animation frames
    // Wait 2 animation frames to make sure it doesn't show quick edit
    await tick();
    await tick();
    await contains(".o-mail-Message .o-mail-Composer", { count: 0 });
});

test("Select composer suggestion via Enter does not send the message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "shrek@odoo.com",
        name: "Shrek",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@Shrek");
    await contains(".o-mail-Composer-suggestion");
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", { value: "@Shrek " });
    // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", { count: 0 });
});

test("composer: drop attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-Dropzone", { count: 0 });
    await contains(".o-mail-AttachmentCard", { count: 0 });
    const files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
        await createFile({
            content: "hello, worlduh",
            contentType: "text/plain",
            name: "text2.txt",
        }),
    ];
    await dragenterFiles(".o-mail-Composer-input", files);
    await contains(".o-mail-Dropzone");
    await contains(".o-mail-AttachmentCard", { count: 0 });
    await dropFiles(".o-mail-Dropzone", files);
    await contains(".o-mail-Dropzone", { count: 0 });
    await contains(".o-mail-AttachmentCard", { count: 2 });
    const extraFiles = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text3.txt",
        }),
    ];
    await dragenterFiles(".o-mail-Composer-input", extraFiles);
    await dropFiles(".o-mail-Dropzone", extraFiles);
    await contains(".o-mail-AttachmentCard", { count: 3 });
});

test("composer: add an attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ]);
    await contains(".o-mail-AttachmentCard .fa-check");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard");
});

test("composer: add an attachment in reply to message in history", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        history_partner_ids: [serverState.partnerId],
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
        is_read: true,
    });
    await start();
    await openDiscuss("mail.box_history");
    await click("[title='Reply']");
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ]);
    await contains(".o-mail-AttachmentCard .fa-check");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard");
});

test("composer: send button is disabled if attachment upload is not finished", async () => {
    const pyEnv = await startServer();
    const attachmentUploadedDef = new Deferred();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpcBefore("/mail/attachment/upload", async () => await attachmentUploadedDef);
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ]);
    await contains(".o-mail-AttachmentCard.o-isUploading");
    await contains(".o-mail-Composer-send:disabled");
    // simulates attachment finishes uploading
    attachmentUploadedDef.resolve();
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard.o-isUploading", { count: 0 });
    await contains(".o-mail-Composer-send:enabled");
});

test("remove an attachment from composer does not need any confirmation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ]);
    await contains(".o-mail-AttachmentCard .fa-check");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentCard");
    await click(".o-mail-AttachmentCard-unlink");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentCard", { count: 0 });
});

test("composer: paste attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    const files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ];
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentCard", { count: 0 });
    await pasteFiles(".o-mail-Composer-input", files);
    await contains(".o-mail-AttachmentList .o-mail-AttachmentCard");
});

test("Replying on a channel should focus composer initially", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "general",
    });
    pyEnv["mail.message"].create({
        body: "Hello world",
        res_id: channelId,
        message_type: "comment",
        model: "discuss.channel",
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Reply']");
    await contains(".o-mail-Composer-input:focus");
});

test("remove an uploading attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    onRpc("/mail/attachment/upload", () => new Deferred()); // simulates uploading indefinitely
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ]);
    await contains(".o-mail-AttachmentCard.o-isUploading");
    await click(".o-mail-AttachmentCard-unlink");
    await contains(".o-mail-Composer .o-mail-AttachmentCard", { count: 0 });
});

test("Show recipient list when there is more than 5 followers.", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create([
        { name: "test name 1", email: "test1@odoo.com" },
        { name: "test name 2", email: "test2@odoo.com" },
        { name: "test name 3", email: "test3@odoo.com" },
        { name: "test name 4", email: "test4@odoo.com" },
        { name: "test name 5", email: "test5@odoo.com" },
        { name: "test name 6", email: "test6@odoo.com" },
    ]);
    for (const partner of partnerIds) {
        pyEnv["mail.followers"].create({
            is_active: true,
            partner_id: partner,
            res_id: partnerIds[0],
            res_model: "res.partner",
        });
    }
    await start();
    await openFormView("res.partner", partnerIds[0]);
    await click("button", { text: "Send message" });
    await click("button[title='Show all recipients']");
    await contains("li", { text: "test1@odoo.com" });
    await contains("li", { text: "test2@odoo.com" });
    await contains("li", { text: "test3@odoo.com" });
    await contains("li", { text: "test4@odoo.com" });
    await contains("li", { text: "test5@odoo.com" });
    await contains("li", { text: "test6@odoo.com" });
    await contains(".o-mail-Chatter", {
        text: "To: test1, test2, test3, test4, test5, and 1 more",
    });
});

test("Show 'No recipient found.' with 0 followers.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test name 1", email: "test1@odoo.com" });
    await start();
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-Chatter-top", { text: "To: No recipient" });
});

test("Uploading multiple files in the composer create multiple temporary attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    onRpc("/mail/attachment/upload", () => new Deferred());
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
        await createFile({
            name: "text1.txt",
            content: "hello, world",
            contentType: "text/plain",
        }),
        await createFile({
            name: "text2.txt",
            content: "hello, world",
            contentType: "text/plain",
        }),
    ]);
    await contains(".o-mail-AttachmentCard", { text: "text1.txt" });
    await contains(".o-mail-AttachmentCard", { text: "text2.txt" });
    await contains(".o-mail-AttachmentCard-aside div[title='Uploading']", { count: 2 });
});

test("[technical] does not crash when an attachment is removed before its upload starts", async () => {
    // Uploading multiple files uploads attachments one at a time, this test
    // ensures that there is no crash when an attachment is destroyed before its
    // upload started.
    const pyEnv = await startServer();
    // Promise to block attachment uploading
    const uploadDef = new Deferred();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    onRpcBefore("/mail/attachment/upload", async () => await uploadDef);
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
        await createFile({
            name: "text1.txt",
            content: "hello, world",
            contentType: "text/plain",
        }),
        await createFile({
            name: "text2.txt",
            content: "hello, world",
            contentType: "text/plain",
        }),
    ]);
    await contains(".o-mail-AttachmentCard.o-isUploading", { text: "text1.txt" });
    await click(".o-mail-AttachmentCard-unlink", {
        parent: [".o-mail-AttachmentCard.o-isUploading", { text: "text2.txt" }],
    });
    await contains(".o-mail-AttachmentCard", { count: 0, text: "text2.txt" });
    // Simulates the completion of the upload of the first attachment
    uploadDef.resolve();
    await contains(".o-mail-AttachmentCard:not(.o-isUploading)", { text: "text1.txt" });
});

test("Message is sent only once when pressing enter twice in a row", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    triggerHotkey("Enter");
    // weak test, no guarantee that we waited long enough for the potential second message to be posted
    await contains(".o-mail-Message-content", { text: "Hello World!" });
});

test('display canned response suggestions on typing ":"', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: serverState.partnerId }],
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-Composer-suggestionList .o-open");
    await contains(".o-mail-NavigableList-item", { text: "helloHello! How are you?" });
});

test("select a canned response suggestion", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: serverState.partnerId }],
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", ":");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "Hello! How are you? " });
});

test("select a canned response suggestion with some text", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario",
        channel_member_ids: [
            [0, 0, { partner_id: serverState.partnerId }],
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "bluhbluh ");
    await contains(".o-mail-Composer-input", { value: "bluhbluh " });
    await insertText(".o-mail-Composer-input", ":");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "bluhbluh Hello! How are you? " });
});

test("add an emoji after a canned response", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario",
        channel_member_ids: [
            [0, 0, { partner_id: serverState.partnerId }],
            Command.create({ guest_id: guestId }),
        ],
    });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", ":");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "Hello! How are you? " });
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😊" });
    await contains(".o-mail-Composer-input", { value: "Hello! How are you? 😊" });
});

test("Canned response can be inserted from the bus", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: serverState.partnerId }],
            Command.create({ guest_id: guestId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-NavigableList-item", { count: 0 });
    await insertText(".o-mail-Composer-input", "", { replace: true });
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await contains(".o-mail-NavigableList-item", { count: 0 });
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-NavigableList-item", { text: "helloHello! How are you?" });
});

test("Canned response can be updated from the bus", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: serverState.partnerId }],
            Command.create({ guest_id: guestId }),
        ],
    });
    const cannedResponseId = pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-NavigableList-item", { count: 1 });
    await insertText(".o-mail-Composer-input", "", { replace: true });
    pyEnv["mail.canned.response"].write([cannedResponseId], {
        substitution: "Howdy! How are you?",
    });
    await contains(".o-mail-NavigableList-item", { count: 0 });
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-NavigableList-item", { text: "helloHowdy! How are you?" });
});

test("Canned response can be deleted from the bus", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "test",
        channel_member_ids: [
            [0, 0, { partner_id: serverState.partnerId }],
            Command.create({ guest_id: guestId }),
        ],
    });
    const [cannedResponseId] = pyEnv["mail.canned.response"].create([
        {
            source: "hello",
            substitution: "Hello! How are you?",
        },
        {
            source: "test",
            substitution: "test",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-NavigableList-item", { count: 2 });
    await insertText(".o-mail-Composer-input", "", { replace: true });
    pyEnv["mail.canned.response"].unlink([cannedResponseId]);
    await contains(".o-mail-NavigableList-item", { count: 0 });
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-Composer-input", { value: ":" });
    await contains(".o-mail-NavigableList-item", { count: 1 });
});
