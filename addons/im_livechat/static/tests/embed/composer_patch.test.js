import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { start, startServer } from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, onRpc, serverState } from "@web/../tests/web_test_helpers";

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
    await contains(".o-livechat-LivechatButton:count(1)").click();
    await waitFor(".o-mail-Message:has(:text('Tell us what you need.')):count(1)");
    await insertTextInComposer(".o-mail-Composer", "/help");
    await contains(".o-sendMessageActive:count(1)").click();
    await expect.waitForSteps(["execute_command_help"]);
    await waitFor(
        ".o-mail-Message-body:has(.o_mail_notification:contains('You are in a private conversation with')):count(1)"
    );
    await waitFor(".o-mail-Composer-html[contenteditable='true']:count(1)");
});
