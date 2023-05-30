/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, setCookie, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";
import { afterNextRender, waitUntil } from "@mail/../tests/helpers/test_utils";

QUnit.module("thread service");

QUnit.test("new message from operator displays unread counter", async (assert) => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: pyEnv.publicPartnerId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const [channelInfo] = pyEnv.mockServer._mockDiscussChannelChannelInfo([channelId]);
    setCookie("im_livechat_session", JSON.stringify(channelInfo));
    const env = await start();
    $(".o-mail-Composer-input").blur();
    await afterNextRender(() => {
        env.services.rpc("/mail/message/post", {
            context: { mockedUserId: pyEnv.currentUserId },
            post_data: { body: "Are you there?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
    });
    await waitUntil(".o-mail-ChatWindow-header:contains(1)");
    assert.containsOnce($, ".o-mail-ChatWindow-header:contains(1)");
});

QUnit.test("focus on unread livechat marks it as read", async (assert) => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: pyEnv.publicPartnerId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const [channelInfo] = pyEnv.mockServer._mockDiscussChannelChannelInfo([channelId]);
    setCookie("im_livechat_session", JSON.stringify(channelInfo));
    const env = await start();
    $(".o-mail-Composer-input").blur();
    await afterNextRender(() => {
        env.services.rpc("/mail/message/post", {
            context: { mockedUserId: pyEnv.currentUserId },
            post_data: { body: "Are you there?", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
    });
    await waitUntil(".o-mail-Thread-newMessage ~ .o-mail-Message:contains(Are you there?)");
    await afterNextRender(() => $(".o-mail-Composer-input").trigger("focus"));
    assert.containsNone($, ".o-mail-Thread-newMessage");
});
