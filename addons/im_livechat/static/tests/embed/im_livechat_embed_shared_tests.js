import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import {
    loadDefaultEmbedConfig,
    postLivechatMessage,
} from "@im_livechat/../tests/livechat_test_helpers";

import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { expect } from "@odoo/hoot";
import { _makeUser, user } from "@web/core/user";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

export async function openClosePersistedChannel() {
    await startServer();
    await loadDefaultEmbedConfig();
    const env = await start({ authenticateAs: false, waitUntilSubscribe: false });
    patchWithCleanup(user, _makeUser({ user_companies: undefined }));
    env.services.bus_service.subscribe("discuss.channel/new_message", () =>
        expect.step("discuss.channel/new_message")
    );
    await click(".o-livechat-LivechatButton");
    const subscribed = waitUntilSubscribe();
    await postLivechatMessage("How can I help?");
    await subscribed;
    await contains(".o-mail-Thread:not([data-transient])");
    await contains(".o-mail-Message-content", { text: "How can I help?" });
    await expect.waitForSteps(["discuss.channel/new_message"]);
    await click("[title*='Close Chat Window']");
    await click(".o-livechat-CloseConfirmation-leave");
    // Leaving posts the "Visitor left the conversation." message: wait for its
    // bus notification so it does not race teardown as an unverified step.
    await expect.waitForSteps(["discuss.channel/new_message"]);
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
    await click("[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await contains(".o-livechat-LivechatButton", { count: 1 });
}
