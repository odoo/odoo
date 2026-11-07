/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("composer (patch)");

QUnit.test("Can execute help command on livechat channels", async (assert) => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start({
        mockRPC(route, args, originalMockRPC) {
            if (args.method === "execute_command_help") {
                assert.step("execute_command_help");
                return true;
            }
            return originalMockRPC(route, args);
        },
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/help");
    await click(".o-mail-Composer-send:enabled");
    assert.verifySteps(["execute_command_help"]);
});

QUnit.test('Receives visitor typing status "is typing"', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-Typing", { text: "" });
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    // simulate receive typing notification from livechat visitor "is typing"
    pyEnv.withGuest(guestId, () =>
        env.services.rpc("/im_livechat/notify_typing", {
            is_typing: true,
            uuid: channel.uuid,
        })
    );
    await contains(".o-discuss-Typing", { text: "Visitor 20 is typing..." });
});

QUnit.test('display canned response suggestions on typing ":"', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Mario",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-Composer-suggestionList .o-open");
});

QUnit.test("use a canned response", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Mario",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", ":");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "Hello! How are you? " });
});

QUnit.test("use a canned response some text", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Mario",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-suggestionList");
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "bluhbluh ");
    await contains(".o-mail-Composer-input", { value: "bluhbluh " });
    await insertText(".o-mail-Composer-input", ":");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-input", { value: "bluhbluh Hello! How are you? " });
});

QUnit.test("add an emoji after a canned response", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    const { openDiscuss } = await start();
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
