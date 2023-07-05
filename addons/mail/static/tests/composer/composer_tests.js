/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { Command } from "@mail/../tests/helpers/command";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import {
    afterNextRender,
    click,
    createFile,
    dragenterFiles,
    dropFiles,
    insertText,
    pasteFiles,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import {
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { file } from "web.test_utils";

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

QUnit.test("composer text input: basic rendering when posting a message", async (assert) => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    await openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button:contains(Send message)");
    assert.containsOnce($, ".o-mail-Composer");
    assert.containsOnce($, "textarea.o-mail-Composer-input");
    assert.hasAttrValue(
        $(".o-mail-Composer-input"),
        "placeholder",
        "Send a message to followers..."
    );
});

QUnit.test("composer text input: basic rendering when logging note", async (assert) => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    await openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button:contains(Log note)");
    assert.containsOnce($, ".o-mail-Composer");
    assert.containsOnce($, "textarea.o-mail-Composer-input");
    assert.hasAttrValue($(".o-mail-Composer-input"), "placeholder", "Log an internal note...");
});

QUnit.test(
    "composer text input: basic rendering when linked thread is a discuss.channel",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "dofus-disco" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Composer");
        assert.containsOnce($, "textarea.o-mail-Composer-input");
    }
);

QUnit.test(
    "composer text input placeholder should contain channel name when thread does not have specific correspondent",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.hasAttrValue($(".o-mail-Composer-input"), "placeholder", "Message #General…");
    }
);

QUnit.test("add an emoji", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "swamp-safari" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await click(".o-mail-Emoji:contains(😤)");
    assert.strictEqual($(".o-mail-Composer-input").val(), "😤");
});

QUnit.test(
    "Exiting emoji picker brings the focus back to the Composer textarea",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        await afterNextRender(() => triggerHotkey("Escape"));
        assert.equal($(".o-mail-Composer-input")[0], document.activeElement);
    }
);

QUnit.test("add an emoji after some text", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "beyblade-room" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Blabla");
    assert.strictEqual($(".o-mail-Composer-input").val(), "Blabla");

    await click("button[aria-label='Emojis']");
    await click(".o-mail-Emoji:contains(🤑)");
    assert.strictEqual($(".o-mail-Composer-input").val(), "Blabla🤑");
});

QUnit.test("add emoji replaces (keyboard) text selection", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const textarea = $(".o-mail-Composer-input")[0];
    await insertText(".o-mail-Composer-input", "Blabla");
    assert.strictEqual(textarea.value, "Blabla");

    // simulate selection of all the content by keyboard
    textarea.setSelectionRange(0, textarea.value.length);
    await click("button[aria-label='Emojis']");
    await click(".o-mail-Emoji:contains(🤠)");
    assert.strictEqual($(".o-mail-Composer-input").val(), "🤠");
});

QUnit.test("Cursor is positioned after emoji after adding it", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const textarea = $(".o-mail-Composer-input")[0];
    await insertText(".o-mail-Composer-input", "Blabla");
    textarea.setSelectionRange(2, 2);
    await click("button[aria-label='Emojis']");
    await click(".o-mail-Emoji:contains(🤠)");
    const expectedPos = 2 + "🤠".length;
    assert.strictEqual(textarea.selectionStart, expectedPos);
    assert.strictEqual(textarea.selectionEnd, expectedPos);
});

QUnit.test("selected text is not replaced after cancelling the selection", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const textarea = $(".o-mail-Composer-input")[0];
    await insertText(".o-mail-Composer-input", "Blabla");
    assert.strictEqual(textarea.value, "Blabla");

    // simulate selection of all the content by keyboard
    textarea.setSelectionRange(0, textarea.value.length);
    $(".o-mail-Discuss-content")[0].click();
    await nextTick();
    await click("button[aria-label='Emojis']");
    await click(".o-mail-Emoji:contains(🤠)");
    assert.strictEqual($(".o-mail-Composer-input").val(), "Blabla🤠");
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
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "Foo");
        // simulate selection of all the content by keyboard
        const textarea = $(".o-mail-Composer-input")[0];
        textarea.setSelectionRange(0, textarea.value.length);
        await nextTick();
        await click($(".o-mail-DiscussCategoryItem:eq(1)"));
        await click($(".o-mail-DiscussCategoryItem:eq(0)"));
        assert.ok(textarea.selectionStart === 0 && textarea.selectionEnd === textarea.value.length);
    }
);

