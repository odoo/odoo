/** @odoo-module **/

import { file } from "web.test_utils";
import {
    afterNextRender,
    click,
    createFile,
    dragenterFiles,
    dropFiles,
    insertText,
    start,
    startServer,
    pasteFiles,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
const { inputFiles } = file;

import {
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { Composer } from "@mail/new/composer/composer";
import { patchUiSize, SIZES } from "../../helpers/patch_ui_size";

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
    assert.containsOnce($, ".o-Composer");
    assert.containsOnce($, "textarea.o-Composer-input");
    assert.hasAttrValue($(".o-Composer-input"), "placeholder", "Send a message to followers...");
});

QUnit.test("composer text input: basic rendering when logging note", async (assert) => {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    await openFormView("res.partner", pyEnv.currentPartnerId);
    await click("button:contains(Log note)");
    assert.containsOnce($, ".o-Composer");
    assert.containsOnce($, "textarea.o-Composer-input");
    assert.hasAttrValue($(".o-Composer-input"), "placeholder", "Log an internal note...");
});

QUnit.test(
    "composer text input: basic rendering when linked thread is a mail.channel",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "dofus-disco" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Composer");
        assert.containsOnce($, "textarea.o-Composer-input");
    }
);

QUnit.test(
    "composer text input placeholder should contain channel name when thread does not have specific correspondent",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.hasAttrValue($(".o-Composer-input"), "placeholder", "Message #General…");
    }
);

QUnit.test("add an emoji", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "swamp-safari" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(😤)");
    assert.strictEqual($(".o-Composer-input").val(), "😤");
});

QUnit.test(
    "Exiting emoji picker brings the focus back to the Composer textarea",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        await afterNextRender(() => triggerHotkey("Escape"));
        assert.equal($(".o-Composer-input")[0], document.activeElement);
    }
);

QUnit.test("add an emoji after some text", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "beyblade-room" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "Blabla");
    assert.strictEqual($(".o-Composer-input").val(), "Blabla");

    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(🤑)");
    assert.strictEqual($(".o-Composer-input").val(), "Blabla🤑");
});

QUnit.test("add emoji replaces (keyboard) text selection", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const textarea = $(".o-Composer-input")[0];
    await insertText(".o-Composer-input", "Blabla");
    assert.strictEqual(textarea.value, "Blabla");

    // simulate selection of all the content by keyboard
    textarea.setSelectionRange(0, textarea.value.length);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(🤠)");
    assert.strictEqual($(".o-Composer-input").val(), "🤠");
});

QUnit.test("Cursor is positioned after emoji after adding it", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const textarea = $(".o-Composer-input")[0];
    await insertText(".o-Composer-input", "Blabla");
    textarea.setSelectionRange(2, 2);
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(🤠)");
    const expectedPos = 2 + "🤠".length;
    assert.strictEqual(textarea.selectionStart, expectedPos);
    assert.strictEqual(textarea.selectionEnd, expectedPos);
});

QUnit.test("selected text is not replaced after cancelling the selection", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const textarea = $(".o-Composer-input")[0];
    await insertText(".o-Composer-input", "Blabla");
    assert.strictEqual(textarea.value, "Blabla");

    // simulate selection of all the content by keyboard
    textarea.setSelectionRange(0, textarea.value.length);
    $(".o-Discuss-content")[0].click();
    await nextTick();
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(🤠)");
    assert.strictEqual($(".o-Composer-input").val(), "Blabla🤠");
});

