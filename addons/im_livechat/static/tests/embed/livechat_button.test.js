import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    insertText,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { asyncStep, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("open/close temporary channel", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    const env = await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await contains(".o-livechat-LivechatButton", { count: 0 });
    expect(Boolean(env.services["im_livechat.livechat"].thread)).toBe(true);
    await click("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    expect(Boolean(env.services["im_livechat.livechat"].thread)).toBe(false);
    await contains(".o-livechat-LivechatButton", { count: 1 });
});

test("open/close persisted channel", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpc("/im_livechat/get_session", async (req) => {
        const { params } = await req.json();
        if (params.persisted) {
            step("persisted");
        }
    });
    const env = await start({ authenticateAs: false });
    env.services.bus_service.subscribe("discuss.channel/new_message", () =>
        asyncStep("discuss.channel/new_message")
    );
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "How can I help?");
    await triggerHotkey("Enter");
    await assertSteps(["persisted"]);
    await contains(".o-mail-Message-content", { text: "How can I help?" });
    await assertSteps(["discuss.channel/new_message"]);
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
    onRpc("/im_livechat/init", () => ({ available_for_me: false }));
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await contains(".o-mail-ChatHub");
    await contains(".o-livechat-LivechatButton", { count: 0 });
});

test("clicking on notification opens the chat", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpc("/im_livechat/init", () => ({
        available_for_me: true,
        rule: { action: "display_button_and_text" },
    }));
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton-notification", {
        text: "Have a Question? Chat with us.",
    });
    await contains(".o-mail-ChatWindow");
});