QUnit.test(
    "click on emoji button, select emoji, then re-click on button should show emoji picker",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "roblox-skateboarding" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        await click(".o-mail-Emoji:contains(👺)");
        await click("button[aria-label='Emojis']");
        assert.containsOnce($, ".o-mail-EmojiPicker");
    }
);

QUnit.test("keep emoji picker scroll value when re-opening it", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-carsurfing" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    $(".o-mail-EmojiPicker-content")[0].scrollTop = 150;
    await click("button[aria-label='Emojis']");
    await click("button[aria-label='Emojis']");
    assert.strictEqual($(".o-mail-EmojiPicker-content")[0].scrollTop, 150);
});

QUnit.test("reset emoji picker scroll value after an emoji is picked", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "roblox-fingerskating" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    $(".o-mail-EmojiPicker-content")[0].scrollTop = 150;
    await click(".o-mail-Emoji:contains(😎)");
    await click("button[aria-label='Emojis']");
    assert.strictEqual($(".o-mail-EmojiPicker-content")[0].scrollTop, 0);
});

QUnit.test(
    "keep emoji picker scroll value independent if two or more different emoji pickers are used",
    async (assert) => {
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
        await openDiscuss(channelId);

        await triggerEvent(getFixture(), null, "mousedown");
        await click("button[aria-label='Emojis']");
        $(".o-mail-EmojiPicker-content")[0].scrollTop = 150;

        await triggerEvent(getFixture(), null, "mousedown");
        await click("[title='Add a Reaction']");
        $(".o-mail-EmojiPicker-content")[0].scrollTop = 200;

        await triggerEvent(getFixture(), null, "mousedown");
        await click("button[aria-label='Emojis']");
        assert.strictEqual($(".o-mail-EmojiPicker-content")[0].scrollTop, 150);

        await triggerEvent(getFixture(), null, "mousedown");
        await click("[title='Add a Reaction']");
        assert.strictEqual($(".o-mail-EmojiPicker-content")[0].scrollTop, 200);
    }
);

QUnit.test("composer text input cleared on message post", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "au-secours-aidez-moi" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test message");
    assert.strictEqual($(".o-mail-Composer-input").val(), "test message");

    await click(".o-mail-Composer-send");
    assert.verifySteps(["message_post"]);
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
});

QUnit.test("send message only once when button send is clicked twice quickly", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "nether-picnic" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test message");
    await afterNextRender(() => {
        $(".o-mail-Composer-send")[0].click();
        $(".o-mail-Composer-send")[0].click();
    });
    assert.verifySteps(["message_post"]);
});

QUnit.test('send button on discuss.channel should have "Send" as label', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "minecraft-wii-u" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.strictEqual($(".o-mail-Composer-send").text().trim(), "Send");
});

QUnit.test("Show send button in mobile", async (assert) => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.SM });
    pyEnv["discuss.channel"].create({ name: "minecraft-wii-u" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Channel)");
    await click(".o-mail-NotificationItem:contains(minecraft-wii-u)");
    assert.containsOnce($, ".o-mail-Composer button[aria-label='Send']");
    assert.containsOnce($, ".o-mail-Composer button[aria-label='Send'] i.fa-paper-plane-o");
});

QUnit.test(
    "composer textarea content is retained when changing channel then going back",
    async (assert) => {
        const pyEnv = await startServer();
        const [channelId] = pyEnv["discuss.channel"].create([
            { name: "minigolf-galaxy-iv" },
            { name: "epic-shrek-lovers" },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "According to all known laws of aviation,");
        await click($("span:contains('epic-shrek-lovers')"));
        await click($("span:contains('minigolf-galaxy-iv')"));
        assert.strictEqual(
            $(".o-mail-Composer-input").val(),
            "According to all known laws of aviation,"
        );
    }
);

QUnit.test("add an emoji after a partner mention", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestion");
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "T");
    await insertText(".o-mail-Composer-input", "e");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual($(".o-mail-Composer-input").val().replace(/\s/, " "), "@TestPartner ");

    await click("button[aria-label='Emojis']");
    await click(".o-mail-Emoji:contains(😊)");
    assert.strictEqual($(".o-mail-Composer-input").val().replace(/\s/, " "), "@TestPartner 😊");
});

