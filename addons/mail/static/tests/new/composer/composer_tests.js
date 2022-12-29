/** @odoo-module **/

import { file, makeTestPromise } from "web.test_utils";
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
} from "@mail/../tests/helpers/test_utils";

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
const { inputFiles } = file;

import { getFixture, nextTick, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { Composer } from "@mail/new/composer/composer";

let target;

QUnit.module("composer", {
    async beforeEach() {
        target = getFixture();
        // Simulate real user interactions
        patchWithCleanup(Composer.prototype, {
            isEventTrusted() {
                return true;
            },
        });
    },
});

QUnit.test("composer text input: basic rendering when posting a message", async function (assert) {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    await openFormView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
    });
    await click("button:contains(Send message)");
    assert.containsOnce(target, ".o-mail-composer");
    assert.containsOnce(target, "textarea.o-mail-composer-textarea");
    assert.hasAttrValue(
        target.querySelector(".o-mail-composer-textarea"),
        "placeholder",
        "Send a message to followers..."
    );
});

QUnit.test("composer text input: basic rendering when logging note", async function (assert) {
    const pyEnv = await startServer();
    const { openFormView } = await start();
    await openFormView({
        res_id: pyEnv.currentPartnerId,
        res_model: "res.partner",
    });
    await click("button:contains(Log note)");
    assert.containsOnce(target, ".o-mail-composer");
    assert.containsOnce(target, "textarea.o-mail-composer-textarea");
    assert.hasAttrValue(
        target.querySelector(".o-mail-composer-textarea"),
        "placeholder",
        "Log an internal note..."
    );
});

QUnit.test(
    "composer text input: basic rendering when linked thread is a mail.channel",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({ name: "dofus-disco" });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId1);
        assert.containsOnce(target, ".o-mail-composer");
        assert.containsOnce(target, "textarea.o-mail-composer-textarea");
    }
);

QUnit.test(
    "composer text input placeholder should contain channel name when thread does not have specific correspondent",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId1);
        assert.hasAttrValue(
            target.querySelector(".o-mail-composer-textarea"),
            "placeholder",
            "Message #General…"
        );
    }
);

QUnit.test("add an emoji", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "swamp-safari" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    await click("i[aria-label='Emojis']");
    await click(".o-emoji[data-codepoints='😤']");
    assert.strictEqual(target.querySelector(".o-mail-composer-textarea").value, "😤");
});

QUnit.test(
    "Exiting emoji picker brings the focus back to the Composer textarea",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({ name: "" });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId1);
        await click("i[aria-label='Emojis']");
        await afterNextRender(() => triggerHotkey("Escape"));
        assert.equal(target.querySelector(".o-mail-composer-textarea"), document.activeElement);
    }
);

QUnit.test("add an emoji after some text", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "beyblade-room" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    await insertText(".o-mail-composer-textarea", "Blabla");
    assert.strictEqual(target.querySelector(".o-mail-composer-textarea").value, "Blabla");

    await click("i[aria-label='Emojis']");
    await click(".o-emoji[data-codepoints='🤑']");
    assert.strictEqual(target.querySelector(".o-mail-composer-textarea").value, "Blabla🤑");
});

QUnit.test("add emoji replaces (keyboard) text selection", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    const composerTextInputTextArea = document.querySelector(".o-mail-composer-textarea");
    await insertText(".o-mail-composer-textarea", "Blabla");
    assert.strictEqual(composerTextInputTextArea.value, "Blabla");

    // simulate selection of all the content by keyboard
    composerTextInputTextArea.setSelectionRange(0, composerTextInputTextArea.value.length);
    await click("i[aria-label='Emojis']");
    await click('.o-emoji[data-codepoints="🤠"]');
    assert.strictEqual(document.querySelector(".o-mail-composer-textarea").value, "🤠");
});

QUnit.test("Cursor is positioned after emoji after adding it", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "pétanque-tournament-14" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    const composerTextInputTextArea = document.querySelector(".o-mail-composer-textarea");
    await insertText(".o-mail-composer-textarea", "Blabla");
    composerTextInputTextArea.setSelectionRange(2, 2);
    await click("i[aria-label='Emojis']");
    await click('.o-emoji[data-codepoints="🤠"]');
    const expectedCursorPos = 2 + "🤠".length;
    assert.strictEqual(composerTextInputTextArea.selectionStart, expectedCursorPos);
    assert.strictEqual(composerTextInputTextArea.selectionEnd, expectedCursorPos);
});

