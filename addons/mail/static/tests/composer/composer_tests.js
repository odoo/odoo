/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { Command } from "@mail/../tests/helpers/command";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    click,
    contains,
    createFile,
    dragenterFiles,
    dropFiles,
    insertText,
    pasteFiles,
    scroll,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import {
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { file } from "@web/../tests/legacy/helpers/test_utils";

const { inputFiles } = file;

QUnit.module("composer", {
    async beforeEach() {
        // Simulate real user interactions
        patchWithCleanup(Composer.prototype, {
            isEventTrusted() {
                return true;
            },
        });
    },
});

QUnit.test("composer text input: basic rendering when posting a message", async () => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button", { text: "Send message" });
    await contains("textarea.o-mail-Composer-input[placeholder='Send a message to followers…']");
});

QUnit.test("composer text input: basic rendering when logging note", async () => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button", { text: "Log note" });
    await contains("textarea.o-mail-Composer-input[placeholder='Log an internal note…']");
});

QUnit.test(
    "composer text input: basic rendering when linked thread is a discuss.channel",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "dofus-disco" });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-Composer");
        await contains("textarea.o-mail-Composer-input");
    }
);

QUnit.test(
    "composer text input placeholder should contain channel name when thread does not have specific correspondent",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains("textarea.o-mail-Composer-input[placeholder='Message #General…']");
    }
);

QUnit.test("add an emoji", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "swamp-safari" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😤" });
    await contains(".o-mail-Composer-input", 1, { value: "😤" });
});

QUnit.test(
    "Exiting emoji picker brings the focus back to the Composer textarea [REQUIRE FOCUS]",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "" });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        await contains(".o-mail-Composer-input:focus", 0);
        triggerHotkey("Escape");
        await contains(".o-mail-Composer-input:focus", 1);
    }
);

QUnit.test("add an emoji after some text", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "beyblade-room" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Blabla");
    await contains(".o-mail-Composer-input", 1, { value: "Blabla" });

    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "🤑" });
    await contains(".o-mail-Composer-input", 1, { value: "Blabla🤑" });
});

QUnit.test("add emoji replaces (keyboard) text selection [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Blabla");
    const textarea = (await contains(".o-mail-Composer-input", 1, { value: "Blabla" }))[0];
    // simulate selection of all the content by keyboard
    textarea.setSelectionRange(0, textarea.value.length);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "🤠" });
    await contains(".o-mail-Composer-input", 1, { value: "🤠" });
});

QUnit.test("Cursor is positioned after emoji after adding it", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    const textarea = (await insertText(".o-mail-Composer-input", "Blabla"))[0];
    textarea.setSelectionRange(2, 2);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "🤠" });
    const expectedPos = 2 + "🤠".length;
    assert.strictEqual(textarea.selectionStart, expectedPos);
    assert.strictEqual(textarea.selectionEnd, expectedPos);
});

QUnit.test("selected text is not replaced after cancelling the selection", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Blabla");
    const textarea = (await contains(".o-mail-Composer-input", 1, { value: "Blabla" }))[0];
    // simulate selection of all the content by keyboard
    textarea.setSelectionRange(0, textarea.value.length);
    await click(".o-mail-Discuss-content");
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "🤠" });
    await contains(".o-mail-Composer-input", 1, { value: "Blabla🤠" });
});

QUnit.test(
    "Selection is kept when changing channel and going back to original channel",
    async (assert) => {
        const pyEnv = await startServer();
        const [channelId] = pyEnv["discuss.channel"].create([
            { name: "channel1" },
            { name: "channel2" },
        ]);
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "Foo");
        // simulate selection of all the content by keyboard
        const textarea = $(".o-mail-Composer-input")[0];
        textarea.setSelectionRange(0, textarea.value.length);
        await nextTick();
        await click(".o-mail-DiscussSidebarChannel:eq(1)");
        await click(".o-mail-DiscussSidebarChannel:eq(0)");
        assert.ok(textarea.selectionStart === 0 && textarea.selectionEnd === textarea.value.length);
    }
);