QUnit.test("mention a channel after some text", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestion");
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
    await insertText(".o-mail-Composer-input", "bluhbluh ");
    assert.strictEqual(
        $(".o-mail-Composer-input").val(),
        "bluhbluh ",
        "text content of composer should have content"
    );
    await insertText(".o-mail-Composer-input", "#");
    assert.containsOnce($, ".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual(
        $(".o-mail-Composer-input").val().replace(/\s/, " "),
        "bluhbluh #General ",
        "previous content + mentioned channel + additional whitespace afterwards"
    );
});

QUnit.test("add an emoji after a channel mention", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Composer-suggestion");
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
    await insertText(".o-mail-Composer-input", "#");
    assert.containsOnce($, ".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-suggestion");
    assert.strictEqual(
        $(".o-mail-Composer-input").val().replace(/\s/, " "),
        "#General ",
        "previous content + mentioned channel + additional whitespace afterwards"
    );

    // select emoji
    await click("button[aria-label='Emojis']");
    await click(".o-mail-Emoji:contains(😊)");
    assert.strictEqual($(".o-mail-Composer-input").val().replace(/\s/, " "), "#General 😊");
});

QUnit.test("pending mentions are kept when toggling composer", async (assert) => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    await openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button:contains(Send message)");
    await insertText(".o-mail-Composer-input", "@");
    await click(".o-mail-Composer-suggestion:contains(Mitchell Admin)");
    await click("button:contains(Send message)");
    await click("button:contains(Send message)");
    await click(".o-mail-Composer-send");
    assert.containsOnce($, ".o-mail-Message-body a.o_mail_redirect:contains(@Mitchell Admin)");
});

QUnit.test(
    'do not post message on channel with "SHIFT-Enter" keyboard shortcut',
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "general" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsNone($, ".o-mail-Message");

        await insertText(".o-mail-Composer-input", "Test");
        await triggerHotkey("shift+Enter");
        await nextTick();
        assert.containsNone($, ".o-mail-Message");
    }
);

QUnit.test('post message on channel with "Enter" keyboard shortcut', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-mail-Message");

    // insert some HTML in editable
    await insertText(".o-mail-Composer-input", "Test");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce($, ".o-mail-Message");
});

QUnit.test("leave command on channel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => {
                assert.step(message);
            }),
        },
    });
    await openDiscuss(channelId);
    assert.hasClass($(".o-mail-DiscussCategoryItem:contains(general)"), "o-active");
    await insertText(".o-mail-Composer-input", "/leave");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(general)");
    assert.containsOnce($, ".o-mail-Discuss:contains(No conversation selected.)");
    assert.verifySteps(["You unsubscribed from general."]);
});

QUnit.test("leave command on chat", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck Norris" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => {
                assert.step(message);
            }),
        },
    });
    await openDiscuss(channelId);
    assert.hasClass($(".o-mail-DiscussCategoryItem:contains(Chuck Norris)"), "o-active");
    await insertText(".o-mail-Composer-input", "/leave");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(Chuck Norris)");
    assert.containsOnce($, ".o-mail-Discuss:contains(No conversation selected.)");
    assert.verifySteps(["You unpinned your conversation with Chuck Norris"]);
});

QUnit.test("Can post suggestions", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    insertText(".o-mail-Composer-input", "#");
    await nextTick();
    await insertText(".o-mail-Composer-input", "general");
    // Close the popup.
    await afterNextRender(() => triggerHotkey("Enter"));
    // Send the message.
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce($, ".o-mail-Message .o_channel_redirect");
});

QUnit.test(
    "composer text input placeholder should contain correspondent name when thread has exactly one correspondent",
    async (assert) => {
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
        await openDiscuss(channelId);
        assert.hasAttrValue($(".o-mail-Composer-input"), "placeholder", "Message Marc Demo…");
    }
);

