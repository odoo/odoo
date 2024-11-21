import { waitNotifications } from "@bus/../tests/bus_test_helpers";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import {
    assertSteps,
    click,
    contains,
    inputFiles,
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
    patchWithCleanup(LivechatButton, { DEBOUNCE_DELAY: 0 });
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
    await click(".o-mail-ChatBubble");
    await click("[title*='Close Chat Window']");
    await assertSteps(["fold - open"]); // clicking close shows the feedback panel
    await click(".o-livechat-CloseConfirmation-leave");
    await click("button", { text: "Close conversation" });
    await assertSteps(["fold - closed"]);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await click(".o-mail-ChatWindow-header");
    await assertSteps([]);
});

test("internal users can upload file to temporary thread", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const [partnerUser] = pyEnv["res.users"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: partnerUser });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await contains(".o-mail-Composer");
    await contains("button[title='Attach files']");
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [file]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });
    await triggerHotkey("Enter");
    await contains(".o-mail-Message .o-mail-AttachmentCard", { text: "text.txt" });
});

test("Conversation name is operator livechat user name", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header", { text: "MitchellOp" });
});
