import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    assertSteps,
    click,
    contains,
    focus,
    insertText,
    onRpcBefore,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, mountWithCleanup, serverState, withUser } from "@web/../tests/web_test_helpers";

import { expirableStorage } from "@im_livechat/embed/common/expirable_storage";
import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { rpc } from "@web/core/network/rpc";
import { queryFirst } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineLivechatModels();

test("new message from operator displays unread counter", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_active: true,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    expirableStorage.setItem(
        "im_livechat.saved_state",
        JSON.stringify({
            store: { "discuss.channel": [{ id: channelId }] },
            persisted: true,
            livechatUserId: serverState.publicUserId,
        })
    );
    onRpcBefore("/mail/data", (args) => {
        if (args.init_messaging) {
            step(`/mail/data - ${JSON.stringify(args)}`);
        }
    });
    const userId = serverState.userId;
    await start({
        authenticateAs: { ...pyEnv["mail.guest"].read(guestId)[0], _name: "mail.guest" },
    });
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            init_messaging: {
                channel_types: ["livechat"],
            },
            failures: true, // called because mail/core/web is loaded in qunit bundle
            systray_get_activities: true, // called because mail/core/web is loaded in qunit bundle
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Are you there?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow-counter", { text: "1" });
});

test.tags("focus required");
test("focus on unread livechat marks it as read", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore("/mail/data", (args) => {
        if (args.init_messaging) {
            step(`/mail/data - ${JSON.stringify(args)}`);
        }
    });
    const userId = serverState.userId;
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await triggerHotkey("Enter");
    // Wait for bus subscription to be done after persisting the thread:
    // presence of the message is not enough (temporary message).
    await waitUntilSubscribe();
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            init_messaging: {
                channel_types: ["livechat"],
            },
            failures: true, // called because mail/core/web is loaded in qunit bundle
            systray_get_activities: true, // called because mail/core/web is loaded in qunit bundle
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    queryFirst(".o-mail-Composer-input").blur();
    const [channelId] = pyEnv["discuss.channel"].search([
        ["channel_type", "=", "livechat"],
        [
            "channel_member_ids",
            "in",
            pyEnv["discuss.channel.member"].search([["guest_id", "=", pyEnv.cookie.get("dgid")]]),
        ],
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    await withUser(userId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Are you there?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow-counter", { text: "1" });
    await contains(".o-mail-Message", { text: "Are you there?" });
    await focus(".o-mail-Composer-input");
    await contains(".o-mail-ChatWindow-counter", { count: 0 });
});