QUnit.test(
    "click on emoji button, select emoji, then re-click on button should show emoji picker",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "roblox-skateboarding" });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        await click(".o-Emoji", { text: "👺" });
        await click("button[aria-label='Emojis']");
        await contains(".o-EmojiPicker");
    }
);

QUnit.test("keep emoji picker scroll value when re-opening it", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-carsurfing" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await scroll(".o-EmojiPicker-content", 150);
    await click("button[aria-label='Emojis']");
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content", 1, { scroll: 150 });
});

QUnit.test("reset emoji picker scroll value after an emoji is picked", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-fingerskating" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await scroll(".o-EmojiPicker-content", 150);
    await click(".o-Emoji", { text: "😎" });
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content", 1, { scroll: 0 });
});

QUnit.test(
    "keep emoji picker scroll value independent if two or more different emoji pickers are used",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "roblox-jaywalking" });
        const { openDiscuss } = await start();
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
        openDiscuss(channelId);
        await triggerEvent(getFixture(), null, "mousedown");
        await click("button[aria-label='Emojis']");
        await scroll(".o-EmojiPicker-content", 150);
        await triggerEvent(getFixture(), null, "mousedown");
        await click("[title='Add a Reaction']");
        await scroll(".o-EmojiPicker-content", 200);
        await triggerEvent(getFixture(), null, "mousedown");
        await click("button[aria-label='Emojis']");
        await contains(".o-EmojiPicker-content", 1, { scroll: 150 });
        await triggerEvent(getFixture(), null, "mousedown");
        await click("[title='Add a Reaction']");
        await contains(".o-EmojiPicker-content", 1, { scroll: 200 });
    }
);

QUnit.test("composer text input cleared on message post", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "au-secours-aidez-moi" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test message");
    await contains(".o-mail-Composer-input", 1, { value: "test message" });

    await click(".o-mail-Composer-send:not([disabled])");
    await contains(".o-mail-Message");
    await contains(".o-mail-Composer-input", 1, { value: "" });
});

QUnit.test("send message only once when button send is clicked twice quickly", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "nether-picnic" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test message");
    await click(".o-mail-Composer-send:not([disabled])");
    await click(".o-mail-Composer-send:not([disabled])");
    await contains(".o-mail-Message");
});

QUnit.test('send button on discuss.channel should have "Send" as label', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "minecraft-wii-u" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-send:disabled", 1, { text: "Send" });
});

QUnit.test("Show send button in mobile", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.SM });
    pyEnv["discuss.channel"].create({ name: "minecraft-wii-u" });
    const { openDiscuss } = await start();
    openDiscuss();
    await click("button", { text: "Channel" });
    await click(".o-mail-NotificationItem-name", { text: "minecraft-wii-u" });
    await contains(".o-mail-Composer button[aria-label='Send']");
    await contains(".o-mail-Composer button[aria-label='Send'] i.fa-paper-plane-o");
});

QUnit.test(
    "composer textarea content is retained when changing channel then going back",
    async () => {
        const pyEnv = await startServer();
        const [channelId] = pyEnv["discuss.channel"].create([
            { name: "minigolf-galaxy-iv" },
            { name: "epic-shrek-lovers" },
        ]);
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "According to all known laws of aviation,");
        await click("span", { text: "epic-shrek-lovers" });
        await contains("textarea.o-mail-Composer-input[placeholder='Message #epic-shrek-lovers…']");
        await contains(".o-mail-Composer-input", 1, { value: "" });
        await click("span", { text: "minigolf-galaxy-iv" });
        await contains(
            "textarea.o-mail-Composer-input[placeholder='Message #minigolf-galaxy-iv…']",
            1,
            { value: "According to all known laws of aviation," }
        );
    }
);

QUnit.test("add an emoji after a partner mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Mario Party",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-input", 1, { value: "" });
    await insertText(".o-mail-Composer-input", "@Te");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", 1, { value: "@TestPartner " });
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😊" });
    await contains(".o-mail-Composer-input", 1, { value: "@TestPartner 😊" });
});

