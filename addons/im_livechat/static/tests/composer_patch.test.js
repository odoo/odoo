import {
    assertSteps,
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";
import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

import { rpc } from "@web/core/network/rpc";

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
    await click(".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-send:enabled");
    await assertSteps(["execute_command_help"]);
});

test("Can execute bot command on livechat channels", async () => {
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
    const [, botId_2] = pyEnv["chatbot.script"].create([{ title: "bot1" }, { title: "bot2" }]);
    onRpc("/web/dataset/call_kw/discuss.channel/execute_command_bot", async (request) => {
        const { params } = await request.json();
        step(`execute_command_bot - ${params.kwargs.bot_id}`);
        return true;
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/bot");
    await click(".o-mail-Composer-suggestion");
    await contains(".o-mail-Composer-suggestion");
    await click(".o-mail-Composer-suggestion", { text: "bot1" });
    await contains(".o-mail-Composer-input", { value: "/bot bot1 " });
    await insertText(".o-mail-Composer-input", "/bot bot2", { replace: true });
    await click(".o-mail-Composer-suggestion", { text: "bot2" });
    await contains(".o-mail-Composer-input", { value: "/bot bot2 " });
    triggerHotkey("Enter");
    await assertSteps([`execute_command_bot - ${botId_2}`]);
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-Typing", { text: "" });
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    // simulate receive typing notification from livechat visitor "is typing"
    withGuest(guestId, () =>
        rpc("/discuss/channel/notify_typing", {
            is_typing: true,
            channel_id: channel.id,
        })
    );
    await contains(".o-discuss-Typing", { text: "Visitor 20 is typing..." });
});
