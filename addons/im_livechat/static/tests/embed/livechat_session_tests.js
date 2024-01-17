/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";

import { mockTimeout, triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";
import { rpc } from "@web/core/network/rpc";

QUnit.module("livechat session");

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
    await contains(".o_notification", {
        text: "No available collaborator, please try again later.",
    });
    await contains(".o-livechat-LivechatButton");
    await advanceTime(LivechatButton.DEBOUNCE_DELAY + 10);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
});

QUnit.test("Fold state is saved on the server", async (assert) => {
    const pyEnv = await startServer();
    await loadDefaultConfig();
    const env = await start();
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Thread");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello World!" });
    let [member] = pyEnv["discuss.channel.member"].searchRead([
        ["guest_id", "=", pyEnv.currentGuest.id],
        ["channel_id", "=", env.services["im_livechat.livechat"].thread.id],
    ]);
    assert.strictEqual(member.fold_state, "open");
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-Thread", { count: 0 });
    [member] = pyEnv["discuss.channel.member"].searchRead([
        ["guest_id", "=", pyEnv.currentGuest.id],
        ["channel_id", "=", env.services["im_livechat.livechat"].thread.id],
    ]);
    assert.strictEqual(member.fold_state, "folded");
    await click(".o-mail-ChatWindow-header");
});

QUnit.test("Seen message is saved on the server", async (assert) => {
    const pyEnv = await startServer();
    await loadDefaultConfig();
    const env = await start();
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Thread");
    await insertText(".o-mail-Composer-input", "Hello, I need help!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello, I need help!" });
    const initialSeenMessageId = env.services["im_livechat.livechat"].thread.seen_message_id;
    $(".o-mail-Composer-input").blur();
    await pyEnv.withUser(pyEnv.adminUserId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hello World!",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: env.services["im_livechat.livechat"].thread.id,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread-newMessage");
    await contains(".o-mail-Composer-input", { setFocus: true });
    await contains(".o-mail-Thread-newMessage", { count: 0 });
    const [member] = pyEnv["discuss.channel.member"].searchRead([
        ["guest_id", "=", pyEnv.currentGuest.id],
        ["channel_id", "=", env.services["im_livechat.livechat"].thread.id],
    ]);
    assert.notEqual(initialSeenMessageId, member.seen_message_id[0]);
    assert.strictEqual(
        env.services["im_livechat.livechat"].thread.seen_message_id,
        member.seen_message_id[0]
    );
});