QUnit.test("mention a channel after some text", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-input", 1, { value: "" });
    await insertText(".o-mail-Composer-input", "bluhbluh ");
    await contains(".o-mail-Composer-input", 1, { value: "bluhbluh " });
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", 1, { value: "bluhbluh #General " });
});

QUnit.test("add an emoji after a channel mention", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Composer-input", 1, { value: "" });
    await insertText(".o-mail-Composer-input", "#");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", 1, { value: "#General " });
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji", { text: "😊" });
    await contains(".o-mail-Composer-input", 1, { value: "#General 😊" });
});

QUnit.test("pending mentions are kept when toggling composer", async () => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion strong", { text: "Mitchell Admin" });
    await contains(".o-mail-Composer-input", 1, { value: "@Mitchell Admin " });
    await click("button", { text: "Send message" });
    await contains(".o-mail-Composer-input", 0);
    await click("button", { text: "Send message" });
    await click(".o-mail-Composer-send:not(:disabled)");
    await contains(".o-mail-Message-body a.o_mail_redirect", 1, { text: "@Mitchell Admin" });
});

QUnit.test('do not post message on channel with "SHIFT-Enter" keyboard shortcut', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Test");
    await contains(".o-mail-Message", 0);
    triggerHotkey("shift+Enter");
    await nextTick(); // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", 0);
});

QUnit.test('post message on channel with "Enter" keyboard shortcut', async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Test");
    await contains(".o-mail-Message", 0);
    triggerHotkey("Enter");
    await contains(".o-mail-Message");
});

QUnit.test("leave command on channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel:contains(general).o-active");
    await insertText(".o-mail-Composer-input", "/leave");
    await contains(".o-mail-Composer-suggestion strong", 1);
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", 1, { value: "/leave " });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel span", 0, { text: "general" });

    await contains(".o-mail-Discuss h4.text-muted", 1, { text: "No conversation selected." });
    await contains(".o_notification_content", 1, { text: "You unsubscribed from general." });
});

QUnit.test("Can handle leave notification from unknown member", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Dobby" });
    const partnerId = pyEnv["res.partner"].create({ name: "Dobby", user_ids: [userId] });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { env, openDiscuss } = await start();
    openDiscuss(channelId);
    await pyEnv.withUser(userId, () =>
        env.services.orm.call("discuss.channel", "action_unfollow", [channelId])
    );
    await click("button[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", 1, { text: "Mitchell Admin" });
    await contains(".o-discuss-ChannelMember", 0, { text: "Dobby" });
});

QUnit.test("leave command on chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck Norris" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebarChannel:contains(Chuck Norris).o-active");
    await insertText(".o-mail-Composer-input", "/leave");
    await contains(".o-mail-Composer-suggestion strong", 1);
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", 1, { value: "/leave " });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel span", 0, { text: "Chuck Norris" });

    await contains(".o-mail-Discuss h4.text-muted", 1, { text: "No conversation selected." });
    await contains(".o_notification_content", 1, {
        text: "You unpinned your conversation with Chuck Norris",
    });
});

QUnit.test("Can post suggestions", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#general");
    await contains(".o-mail-Composer-suggestion strong", 1);
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", 1, { value: "#general " });
    triggerHotkey("Enter");
    await contains(".o-mail-Message .o_channel_redirect");
});

QUnit.test(
    "composer text input placeholder should contain correspondent name when thread has exactly one correspondent",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains("textarea.o-mail-Composer-input[placeholder='Message Marc Demo…']");
    }
);

QUnit.test("quick edit last self-message from UP arrow", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Test",
        attachment_ids: [],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message-content", 1, { text: "Test" });
    await contains(".o-mail-Message:contains(Test) .o-mail-Composer", 0);

    triggerHotkey("ArrowUp");
    await contains(".o-mail-Message .o-mail-Composer");

    triggerHotkey("Escape");
    await contains(".o-mail-Message .o-mail-Composer", 0);
    await contains(".o-mail-Composer-input:focus");

    // non-empty composer should not trigger quick edit
    await insertText(".o-mail-Composer-input", "Shrek");
    triggerHotkey("ArrowUp");
    // Navigable List relies on useEffect, which behaves with 2 animation frames
    // Wait 2 animation frames to make sure it doesn't show quick edit
    await nextTick();
    await nextTick();
    await contains(".o-mail-Message .o-mail-Composer", 0);
});