QUnit.test(
    "Selection is kept when changing channel and going back to original channel",
    async (assert) => {
        const pyEnv = await startServer();
        const [channelId] = pyEnv["mail.channel"].create([
            { name: "channel1" },
            { name: "channel2" },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-Composer-input", "Foo");
        // simulate selection of all the content by keyboard
        const textarea = $(".o-Composer-input")[0];
        textarea.setSelectionRange(0, textarea.value.length);
        await nextTick();
        await click($(".o-DiscussCategoryItem:eq(1)"));
        await click($(".o-DiscussCategoryItem:eq(0)"));
        assert.ok(textarea.selectionStart === 0 && textarea.selectionEnd === textarea.value.length);
    }
);

QUnit.test(
    "click on emoji button, select emoji, then re-click on button should show emoji picker",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "roblox-skateboarding" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        await click(".o-Emoji:contains(👺)");
        await click("button[aria-label='Emojis']");
        assert.containsOnce($, ".o-EmojiPicker");
    }
);

QUnit.test("keep emoji picker scroll value when re-opening it", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "roblox-carsurfing" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    $(".o-EmojiPicker-content")[0].scrollTop = 150;
    await click("button[aria-label='Emojis']");
    await click("button[aria-label='Emojis']");
    assert.strictEqual($(".o-EmojiPicker-content")[0].scrollTop, 150);
});

QUnit.test("reset emoji picker scroll value after an emoji is picked", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "roblox-fingerskating" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    $(".o-EmojiPicker-content")[0].scrollTop = 150;
    await click(".o-Emoji:contains(😎)");
    await click("button[aria-label='Emojis']");
    assert.strictEqual($(".o-EmojiPicker-content")[0].scrollTop, 0);
});

QUnit.test(
    "keep emoji picker scroll value independent if two or more different emoji pickers are used",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "roblox-jaywalking" });
        const { openDiscuss } = await start();
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "mail.channel",
            res_id: channelId,
        });
        await openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        $(".o-EmojiPicker-content")[0].scrollTop = 150;
        await click("i[title='Add a Reaction']");
        $(".o-EmojiPicker-content")[0].scrollTop = 200;
        await click("button[aria-label='Emojis']");
        assert.strictEqual($(".o-EmojiPicker-content")[0].scrollTop, 150);
        await click("i[title='Add a Reaction']");
        assert.strictEqual($(".o-EmojiPicker-content")[0].scrollTop, 200);
    }
);

QUnit.test('do not send typing notification on typing "/" command', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "channel" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/channel/notify_typing") {
                assert.step(`notify_typing:${args.is_typing}`);
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "/");
    assert.verifySteps([], "No rpc done");
});

QUnit.test("composer text input cleared on message post", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "au-secours-aidez-moi" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "test message");
    assert.strictEqual($(".o-Composer-input").val(), "test message");

    await click(".o-Composer-send");
    assert.verifySteps(["message_post"]);
    assert.strictEqual($(".o-Composer-input").val(), "");
});

QUnit.test("send message only once when button send is clicked twice quickly", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "nether-picnic" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "test message");
    await afterNextRender(() => {
        $(".o-Composer-send")[0].click();
        $(".o-Composer-send")[0].click();
    });
    assert.verifySteps(["message_post"]);
});

QUnit.test('send button on mail.channel should have "Send" as label', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "minecraft-wii-u" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.strictEqual($(".o-Composer-send").text().trim(), "Send");
});

QUnit.test("Show send button in mobile", async (assert) => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.SM });
    pyEnv["mail.channel"].create({ name: "minecraft-wii-u" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Channel)");
    await click(".o-NotificationItem:contains(minecraft-wii-u)");
    assert.containsOnce($, ".o-Composer button[aria-label='Send']");
    assert.containsOnce($, ".o-Composer button[aria-label='Send'] i.fa-paper-plane-o");
});

QUnit.test(
    "composer textarea content is retained when changing channel then going back",
    async (assert) => {
        const pyEnv = await startServer();
        const [channelId] = pyEnv["mail.channel"].create([
            { name: "minigolf-galaxy-iv" },
            { name: "epic-shrek-lovers" },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-Composer-input", "According to all known laws of aviation,");
        await click($("span:contains('epic-shrek-lovers')"));
        await click($("span:contains('minigolf-galaxy-iv')"));
        assert.strictEqual(
            $(".o-Composer-input").val(),
            "According to all known laws of aviation,"
        );
    }
);

QUnit.test(
    'do not send typing notification on typing after selecting suggestion from "/" command',
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "channel" });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(channelId);
        await insertText(".o-Composer-input", "/");
        await click(".o-composer-suggestion");
        await insertText(".o-Composer-input", " is user?");
        assert.verifySteps([], "No rpc done");
    }
);

