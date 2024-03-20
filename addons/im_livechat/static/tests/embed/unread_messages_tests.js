const test = QUnit.test; // QUnit.test()

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";
import { waitUntilSubscribe } from "@bus/../tests/helpers/websocket_event_deferred";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";

import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, focus, insertText, step } from "@web/../tests/utils";

QUnit.module("thread service");

test("new message from operator displays unread counter", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv.cookie.set("dgid", guestId);
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.adminPartnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_active: true,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.adminPartnerId,
    });
    browser.localStorage.setItem(
        "im_livechat.saved_state",
        JSON.stringify({ threadData: { id: channelId, model: "discuss.channel" }, persisted: true })
    );
    await start({
        async mockRPC(route, args, originalRpc) {
            if (route === "/mail/action" && args.init_messaging) {
                const res = await originalRpc(...arguments);
                step(`/mail/action - ${JSON.stringify(args)}`);
                return res;
            }
        },
    });
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {
                channel_types: ["livechat"],
            },
            failures: true, // called because mail/core/web is loaded in qunit bundle
            systray_get_activities: true, // called because mail/core/web is loaded in qunit bundle
            context: { lang: "en", tz: "taht", uid: serverState.userId },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    pyEnv.withUser(pyEnv.adminUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Are you there?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow-counter", { text: "1" });
});

test("focus on unread livechat marks it as read", async () => {
    const pyEnv = await startServer();
    await loadDefaultConfig();
    await start({
        async mockRPC(route, args, originalRpc) {
            if (route === "/mail/action" && args.init_messaging) {
                const res = await originalRpc(...arguments);
                step(`/mail/action - ${JSON.stringify(args)}`);
                return res;
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await insertText(".o-mail-Composer-input", "Hello World!");
    await triggerHotkey("Enter");
    // Wait for bus subscription to be done after persisting the thread:
    // presence of the message is not enough (temporary message).
    await waitUntilSubscribe();
    await contains(".o-mail-Message-content", { text: "Hello World!" });
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {
                channel_types: ["livechat"],
            },
            failures: true, // called because mail/core/web is loaded in qunit bundle
            systray_get_activities: true, // called because mail/core/web is loaded in qunit bundle
            context: { lang: "en", tz: "taht", uid: serverState.userId },
        })}`,
    ]);
    $(".o-mail-Composer-input").blur();
    const [channelId] = pyEnv["discuss.channel"].search([
        ["channel_type", "=", "livechat"],
        [
            "channel_member_ids",
            "in",
            pyEnv["discuss.channel.member"].search([["guest_id", "=", pyEnv.currentGuest.id]]),
        ],
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    pyEnv.withUser(pyEnv.adminUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Are you there?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "Are you there?" });
    await focus(".o-mail-Composer-input");
    await contains(".o-mail-Thread-newMessage", { count: 0 });
});