QUnit.test("selected text is not replaced after cancelling the selection", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({
        name: "pétanque-tournament-14",
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    const composerTextInputTextArea = document.querySelector(".o-mail-composer-textarea");
    await insertText(".o-mail-composer-textarea", "Blabla");
    assert.strictEqual(composerTextInputTextArea.value, "Blabla");

    // simulate selection of all the content by keyboard
    composerTextInputTextArea.setSelectionRange(0, composerTextInputTextArea.value.length);
    document.querySelector(".o-mail-discuss-content").click();
    await nextTick();
    await click("i[aria-label='Emojis']");
    await click('.o-emoji[data-codepoints="🤠"]');
    assert.strictEqual(document.querySelector(".o-mail-composer-textarea").value, "Blabla🤠");
});

QUnit.test(
    "Selection is kept when changing channel and going back to original channel",
    async (assert) => {
        const pyEnv = await startServer();
        const [firstChannelId] = pyEnv["mail.channel"].create([
            { name: "firstChannel" },
            { name: "secondChannel" },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss(firstChannelId);
        await insertText(".o-mail-composer-textarea", "Foo");
        // simulate selection of all the content by keyboard
        const composerTextArea = document.querySelector(".o-mail-composer-textarea");
        composerTextArea.setSelectionRange(0, composerTextArea.value.length);
        await nextTick();
        const [firstChannelBtn, secondChannelBtn] =
            document.querySelectorAll(".o-mail-category-item");
        await afterNextRender(() => secondChannelBtn.click());
        await afterNextRender(() => firstChannelBtn.click());
        assert.ok(
            composerTextArea.selectionStart === 0 &&
                composerTextArea.selectionEnd === composerTextArea.value.length,
            "Content of the text area should still be selected after switching channels"
        );
    }
);

QUnit.test(
    "click on emoji button, select emoji, then re-click on button should show emoji picker",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "roblox-skateboarding",
        });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId1);
        await click("i[aria-label='Emojis']");
        await click(".o-emoji[data-codepoints='👺']");
        await click("i[aria-label='Emojis']");
        assert.containsOnce(target, ".o-mail-emoji-picker");
    }
);

QUnit.test('do not send typing notification on typing "/" command', async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "channel" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/channel/notify_typing") {
                assert.step(`notify_typing:${args.is_typing}`);
            }
        },
    });
    await openDiscuss(mailChannelId1);
    await insertText(".o-mail-composer-textarea", "/");
    assert.verifySteps([], "No rpc done");
});

QUnit.test("composer text input cleared on message post", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "au-secours-aidez-moi" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(mailChannelId1);
    await insertText(".o-mail-composer-textarea", "test message");
    assert.strictEqual(document.querySelector(".o-mail-composer-textarea").value, "test message");

    await click(".o-mail-composer-send-button");
    assert.verifySteps(["message_post"]);
    assert.strictEqual(document.querySelector(".o-mail-composer-textarea").value, "");
});

QUnit.test(
    "send message only once when button send is clicked twice quickly",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({ name: "nether-picnic" });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/message/post") {
                    assert.step("message_post");
                }
            },
        });
        await openDiscuss(mailChannelId1);
        await insertText(".o-mail-composer-textarea", "test message");
        await afterNextRender(() => {
            target.querySelector(".o-mail-composer-send-button").click();
            target.querySelector(".o-mail-composer-send-button").click();
        });
        assert.verifySteps(["message_post"]);
    }
);

QUnit.test('send button on mail.channel should have "Send" as label', async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "minecraft-wii-u" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    assert.strictEqual(
        target.querySelector(".o-mail-composer-send-button").textContent.trim(),
        "Send"
    );
});

QUnit.test(
    "composer textarea content is retained when changing channel then going back",
    async function (assert) {
        const pyEnv = await startServer();
        const [mailChannelId1] = pyEnv["mail.channel"].create([
            { name: "minigolf-galaxy-iv" },
            { name: "epic-shrek-lovers" },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId1);
        await insertText(".o-mail-composer-textarea", "According to all known laws of aviation,");
        await click($(target).find("span:contains('epic-shrek-lovers')"));
        await click($(target).find("span:contains('minigolf-galaxy-iv')"));
        assert.strictEqual(
            target.querySelector(".o-mail-composer-textarea").value,
            "According to all known laws of aviation,"
        );
    }
);

QUnit.test(
    'do not send typing notification on typing after selecting suggestion from "/" command',
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({ name: "channel" });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/channel/notify_typing") {
                    assert.step(`notify_typing:${args.is_typing}`);
                }
            },
        });
        await openDiscuss(mailChannelId1);
        await insertText(".o-mail-composer-textarea", "/");
        await click(".o-composer-suggestion");
        await insertText(".o-mail-composer-textarea", " is user?");
        assert.verifySteps([], "No rpc done");
    }
);

