import { loadDefaultEmbedConfig } from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { expect } from "@odoo/hoot";
import { _makeUser, user } from "@web/core/user";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

export async function openClosePersistedChannel() {
    await startServer();
    await loadDefaultEmbedConfig();
    const env = await start({ authenticateAs: false });
    patchWithCleanup(user, _makeUser({ user_companies: undefined }));
    env.services.bus_service.subscribe("discuss.channel/new_message", () =>
        expect.step("discuss.channel/new_message")
    );
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "How can I help?");
    await triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await contains(".o-mail-Message-content", { text: "How can I help?" });
    await expect.waitForSteps(["discuss.channel/new_message"]);
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
    await click("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-livechat-LivechatButton", { count: 1 });
}