QUnit.test("add an emoji after a command", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-composer-suggestion-list .o-open");
    assert.strictEqual($(".o-Composer-input").val(), "");
    await insertText(".o-Composer-input", "/");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        $(".o-Composer-input").val().replace(/\s/, " "),
        "/who ",
        "previous content + used command + additional whitespace afterwards"
    );

    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(😊)");
    assert.strictEqual($(".o-Composer-input").val().replace(/\s/, " "), "/who 😊");
});

QUnit.test("add an emoji after a canned response", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "Mario Party",
    });
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-composer-suggestion");
    assert.strictEqual($(".o-Composer-input").val(), "");
    await insertText(".o-Composer-input", ":");
    assert.containsOnce($, ".o-composer-suggestion");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        $(".o-Composer-input").val().replace(/\s/, " "),
        "Hello! How are you? ",
        "previous content + canned response substitution + additional whitespace afterwards"
    );

    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(😊)");
    assert.strictEqual($(".o-Composer-input").val().replace(/\s/, " "), "Hello! How are you? 😊");
});

QUnit.test("add an emoji after a partner mention", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const channelId = pyEnv["mail.channel"].create({
        name: "Mario Party",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-composer-suggestion");
    assert.strictEqual($(".o-Composer-input").val(), "");
    await insertText(".o-Composer-input", "@");
    await insertText(".o-Composer-input", "T");
    await insertText(".o-Composer-input", "e");
    await click(".o-composer-suggestion");
    assert.strictEqual($(".o-Composer-input").val().replace(/\s/, " "), "@TestPartner ");

    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(😊)");
    assert.strictEqual($(".o-Composer-input").val().replace(/\s/, " "), "@TestPartner 😊");
});

QUnit.test("mention a channel after some text", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-composer-suggestion");
    assert.strictEqual($(".o-Composer-input").val(), "");
    await insertText(".o-Composer-input", "bluhbluh ");
    assert.strictEqual(
        $(".o-Composer-input").val(),
        "bluhbluh ",
        "text content of composer should have content"
    );
    await insertText(".o-Composer-input", "#");
    assert.containsOnce($, ".o-composer-suggestion");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        $(".o-Composer-input").val().replace(/\s/, " "),
        "bluhbluh #General ",
        "previous content + mentioned channel + additional whitespace afterwards"
    );
});

QUnit.test("add an emoji after a channel mention", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-composer-suggestion");
    assert.strictEqual($(".o-Composer-input").val(), "");
    await insertText(".o-Composer-input", "#");
    assert.containsOnce($, ".o-composer-suggestion");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        $(".o-Composer-input").val().replace(/\s/, " "),
        "#General ",
        "previous content + mentioned channel + additional whitespace afterwards"
    );

    // select emoji
    await click("button[aria-label='Emojis']");
    await click(".o-Emoji:contains(😊)");
    assert.strictEqual($(".o-Composer-input").val().replace(/\s/, " "), "#General 😊");
});

QUnit.test(
    'do not post message on channel with "SHIFT-Enter" keyboard shortcut',
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "general" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsNone($, ".o-Message");

        await insertText(".o-Composer-input", "Test");
        await triggerHotkey("shift+Enter");
        await nextTick();
        assert.containsNone($, ".o-Message");
    }
);

QUnit.test('post message on channel with "Enter" keyboard shortcut', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsNone($, ".o-Message");

    // insert some HTML in editable
    await insertText(".o-Composer-input", "Test");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce($, ".o-Message");
});

QUnit.test("leave command on channel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => {
                assert.step(message);
            }),
        },
    });
    await openDiscuss(channelId);
    assert.hasClass($(".o-DiscussCategoryItem:contains(general)"), "o-active");
    await insertText(".o-Composer-input", "/leave");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsNone($, ".o-DiscussCategoryItem:contains(general)");
    assert.containsOnce($, ".o-Discuss:contains(No conversation selected.)");
    assert.verifySteps(["You unsubscribed from general."]);
});