QUnit.test("add an emoji after a command", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    assert.containsNone(target, ".o-composer-suggestion-list .o-open");
    assert.strictEqual(document.querySelector(".o-mail-composer-textarea").value, "");
    await insertText(".o-mail-composer-textarea", "/");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        document.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "/who ",
        "text content of composer should have previous content + used command + additional whitespace afterwards"
    );

    await click("i[aria-label='Emojis']");
    await click('.o-emoji[data-codepoints="😊"]');
    assert.strictEqual(
        document.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "/who 😊"
    );
});

QUnit.test("add an emoji after a canned response", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({
        name: "Mario Party",
    });
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    assert.containsNone(target, ".o-composer-suggestion");
    assert.strictEqual(target.querySelector(".o-mail-composer-textarea").value, "");
    await insertText(".o-mail-composer-textarea", ":");
    assert.containsOnce(target, ".o-composer-suggestion");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        target.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "Hello! How are you? ",
        "text content of composer should have previous content + canned response substitution + additional whitespace afterwards"
    );

    await click("i[aria-label='Emojis']");
    await click(".o-emoji[data-codepoints='😊']");
    assert.strictEqual(
        target.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "Hello! How are you? 😊"
    );
});

QUnit.test("add an emoji after a partner mention", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const mailChannelId1 = pyEnv["mail.channel"].create({
        name: "Mario Party",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    assert.containsNone(target, ".o-composer-suggestion");
    assert.strictEqual(target.querySelector(".o-mail-composer-textarea").value, "");
    await insertText(".o-mail-composer-textarea", "@");
    await insertText(".o-mail-composer-textarea", "T");
    await insertText(".o-mail-composer-textarea", "e");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        target.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "@TestPartner "
    );

    await click("i[aria-label='Emojis']");
    await click(".o-emoji[data-codepoints='😊']");
    assert.strictEqual(
        target.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "@TestPartner 😊"
    );
});

QUnit.test("mention a channel after some text", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    assert.containsNone(target, ".o-composer-suggestion");
    assert.strictEqual(target.querySelector(".o-mail-composer-textarea").value, "");
    await insertText(".o-mail-composer-textarea", "bluhbluh ");
    assert.strictEqual(
        target.querySelector(".o-mail-composer-textarea").value,
        "bluhbluh ",
        "text content of composer should have content"
    );
    await insertText(".o-mail-composer-textarea", "#");
    assert.containsOnce(target, ".o-composer-suggestion");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        target.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "bluhbluh #General ",
        "text content of composer should have previous content + mentioned channel + additional whitespace afterwards"
    );
});

QUnit.test("add an emoji after a channel mention", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    assert.containsNone(target, ".o-composer-suggestion");
    assert.strictEqual(target.querySelector(".o-mail-composer-textarea").value, "");
    await insertText(".o-mail-composer-textarea", "#");
    assert.containsOnce(document.body, ".o-composer-suggestion");
    await click(".o-composer-suggestion");
    assert.strictEqual(
        target.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "#General ",
        "text content of composer should have previous content + mentioned channel + additional whitespace afterwards"
    );

    // select emoji
    await click("i[aria-label='Emojis']");
    await click(".o-emoji[data-codepoints='😊']");
    assert.strictEqual(
        target.querySelector(".o-mail-composer-textarea").value.replace(/\s/, " "),
        "#General 😊"
    );
});

QUnit.test(
    'do not post message on channel with "SHIFT-Enter" keyboard shortcut',
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({ name: "general" });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId1);
        assert.containsNone(target, ".o-mail-message");

        await insertText(".o-mail-composer-textarea", "Test");
        await triggerHotkey("shift+Enter");
        await nextTick();
        assert.containsNone(target, ".o-mail-message");
    }
);

QUnit.test('post message on channel with "Enter" keyboard shortcut', async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    assert.containsNone(target, ".o-mail-message");

    // insert some HTML in editable
    await insertText(".o-mail-composer-textarea", "Test");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce(target, ".o-mail-message");
});

