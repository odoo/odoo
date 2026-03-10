import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { openClosePersistedChannel } from "./im_livechat_embed_shared_tests";

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

test("open/close persisted channel", openClosePersistedChannel);

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

test("can start a new live chat when acting as an agent in active live chats", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    setupChatHub({ opened: [channelId] });
    await start();
    await contains(".o-mail-ChatWindow");
    await contains(".o-livechat-LivechatButton");
});
