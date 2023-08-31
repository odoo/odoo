/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, setCookie, start } from "@im_livechat/../tests/embed/helper/test_utils";
import { LivechatButton } from "@im_livechat/embed/core_ui/livechat_button";

import { Command } from "@mail/../tests/helpers/command";
import { click, contains, insertText } from "@mail/../tests/helpers/test_utils";

import { mockTimeout, triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("livechat session");

QUnit.test("Unsuccessful message post shows session expired", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.adminPartnerId }),
            Command.create({ partner_id: pyEnv.publicPartnerId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.adminPartnerId,
    });
    const [channelInfo] = pyEnv.mockServer._mockDiscussChannelChannelInfo([channelId]);
    setCookie("im_livechat_session", JSON.stringify(channelInfo));
    start({
        mockRPC(route) {
            if (route === "/im_livechat/chat_post") {
                return false;
            }
        },
    });
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o_notification_content", {
        text: "Session expired... Please refresh and try again.",
    });
    await contains(".o-mail-ChatWindow", { count: 0 });
});

QUnit.test("Session is reset after failing to persist the channel", async () => {
    await startServer();
    await loadDefaultConfig();
    const { advanceTime } = mockTimeout();
    start({
        mockRPC(route, args) {
            if (route === "/im_livechat/get_session" && args.persisted) {
                return false;
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o_notification_content", {
        text: "No available collaborator, please try again later.",
    });
    await contains(".o-livechat-LivechatButton");
    await advanceTime(LivechatButton.DEBOUNCE_DELAY + 10);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
});

QUnit.test("Thread state is saved on the session", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    const env = await start();
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-content");
    assert.strictEqual(env.services["im_livechat.livechat"].sessionCookie.state, "open");
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-ChatWindow-content", { count: 0 });
    assert.strictEqual(env.services["im_livechat.livechat"].sessionCookie.state, "folded");
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-ChatWindow-content");
    assert.strictEqual(env.services["im_livechat.livechat"].sessionCookie.state, "open");
});

QUnit.test("Seen message is saved on the session", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    const env = await start();
    await click(".o-livechat-LivechatButton");
    assert.notOk(env.services["im_livechat.livechat"].sessionCookie.seen_message_id);
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { count: 2 });
    assert.strictEqual(
        env.services["im_livechat.livechat"].sessionCookie.seen_message_id,
        env.services["im_livechat.livechat"].thread.newestMessage.id
    );
});