QUnit.test("leave command on channel", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => {
                assert.step(message);
            }),
        },
    });
    await openDiscuss(mailChannelId);
    assert.hasClass(
        $(target).find(`.o-mail-category-item[data-channel-id="${mailChannelId}"]`),
        "o-active"
    );
    await insertText(".o-mail-composer-textarea", "/leave");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsNone(target, `.o-mail-category-item[data-channel-id="${mailChannelId}"]`);
    assert.containsOnce(target, ".o-mail-discuss-no-thread");
    assert.verifySteps(["You unsubscribed from general."]);
});

QUnit.test("leave command on chat", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId = pyEnv["res.partner"].create({ name: "Chuck Norris" });
    const mailChannelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
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
    await openDiscuss(mailChannelId);
    assert.hasClass(
        $(target).find(`.o-mail-category-item[data-channel-id="${mailChannelId}"]`),
        "o-active"
    );
    await insertText(".o-mail-composer-textarea", "/leave");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsNone(target, `.o-mail-category-item[data-channel-id="${mailChannelId}"]`);
    assert.containsOnce(target, ".o-mail-discuss-no-thread");
    assert.verifySteps(["You unpinned your conversation with Chuck Norris"]);
});

QUnit.test("Can post suggestions", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    insertText(".o-mail-composer-textarea", "#");
    await nextTick();
    await insertText(".o-mail-composer-textarea", "general");
    // Close the popup.
    await afterNextRender(() => triggerHotkey("Enter"));
    // Send the message.
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce(target, ".o-mail-message .o_channel_redirect");
});

QUnit.test(
    "composer text input placeholder should contain correspondent name when thread has exactly one correspondent",
    async function (assert) {
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv["res.partner"].create({ name: "Marc Demo" });
        const mailChannelId1 = pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId1);
        assert.hasAttrValue(
            target.querySelector(".o-mail-composer-textarea"),
            "placeholder",
            "Message Marc Demo…"
        );
    }
);

QUnit.test("send message only once when enter is pressed twice quickly", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
            }
        },
    });
    await openDiscuss(mailChannelId1);
    // Type message
    await insertText(".o-mail-composer-textarea", "test message");
    triggerHotkey("Enter");
    triggerHotkey("Enter");
    await nextTick();
    assert.verifySteps(["message_post"], "The message has been posted only once");
});

QUnit.test("quick edit last self-message from UP arrow", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv["mail.channel"].create({ name: "general" });
    const mailMessageId = pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: "Test",
        attachment_ids: [],
        message_type: "comment",
        model: "mail.channel",
        res_id: mailChannelId1,
    });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId1);
    assert.containsOnce(target, `.o-mail-message[data-message-id=${mailMessageId}]`);
    assert.containsNone(
        target,
        `.o-mail-message[data-message-id=${mailMessageId}] .o-mail-composer`
    );

    await afterNextRender(() => triggerHotkey("ArrowUp"));
    assert.containsOnce(
        target,
        `.o-mail-message[data-message-id=${mailMessageId}] .o-mail-composer`
    );
});

QUnit.test(
    "Select composer suggestion via Enter does not send the message",
    async function (assert) {
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv["res.partner"].create({
            email: "shrek@odoo.com",
            name: "Shrek",
        });
        pyEnv["res.users"].create({ partner_id: resPartnerId1 });
        const mailChannelId1 = pyEnv["mail.channel"].create({
            name: "general",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
        });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/message/post") {
                    assert.step("message_post");
                }
            },
        });
        await openDiscuss(mailChannelId1);
        await insertText(".o-mail-composer-textarea", "@");
        await insertText(".o-mail-composer-textarea", "Shrek");
        await afterNextRender(() => triggerHotkey("Enter"));
        assert.equal(target.querySelector(".o-mail-composer-textarea").value.trim(), "@Shrek");
        assert.verifySteps([]);
    }
);

QUnit.test("composer: drop attachments", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
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
    assert.containsNone(target, ".o-dropzone");
    assert.containsNone(target, ".o-mail-attachment-card");

    await afterNextRender(() => dragenterFiles(target.querySelector(".o-mail-composer-textarea")));
    assert.containsOnce(target, ".o-dropzone");
    assert.containsNone(target, ".o-mail-attachment-card");

    await afterNextRender(() => dropFiles(target.querySelector(".o-dropzone"), files));
    assert.containsNone(target, ".o-dropzone");
    assert.containsN(target, ".o-mail-attachment-card", 2);

    await afterNextRender(() => dragenterFiles(target.querySelector(".o-mail-composer-textarea")));
    await afterNextRender(async () =>
        dropFiles(target.querySelector(".o-dropzone"), [
            await createFile({
                content: "hello, world",
                contentType: "text/plain",
                name: "text3.txt",
            }),
        ])
    );
    assert.containsN(document.body, ".o-mail-attachment-card", 3);
});

