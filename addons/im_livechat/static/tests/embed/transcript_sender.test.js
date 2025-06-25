import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    insertText,
    onRpcBefore,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("send", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore("/im_livechat/email_livechat_transcript", (args) =>
        step(`send_transcript - ${args.email}`)
    );
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await click(".o-livechat-CloseConfirmation-leave");
    await contains(".form-text", { text: "Receive a copy of this conversation." });
    await contains("button[data-action='sendTranscript']:disabled");
    await insertText("input[placeholder='mail@example.com']", "odoobot@odoo.com");
    await click("button[data-action='sendTranscript']:enabled");
    await contains(".form-text", { text: "The conversation was sent." });
    await assertSteps(["send_transcript - odoobot@odoo.com"]);
});

test("send failed", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpc("/im_livechat/email_livechat_transcript", () => {
        throw new Error();
    });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await click(".o-mail-ChatWindow-command[title*='Close']");
    await click(".o-livechat-CloseConfirmation-leave");
    await insertText("input[placeholder='mail@example.com']", "odoobot@odoo.com");
    await click("button[data-action='sendTranscript']:enabled");
    await contains(".form-text", { text: "An error occurred. Please try again." });
});