QUnit.test("Select composer suggestion via Enter does not send the message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "shrek@odoo.com",
        name: "Shrek",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@Shrek");
    await contains(".o-mail-Composer-suggestion");
    triggerHotkey("Enter");
    await contains(".o-mail-Composer-input", 1, { value: "@Shrek " });
    // weak test, no guarantee that we waited long enough for the potential message to be posted
    await contains(".o-mail-Message", 0);
});

QUnit.test("composer: drop attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
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
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-Dropzone", 0);
    await contains(".o-mail-AttachmentCard", 0);
    dragenterFiles($(".o-mail-Composer-input")[0]);
    await contains(".o-mail-Dropzone");
    await contains(".o-mail-AttachmentCard", 0);
    dropFiles((await contains(".o-mail-Dropzone"))[0], files);
    await contains(".o-mail-Dropzone", 0);
    await contains(".o-mail-AttachmentCard", 2);
    dragenterFiles($(".o-mail-Composer-input")[0]);
    dropFiles((await contains(".o-mail-Dropzone"))[0], [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text3.txt",
        }),
    ]);
    await contains(".o-mail-AttachmentCard", 3);
});

QUnit.test("composer: add an attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles((await contains(".o-mail-Composer-coreMain .o_input_file"))[0], [file]);
    await contains(".o-mail-AttachmentCard .fa-check");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard");
});

QUnit.test("composer: add an attachment in reply to message in history", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        history_partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
        is_read: true,
    });
    const { openDiscuss } = await start();
    openDiscuss("mail.box_history");
    await click("[title='Reply']");
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles((await contains(".o-mail-Composer-coreMain .o_input_file"))[0], [file]);
    await contains(".o-mail-AttachmentCard .fa-check");

    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard");
});

QUnit.test("composer: send button is disabled if attachment upload is not finished", async () => {
    const pyEnv = await startServer();
    const attachmentUploadedPromise = makeDeferred();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start({
        async mockRPC(route) {
            if (route === "/mail/attachment/upload") {
                await attachmentUploadedPromise;
            }
        },
    });
    openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles((await contains(".o-mail-Composer-coreMain .o_input_file"))[0], [file]);
    await contains(".o-mail-AttachmentCard.o-isUploading");
    await contains(".o-mail-Composer-send:disabled");
    // simulates attachment finishes uploading
    attachmentUploadedPromise.resolve();
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard.o-isUploading", 0);
    await contains(".o-mail-Composer-send:not(:disabled)");
});

QUnit.test("remove an attachment from composer does not need any confirmation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles((await contains(".o-mail-Composer-coreMain .o_input_file"))[0], [file]);
    await contains(".o-mail-AttachmentCard .fa-check");
    await contains(".o-mail-Composer-footer .o-mail-AttachmentList");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentCard");

    await click(".o-mail-AttachmentCard-unlink");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentCard", 0);
});

QUnit.test("composer: paste attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    const files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ];
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-AttachmentList .o-mail-AttachmentCard", 0);
    pasteFiles($(".o-mail-Composer-input")[0], files);
    await contains(".o-mail-AttachmentList .o-mail-AttachmentCard");
});

QUnit.test("Replying on a channel should focus composer initially", async () => {
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
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Reply']");
    await contains(".o-mail-Composer-input:focus");
});

QUnit.test("remove an uploading attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const { openDiscuss } = await start({
        async mockRPC(route) {
            if (route === "/mail/attachment/upload") {
                // simulates uploading indefinitely
                await new Promise(() => {});
            }
        },
    });
    openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles((await contains(".o-mail-Composer-coreMain .o_input_file"))[0], [file]);
    await contains(".o-mail-AttachmentCard.o-isUploading");

    click(".o-mail-AttachmentCard-unlink");
    await contains(".o-mail-Composer .o-mail-AttachmentCard", 0);
});