QUnit.test("send message only once when enter is pressed twice quickly", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(channelId);
    // Type message
    await insertText(".o-mail-Composer-input", "test message");
    triggerHotkey("Enter");
    triggerHotkey("Enter");
    await nextTick();
    assert.verifySteps(["message_post"], "The message has been posted only once");
});

QUnit.test("quick edit last self-message from UP arrow", async (assert) => {
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
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Message:contains(Test)");
    assert.containsNone($, ".o-mail-Message:contains(Test) .o-mail-Composer");

    await afterNextRender(() => triggerHotkey("ArrowUp"));
    assert.containsOnce($, ".o-mail-Message .o-mail-Composer");

    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone($, ".o-mail-Message .o-mail-Composer");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);

    // non-empty composer should not trigger quick edit
    await insertText(".o-mail-Composer-input", "Shrek");
    await triggerHotkey("ArrowUp");
    // Navigable List relies on useEffect, which behaves with 2 animation frames
    // Wait 2 animation frames to make sure it doesn't show quick edit
    await nextTick();
    await nextTick();
    assert.containsNone($, ".o-mail-Message .o-mail-Composer");
});

QUnit.test("Select composer suggestion via Enter does not send the message", async (assert) => {
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
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await insertText(".o-mail-Composer-input", "Shrek");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.equal($(".o-mail-Composer-input").val().trim(), "@Shrek");
    assert.verifySteps([]);
});

QUnit.test("composer: drop attachments", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
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
    assert.containsNone($, ".o-mail-Dropzone");
    assert.containsNone($, ".o-mail-AttachmentCard");

    await afterNextRender(() => dragenterFiles($(".o-mail-Composer-input")[0]));
    assert.containsOnce($, ".o-mail-Dropzone");
    assert.containsNone($, ".o-mail-AttachmentCard");

    await afterNextRender(() => dropFiles($(".o-mail-Dropzone")[0], files));
    assert.containsNone($, ".o-mail-Dropzone");
    assert.containsN($, ".o-mail-AttachmentCard", 2);

    await afterNextRender(() => dragenterFiles($(".o-mail-Composer-input")[0]));
    await afterNextRender(async () =>
        dropFiles($(".o-mail-Dropzone")[0], [
            await createFile({
                content: "hello, world",
                contentType: "text/plain",
                name: "text3.txt",
            }),
        ])
    );
    assert.containsN($, ".o-mail-AttachmentCard", 3);
});

QUnit.test("composer: add an attachment", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles($(".o-mail-Composer-coreMain .o_input_file")[0], [file]);
    await waitUntil(".o-mail-AttachmentCard .fa-check");

    assert.containsOnce($, ".o-mail-Composer-footer .o-mail-AttachmentList");
    assert.containsOnce($, ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard");
});

QUnit.test("composer: add an attachment in reply to message in history", async (assert) => {
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
    await openDiscuss("mail.box_history");
    await click("[title='Reply']");
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles($(".o-mail-Composer-coreMain .o_input_file")[0], [file]);
    await waitUntil(".o-mail-AttachmentCard .fa-check");

    assert.containsOnce($, ".o-mail-Composer-footer .o-mail-AttachmentList");
    assert.containsOnce($, ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentCard");
});

QUnit.test(
    "composer: send button is disabled if attachment upload is not finished",
    async (assert) => {
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
        await openDiscuss(channelId);
        const file = await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        });
        inputFiles($(".o-mail-Composer-coreMain .o_input_file")[0], [file]);
        await waitUntil(".o-mail-AttachmentCard.o-isUploading");
        assert.containsOnce($, ".o-mail-Composer-send");
        assert.ok($(".o-mail-Composer-send")[0].attributes.disabled);

        // simulates attachment finishes uploading
        await afterNextRender(() => attachmentUploadedPromise.resolve());
        assert.containsOnce($, ".o-mail-AttachmentCard");
        assert.containsNone($, ".o-mail-AttachmentCard.o-isUploading");
        assert.containsOnce($, ".o-mail-Composer-send");
        assert.notOk($(".o-mail-Composer-send")[0].attributes.disabled);
    }
);