QUnit.test("composer: add an attachment", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    await afterNextRender(() =>
        inputFiles(target.querySelector(".o-mail-composer-core-main .o_input_file"), [file])
    );
    assert.containsOnce(target, ".o-mail-composer-footer .o-mail-attachment-list");
    assert.containsOnce(
        target,
        ".o-mail-composer-footer .o-mail-attachment-list .o-mail-attachment-card"
    );
});

QUnit.test("composer: add an attachment in reply to message in history", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId = pyEnv["mail.channel"].create({ name: "General" });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
        history_partner_ids: [pyEnv.currentPartnerId],
        res_id: mailChannelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
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
    await afterNextRender(() =>
        inputFiles(target.querySelector(".o-mail-composer-core-main .o_input_file"), [file])
    );
    assert.containsOnce(target, ".o-mail-composer-footer .o-mail-attachment-list");
    assert.containsOnce(
        target,
        ".o-mail-composer-footer .o-mail-attachment-list .o-mail-attachment-card"
    );
});

QUnit.skipRefactoring(
    "composer: send button is disabled if attachment upload is not finished",
    // FIXME: upload uses XHR, so not properly testable.
    async function (assert) {
        const pyEnv = await startServer();
        const attachmentUploadedPromise = makeTestPromise();
        const mailChannelId = pyEnv["mail.channel"].create({ name: "General" });
        const { openDiscuss } = await start({
            async mockRPC(route) {
                if (route === "/mail/attachment/upload") {
                    await attachmentUploadedPromise;
                }
            },
        });
        await openDiscuss(mailChannelId);
        const file = await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        });
        await afterNextRender(() =>
            inputFiles(target.querySelector(".o-mail-composer-core-main .o_input_file"), [file])
        );
        assert.containsOnce(target, ".o-mail-attachment-card");
        assert.containsOnce(target, ".o-mail-attachment-card.o-mail-is-uploading");
        assert.containsOnce(target, ".o-mail-composer-send-button");
        assert.ok(target.querySelector(".o-mail-composer-send-button").attributes.disabled);

        // simulates attachment finishes uploading
        await afterNextRender(() => attachmentUploadedPromise.resolve());
        assert.containsOnce(target, ".o-mail-attachment-card");
        assert.containsNone(target, ".o-mail-attachment-card.o-mail-is-uploading");
        assert.containsOnce(target, ".o-mail-composer-send-button");
        assert.notOk(target.querySelector(".o-mail-composer-send-button").attributes.disabled);
    }
);

QUnit.test(
    "remove an attachment from composer does not need any confirmation",
    async function (assert) {
        const pyEnv = await startServer();
        const mailChannelId = pyEnv["mail.channel"].create({ name: "General" });
        const { openDiscuss } = await start();
        await openDiscuss(mailChannelId);
        const file = await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        });
        await afterNextRender(() =>
            inputFiles(document.querySelector(".o-mail-composer-core-main .o_input_file"), [file])
        );
        await nextTick(); // wait for uploading
        assert.containsOnce(target, ".o-mail-composer-footer .o-mail-attachment-list");
        assert.containsOnce(target, ".o-mail-attachment-list .o-mail-attachment-card");

        await click(".o-mail-attachment-card-aside-unlink");
        assert.containsNone(target, ".o-mail-attachment-list .o-mail-attachment-card");
    }
);

QUnit.test("composer: paste attachments", async function (assert) {
    const pyEnv = await startServer();
    const mailChannelId = pyEnv["mail.channel"].create({ name: "test" });
    const { openDiscuss } = await start();
    await openDiscuss(mailChannelId);
    const files = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
    ];
    assert.containsNone(target, ".o-mail-attachment-list .o-mail-attachment-card");

    await afterNextRender(() =>
        pasteFiles(target.querySelector(".o-mail-composer-textarea"), files)
    );
    assert.containsOnce(target, ".o-mail-attachment-list .o-mail-attachment-card");
});

QUnit.test("Replying on a channel should focus composer initially", async function (assert) {
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
    assert.strictEqual(document.activeElement, target.querySelector(".o-mail-composer-textarea"));
});
