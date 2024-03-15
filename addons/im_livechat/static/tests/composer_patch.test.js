import {
    assertSteps,
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { rpcWithEnv } from "@mail/utils/common/misc";
import { describe, test } from "@odoo/hoot";
import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;

describe.current.tags("desktop");
defineLivechatModels();

test("Can execute help command on livechat channels", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    onRpc("/web/dataset/call_kw/discuss.channel/execute_command_help", () => {
        step("execute_command_help");
        return true;
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/help");
    await click(".o-mail-Composer-send:enabled");
    await assertSteps(["execute_command_help"]);
});

test('Receives visitor typing status "is typing"', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    await openDiscuss(channelId);
    await contains(".o-discuss-Typing", { text: "" });
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    // simulate receive typing notification from livechat visitor "is typing"
    withGuest(guestId, () =>
        rpc("/im_livechat/notify_typing", {
            is_typing: true,
            channel_id: channel.id,
        })
    );
    await contains(".o-discuss-Typing", { text: "Visitor 20 is typing..." });
});

test('display canned response suggestions on typing ":"', async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Mario",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello! How are you?",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input");
    await contains(".o-mail-Composer-suggestionList .o-open", { count: 0 });
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-Composer-suggestionList .o-open");
});

test("use a canned response", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Mario",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    pyEnv["mail.shortcode"].create({
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

test("use a canned response some text", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Mario",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    pyEnv["mail.shortcode"].create({
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
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    pyEnv["mail.shortcode"].create({
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