QUnit.test("leave command on chat", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Chuck Norris" });
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
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
    assert.hasClass($(".o-DiscussCategoryItem:contains(Chuck Norris)"), "o-active");
    await insertText(".o-Composer-input", "/leave");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsNone($, ".o-DiscussCategoryItem:contains(Chuck Norris)");
    assert.containsOnce($, ".o-Discuss:contains(No conversation selected.)");
    assert.verifySteps(["You unpinned your conversation with Chuck Norris"]);
});

QUnit.test("Can post suggestions", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    insertText(".o-Composer-input", "#");
    await nextTick();
    await insertText(".o-Composer-input", "general");
    // Close the popup.
    await afterNextRender(() => triggerHotkey("Enter"));
    // Send the message.
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce($, ".o-Message .o_channel_redirect");
});

QUnit.test(
    "composer text input placeholder should contain correspondent name when thread has exactly one correspondent",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
        const channelId = pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.hasAttrValue($(".o-Composer-input"), "placeholder", "Message Marc Demo…");
    }
);

QUnit.test("send message only once when enter is pressed twice quickly", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(channelId);
    // Type message
    await insertText(".o-Composer-input", "test message");
    triggerHotkey("Enter");
    triggerHotkey("Enter");
    await nextTick();
    assert.verifySteps(["message_post"], "The message has been posted only once");
});

QUnit.test("quick edit last self-message from UP arrow", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Test",
        attachment_ids: [],
        message_type: "comment",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message:contains(Test)");
    assert.containsNone($, ".o-Message:contains(Test) .o-Composer");

    await afterNextRender(() => triggerHotkey("ArrowUp"));
    assert.containsOnce($, ".o-Message .o-Composer");
});

QUnit.test("Select composer suggestion via Enter does not send the message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "shrek@odoo.com",
        name: "Shrek",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
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
    await insertText(".o-Composer-input", "@");
    await insertText(".o-Composer-input", "Shrek");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.equal($(".o-Composer-input").val().trim(), "@Shrek");
    assert.verifySteps([]);
});

QUnit.test("composer: drop attachments", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
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
    assert.containsNone($, ".o-Dropzone");
    assert.containsNone($, ".o-AttachmentCard");

    await afterNextRender(() => dragenterFiles($(".o-Composer-input")[0]));
    assert.containsOnce($, ".o-Dropzone");
    assert.containsNone($, ".o-AttachmentCard");

    await afterNextRender(() => dropFiles($(".o-Dropzone")[0], files));
    assert.containsNone($, ".o-Dropzone");
    assert.containsN($, ".o-AttachmentCard", 2);

    await afterNextRender(() => dragenterFiles($(".o-Composer-input")[0]));
    await afterNextRender(async () =>
        dropFiles($(".o-Dropzone")[0], [
            await createFile({
                content: "hello, world",
                contentType: "text/plain",
                name: "text3.txt",
            }),
        ])
    );
    assert.containsN($, ".o-AttachmentCard", 3);
});

QUnit.test("composer: add an attachment", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles($(".o-Composer-coreMain .o_input_file")[0], [file]);
    await waitUntil(".o-AttachmentCard .fa-check");

    assert.containsOnce($, ".o-Composer-footer .o-AttachmentList");
    assert.containsOnce($, ".o-Composer-footer .o-AttachmentList .o-AttachmentCard");
});

QUnit.test("composer: add an attachment in reply to message in history", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
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
    await click("i[aria-label='Reply']");
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles($(".o-Composer-coreMain .o_input_file")[0], [file]);
    await waitUntil(".o-AttachmentCard .fa-check");

    assert.containsOnce($, ".o-Composer-footer .o-AttachmentList");
    assert.containsOnce($, ".o-Composer-footer .o-AttachmentList .o-AttachmentCard");
});