QUnit.test("remove an attachment from composer does not need any confirmation", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles($(".o-mail-Composer-coreMain .o_input_file")[0], [file]);
    await waitUntil(".o-mail-AttachmentCard .fa-check");
    assert.containsOnce($, ".o-mail-Composer-footer .o-mail-AttachmentList");
    assert.containsOnce($, ".o-mail-AttachmentList .o-mail-AttachmentCard");

    await click(".o-mail-AttachmentCard-unlink");
    assert.containsNone($, ".o-mail-AttachmentList .o-mail-AttachmentCard");
});

QUnit.test("composer: paste attachments", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ];
    assert.containsNone($, ".o-mail-AttachmentList .o-mail-AttachmentCard");

    await afterNextRender(() => pasteFiles($(".o-mail-Composer-input")[0], files));
    assert.containsOnce($, ".o-mail-AttachmentList .o-mail-AttachmentCard");
});

QUnit.test("Replying on a channel should focus composer initially", async (assert) => {
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
    await openDiscuss(channelId);
    await click("[title='Reply']");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);
});

QUnit.test("remove an uploading attachment", async (assert) => {
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
    await openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles($(".o-mail-Composer-coreMain .o_input_file")[0], [file]);
    await waitUntil(".o-mail-AttachmentCard.o-isUploading");
    assert.containsOnce($, ".o-mail-AttachmentCard.o-isUploading");

    await click(".o-mail-AttachmentCard-unlink");
    assert.containsNone($, ".o-mail-Composer .o-mail-AttachmentCard");
});

QUnit.test("Show a thread name in the recipient status text.", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test name", email: "test@odoo.com" });
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    assert.containsOnce($, ".o-mail-Chatter:contains(To: test)");
    assert.containsOnce($, 'span[title="test@odoo.com"]');
});

QUnit.test("Show follower list when there is more than 5 followers.", async (assert) => {
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
    await openFormView("res.partner", partnerIds[0]);
    await click("button:contains(Send message)");
    assert.containsOnce($, "button[title='Show all recipients']");
    await click("button[title='Show all recipients']");
    assert.containsOnce($, "li:contains('test1@odoo.com')");
    assert.containsOnce($, "li:contains('test2@odoo.com')");
    assert.containsOnce($, "li:contains('test3@odoo.com')");
    assert.containsOnce($, "li:contains('test4@odoo.com')");
    assert.containsOnce($, "li:contains('test5@odoo.com')");
    assert.containsOnce($, "li:contains('test6@odoo.com')");
    assert.containsOnce($, ".o-mail-Chatter:contains('test1, test2, test3, test4, test5, …')");
});

QUnit.test(
    "Uploading multiple files in the composer create multiple temporary attachments",
    async (assert) => {
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
        await openDiscuss(channelId);
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
        inputFiles($(".o-mail-Composer-coreMain .o_input_file")[0], [file1, file2]);
        await waitUntil(".o-mail-AttachmentCard:contains(text1.txt)");
        await waitUntil(".o-mail-AttachmentCard:contains(text2.txt)");
        assert.containsN($, ".o-mail-AttachmentCard-aside div[title='Uploading']", 2);
    }
);

QUnit.test(
    "[technical] does not crash when an attachment is removed before its upload starts",
    async (assert) => {
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
        await openDiscuss(channelId);
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
        inputFiles($(".o-mail-Composer-coreMain .o_input_file")[0], [file1, file2]);
        await waitUntil(".o-mail-AttachmentCard:contains(text1.txt)");
        await waitUntil(".o-mail-AttachmentCard:contains(text2.txt)");
        await click(".o-mail-AttachmentCard-unlink:eq(1)");

        // Simulates the completion of the upload of the first attachment
        await afterNextRender(() => uploadPromise.resolve());
        assert.containsOnce($, '.o-mail-AttachmentCard:contains("text1.txt")');
    }
);

QUnit.test("Message is sent only once when pressing enter twice in a row", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello World!");
    // Simulate user pressing enter twice in a row.
    await afterNextRender(async () => {
        triggerHotkey("Enter");
        await nextTick();
        triggerHotkey("Enter");
    });
    assert.containsOnce($, ".o-mail-Message:contains(Hello World!)");
});
