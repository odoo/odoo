import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
    postLivechatMessage,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    assertChatHub,
    click,
    contains,
    focus,
    onRpcBefore,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { getService, serverState, withUser } from "@web/../tests/web_test_helpers";

import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { queryFirst, waitFor, waitForNone } from "@odoo/hoot-dom";
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
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await postLivechatMessage("Hello World!");
    await contains(".o_notification", {
        text: "No available collaborator, please try again later.",
    });
    await waitFor(".o-livechat-LivechatButton:count(1)");
    await advanceTime(LivechatButton.DEBOUNCE_DELAY + 10);
    await click(".o-livechat-LivechatButton");
    await waitFor(".o-mail-ChatWindow:count(1)");
});

test("Fold state is saved", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await waitFor(".o-mail-Thread:count(1)");
    const subscribed = waitUntilSubscribe();
    await postLivechatMessage("Hello World!");
    await subscribed;
    await waitFor(".o-mail-Thread:not([data-transient]):count(1)");
    assertChatHub({ opened: [1] });
    await click(".o-mail-ChatWindow-header");
    await waitForNone(".o-mail-Thread");
    assertChatHub({ folded: [1] });
    await click(".o-mail-ChatBubble");
    assertChatHub({ opened: [1] });
});

test.tags("focus required");
test("Seen message is saved on the server", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const userId = serverState.userId;
    await start({ authenticateAs: false, waitUntilSubscribe: false });
    await click(".o-livechat-LivechatButton");
    await waitFor(".o-mail-Thread:count(1)");
    const subscribed = waitUntilSubscribe();
    await postLivechatMessage("Hello, I need help!");
    await subscribed;
    await contains(".o-mail-Message", { text: "Hello, I need help!" });
    const initialSeenMessageId = [
        ...getService("mail.store")["discuss.channel"].records.values(),
    ].at(-1).self_member_id.seen_message_id?.id;
    queryFirst(".o-mail-Composer-html").blur();
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hello World!",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: [...getService("mail.store")["mail.thread"].records.values()].at(-1).id,
            thread_model: "discuss.channel",
        })
    );
    await waitFor(".o-mail-Thread-newMessage:count(1)");
    await contains(".o-mail-ChatWindow-counter", { text: "1" });
    await focus(".o-mail-Composer-html");
    await waitForNone(".o-mail-ChatWindow-counter");
    const guestId = pyEnv.cookie.get("dgid");
    const [member] = pyEnv["discuss.channel.member"].search_read([
        ["guest_id", "=", guestId],
        [
            "channel_id",
            "=",
            [...getService("mail.store")["mail.thread"].records.values()].at(-1).id,
        ],
    ]);
    expect(initialSeenMessageId).not.toBe(member.seen_message_id[0]);
    expect(
        [...getService("mail.store")["discuss.channel"].records.values()].at(-1).self_member_id
            .seen_message_id.id
    ).toBe(member.seen_message_id[0]);
});
