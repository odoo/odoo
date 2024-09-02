import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    focus,
    insertText,
    onRpcBefore,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import {
    getService,
    mountWithCleanup,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";

import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineLivechatModels();

test("Session is reset after failing to persist the channel", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore("/im_livechat/get_session", (args) => {
        if (args.persisted) {
            return false;
        }
    });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
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

test("Fold state is saved on the server", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Thread");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello World!" });
    const guestId = pyEnv.cookie.get("dgid");
    let [member] = pyEnv["discuss.channel.member"].search_read([
        ["guest_id", "=", guestId],
        ["channel_id", "=", getService("im_livechat.livechat").thread.id],
    ]);
    expect(member.fold_state).toBe("open");
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-Thread", { count: 0 });
    [member] = pyEnv["discuss.channel.member"].search_read([
        ["guest_id", "=", guestId],
        ["channel_id", "=", getService("im_livechat.livechat").thread.id],
    ]);
    expect(member.fold_state).toBe("folded");
    await click(".o-mail-ChatBubble");
});

test("Seen message is saved on the server [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const userId = serverState.userId;
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Thread");
    await insertText(".o-mail-Composer-input", "Hello, I need help!");
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello, I need help!" });
    await waitUntilSubscribe();
    const initialSeenMessageId =
        getService("im_livechat.livechat").thread.selfMember.seen_message_id?.id;
    $(".o-mail-Composer-input").blur();
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hello World!",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: getService("im_livechat.livechat").thread.id,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread-newMessage");
    await contains(".o-mail-ChatWindow-counter", { text: "1" });
    await focus(".o-mail-Composer-input");
    await contains(".o-mail-ChatWindow-counter", { count: 0 });
    const guestId = pyEnv.cookie.get("dgid");
    const [member] = pyEnv["discuss.channel.member"].search_read([
        ["guest_id", "=", guestId],
        ["channel_id", "=", getService("im_livechat.livechat").thread.id],
    ]);
    expect(initialSeenMessageId).not.toBe(member.seen_message_id[0]);
    expect(getService("im_livechat.livechat").thread.selfMember.seen_message_id.id).toBe(
        member.seen_message_id[0]
    );
});
