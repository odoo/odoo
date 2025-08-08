import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";
import { asyncStep, patchWithCleanup, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("open/close temporary channel", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await contains(".o-livechat-LivechatButton", { count: 0 });
    await click("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-livechat-LivechatButton", { count: 1 });
});

test("open/close persisted channel", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    const env = await start({ authenticateAs: false });
    env.services.bus_service.subscribe("discuss.channel/new_message", () =>
        asyncStep("discuss.channel/new_message")
    );
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "How can I help?");
    await triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await contains(".o-mail-Message-content", { text: "How can I help?" });
    await waitForSteps(["discuss.channel/new_message"]);
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
    await click("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-livechat-LivechatButton", { count: 1 });
});

test("livechat not available", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    patchWithCleanup(mailDataHelpers, {
        _process_request_for_all(store) {
            super._process_request_for_all(...arguments);
            store.add({ livechat_available: false });
        },
    });
    await start({ authenticateAs: false });
    await contains(".o-mail-ChatHub");
    await contains(".o-livechat-LivechatButton", { count: 0 });
});

test("clicking on notification opens the chat", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const btnAndTextRuleId = pyEnv["im_livechat.channel.rule"].create({
        action: "display_button_and_text",
    });
    patchWithCleanup(mailDataHelpers, {
        _process_request_for_all(store) {
            super._process_request_for_all(...arguments);
            store.add(pyEnv["im_livechat.channel.rule"].browse(btnAndTextRuleId), {
                action: "display_button_and_text",
            });
            store.add({ livechat_rule: btnAndTextRuleId });
        },
    });
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton-notification", {
        text: "Need help? Chat with us.",
    });
    await contains(".o-mail-ChatWindow");
});
