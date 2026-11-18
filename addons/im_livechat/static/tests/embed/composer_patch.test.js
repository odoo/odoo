import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { click, contains, insertText, start, startServer } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { onRpc, serverState } from "@web/../tests/web_test_helpers";

defineLivechatModels();

test("Internal visitor can execute command while answering a chatbot", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const partnerId = pyEnv["res.partner"].create({ name: "Internal Visitor" });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        login: "visitor",
        password: "visitor",
        share: false,
    });
    const scriptId = pyEnv["chatbot.script"].create({
        operator_partner_id: serverState.odoobotId,
        title: "Bot",
    });
    pyEnv["chatbot.script.step"].create({
        chatbot_script_id: scriptId,
        message: "Tell us what you need.",
        sequence: 1,
        step_type: "free_input_single",
    });
    pyEnv["im_livechat.channel.rule"].create({
        channel_id: livechatChannelId,
        chatbot_script_id: scriptId,
    });
    onRpc("discuss.channel", "execute_command_help", () => {
        expect.step("execute_command_help");
    });
    await start({
        authenticateAs: { login: "visitor", password: "visitor" },
        waitUntilSubscribe: false,
    });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message:has(:text('Tell us what you need.'))");
    await insertText(".o-mail-Composer-input", "/help");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await expect.waitForSteps(["execute_command_help"]);
    await contains(
        ".o-mail-Message-body:has(.o_mail_notification:contains('You are in a private conversation with'))"
    );
    await contains(".o-mail-Composer-input:enabled");
});