QUnit.test("Show a thread name in the recipient status text.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test name", email: "test@odoo.com" });
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-Chatter div", 1, { text: "To: test" });
    await contains('span[title="test@odoo.com"]');
});

QUnit.test("Show recipient list when there is more than 5 followers.", async () => {
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
    const { openFormView } = await start();
    openFormView("res.partner", partnerIds[0]);
    await click("button", { text: "Send message" });
    await click("button[title='Show all recipients']");
    await contains("li", 1, { text: "test1@odoo.com" });
    await contains("li", 1, { text: "test2@odoo.com" });
    await contains("li", 1, { text: "test3@odoo.com" });
    await contains("li", 1, { text: "test4@odoo.com" });
    await contains("li", 1, { text: "test5@odoo.com" });
    await contains("li", 1, { text: "test6@odoo.com" });
    await contains(".o-mail-Chatter div", 1, { text: "To: test1, test2, test3, test4, test5, …" });
});

QUnit.test(
    "Uploading multiple files in the composer create multiple temporary attachments",
    async () => {
        const pyEnv = await startServer();
        // Promise to block attachment uploading
        const uploadPromise = makeDeferred();
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/attachment/upload") {
                    await uploadPromise;
                }
            },
        });
        openDiscuss(channelId);
        const file1 = await createFile({
            name: "text1.txt",
            content: "hello, world",
            contentType: "text/plain",
        });
        const file2 = await createFile({
            name: "text2.txt",
            content: "hello, world",
            contentType: "text/plain",
        });
        inputFiles((await contains(".o-mail-Composer-coreMain .o_input_file"))[0], [file1, file2]);
        await contains(".o-mail-AttachmentCard div", 1, { text: "text1.txt" });
        await contains(".o-mail-AttachmentCard div", 1, { text: "text2.txt" });
        await contains(".o-mail-AttachmentCard-aside div[title='Uploading']", 2);
    }
);

QUnit.test(
    "[technical] does not crash when an attachment is removed before its upload starts",
    async () => {
        // Uploading multiple files uploads attachments one at a time, this test
        // ensures that there is no crash when an attachment is destroyed before its
        // upload started.
        const pyEnv = await startServer();
        // Promise to block attachment uploading
        const uploadPromise = makeDeferred();
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/attachment/upload") {
                    await uploadPromise;
                }
            },
        });
        openDiscuss(channelId);
        const [input, file1, file2] = await Promise.all([
            contains(".o-mail-Composer-coreMain .o_input_file"),
            createFile({
                name: "text1.txt",
                content: "hello, world",
                contentType: "text/plain",
            }),
            createFile({
                name: "text2.txt",
                content: "hello, world",
                contentType: "text/plain",
            }),
        ]);
        inputFiles(input[0], [file1, file2]);
        await contains(".o-mail-AttachmentCard.o-isUploading div", 1, { text: "text1.txt" });
        await contains(".o-mail-AttachmentCard.o-isUploading div", 1, { text: "text2.txt" });

        click(".o-mail-AttachmentCard-unlink:eq(1)");
        await contains(".o-mail-AttachmentCard div", 0, { text: "text2.txt" });

        // Simulates the completion of the upload of the first attachment
        uploadPromise.resolve();
        await contains('.o-mail-AttachmentCard:not(.o-isUploading):contains("text1.txt")');
    }
);

QUnit.test("Message is sent only once when pressing enter twice in a row", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello World!");
    await afterNextRender(async () => {
        // weak test, no guarantee that we waited long enough for the potential second message to be
        // posted. afterNextRender is the *minimum* to see the issue (before it was fixed): it
        // should not be removed even it the test works without it.
        triggerHotkey("Enter");
        triggerHotkey("Enter");
    });
    await contains(".o-mail-Message-content", 1, { text: "Hello World!" });
});
