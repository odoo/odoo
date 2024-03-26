import { waitNotifications } from "@bus/../tests/bus_test_helpers";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
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

describe.current.tags("desktop");
defineLivechatModels();

test("do not save fold state of temporary live chats", async () => {
    patchWithCleanup(LivechatButton, {
        DEBOUNCE_DELAY: 0,
    });
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore("/discuss/channel/fold", (args) => {
        step(`fold - ${args.state}`);
    });
    const env = await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await insertText(".o-mail-Composer-input", "Hello");
    await triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello" });
    await click(".o-mail-ChatWindow-header");
    await waitNotifications([env, "discuss.Thread/fold_state"]);
    await contains(".o-mail-Message", { text: "Hello", count: 0 });
    await assertSteps(["fold - folded"]);
    await click("[title='Close Chat Window']");
    await click("button", { text: "Close conversation" });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await click(".o-mail-ChatWindow-header");
    await assertSteps([]);
});
