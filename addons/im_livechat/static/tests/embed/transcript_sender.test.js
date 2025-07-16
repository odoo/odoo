import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    insertText,
    onRpcBefore,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("send", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore("/im_livechat/email_livechat_transcript", () => expect.step(`send_transcript`));
    const partnerId = pyEnv["res.partner"].create({ email: "paul@example.com", name: "Paul" });
    pyEnv["res.users"].create({ partner_id: partnerId, login: "paul", password: "paul" });
    await start({ authenticateAs: { login: "paul", password: "paul" } });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await click(".o-livechat-CloseConfirmation-leave");
    await contains(".form-text", { text: "Receive a copy of this conversation." });
    await contains("input", { value: "paul@example.com" });
    await click("button[data-action='sendTranscript']:enabled");
    await contains(".form-text", { text: "The conversation was sent." });
    await expect.waitForSteps(["send_transcript"]);
});

test("send failed", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    onRpc("/im_livechat/email_livechat_transcript", () => {
        throw new Error();
    });
    const partnerId = pyEnv["res.partner"].create({ email: "paul@example.com", name: "Paul" });
    pyEnv["res.users"].create({ partner_id: partnerId, login: "paul", password: "paul" });
    await start({ authenticateAs: { login: "paul", password: "paul" } });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await click(".o-livechat-CloseConfirmation-leave");
    await contains("input", { value: "paul@example.com" });
    await click("button[data-action='sendTranscript']:enabled");
    await contains(".form-text", { text: "An error occurred. Please try again." });
});