QUnit.test(
    "composer: send button is disabled if attachment upload is not finished",
    async (assert) => {
        const pyEnv = await startServer();
        const attachmentUploadedPromise = makeDeferred();
        const channelId = pyEnv["mail.channel"].create({ name: "General" });
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
        inputFiles($(".o-Composer-coreMain .o_input_file")[0], [file]);
        await waitUntil(".o-AttachmentCard.o-isUploading");
        assert.containsOnce($, ".o-Composer-send");
        assert.ok($(".o-Composer-send")[0].attributes.disabled);

        // simulates attachment finishes uploading
        await afterNextRender(() => attachmentUploadedPromise.resolve());
        assert.containsOnce($, ".o-AttachmentCard");
        assert.containsNone($, ".o-AttachmentCard.o-isUploading");
        assert.containsOnce($, ".o-Composer-send");
        assert.notOk($(".o-Composer-send")[0].attributes.disabled);
    }
);

QUnit.test("remove an attachment from composer does not need any confirmation", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    inputFiles($(".o-Composer-coreMain .o_input_file")[0], [file]);
    await waitUntil(".o-AttachmentCard .fa-check");
    assert.containsOnce($, ".o-Composer-footer .o-AttachmentList");
    assert.containsOnce($, ".o-AttachmentList .o-AttachmentCard");

    await click(".o-AttachmentCard-unlink");
    assert.containsNone($, ".o-AttachmentList .o-AttachmentCard");
});

QUnit.test("composer: paste attachments", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ];
    assert.containsNone($, ".o-AttachmentList .o-AttachmentCard");

    await afterNextRender(() => pasteFiles($(".o-Composer-input")[0], files));
    assert.containsOnce($, ".o-AttachmentList .o-AttachmentCard");
});

QUnit.test("Replying on a channel should focus composer initially", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "general",
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
    assert.strictEqual(document.activeElement, $(".o-Composer-input")[0]);
});

QUnit.test("remove an uploading attachment", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
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
    inputFiles($(".o-Composer-coreMain .o_input_file")[0], [file]);
    await waitUntil(".o-AttachmentCard.o-isUploading");
    assert.containsOnce($, ".o-AttachmentCard.o-isUploading");

    await click(".o-AttachmentCard-unlink");
    assert.containsNone($, ".o-Composer .o-AttachmentCard");
});

QUnit.test(
    "Show a default status in the recipient status text when the thread doesn't have a name.",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const { openFormView } = await start();
        await openFormView("res.partner", partnerId);
        await click("button:contains(Send message)");
        assert.containsOnce($, ".o-Chatter:contains(To followers of:  this document)");
    }
);

QUnit.test("Show a thread name in the recipient status text.", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test name" });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click("button:contains(Send message)");
    assert.containsOnce($, '.o-Chatter:contains(To followers of:  "test name")');
});

QUnit.test(
    "Uploading multiple files in the composer create multiple temporary attachments",
    async (assert) => {
        const pyEnv = await startServer();
        // Promise to block attachment uploading
        const uploadPromise = makeDeferred();
        const channelId = pyEnv["mail.channel"].create({ name: "test" });
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
        inputFiles($(".o-Composer-coreMain .o_input_file")[0], [file1, file2]);
        await waitUntil(".o-AttachmentCard:contains(text1.txt)");
        await waitUntil(".o-AttachmentCard:contains(text2.txt)");
        assert.containsN($, ".o-AttachmentCard-aside div[title='Uploading']", 2);
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
        const channelId = pyEnv["mail.channel"].create({ name: "test" });
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
        inputFiles($(".o-Composer-coreMain .o_input_file")[0], [file1, file2]);
        await waitUntil(".o-AttachmentCard:contains(text1.txt)");
        await waitUntil(".o-AttachmentCard:contains(text2.txt)");
        await click(".o-AttachmentCard-unlink:eq(1)");

        // Simulates the completion of the upload of the first attachment
        await afterNextRender(() => uploadPromise.resolve());
        assert.containsOnce($, '.o-AttachmentCard:contains("text1.txt")');
    }
);

QUnit.test("Message is sent only once when pressing enter twice in a row", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "Hello World!");
    // Simulate user pressing enter twice in a row.
    await afterNextRender(async () => {
        triggerHotkey("Enter");
        await nextTick();
        triggerHotkey("Enter");
    });
    assert.containsOnce($, ".o-Message:contains(Hello World!)");
});
