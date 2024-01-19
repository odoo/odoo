/* @odoo-module */

import { rpc } from "@web/core/network/rpc";

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";

import { assertSteps, contains, focus, step } from "@web/../tests/utils";
import { cookie } from "@web/core/browser/cookie";

QUnit.module("thread service");

QUnit.test("new message from operator displays unread counter", async () => {
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
    cookie.set(
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
            init_messaging: true,
            failures: true, // called because mail/core/web is loaded in qunit bundle
            context: { is_for_livechat: true },
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

QUnit.test("focus on unread livechat marks it as read", async () => {
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
    cookie.set(
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
            init_messaging: true,
            failures: true, // called because mail/core/web is loaded in qunit bundle
            context: { is_for_livechat: true },
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
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "Are you there?" });
    await focus(".o-mail-Composer-input");
    await contains(".o-mail-Thread-newMessage", { count: 0 });
});
