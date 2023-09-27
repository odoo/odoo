/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";

import { click, contains } from "@web/../tests/utils";
import { cookie } from "@web/core/browser/cookie";

QUnit.module("livechat service");

QUnit.test("persisted session history", async () => {
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
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.adminPartnerId,
    });
    const [channelInfo] = pyEnv.mockServer._mockDiscussChannelChannelInfo([channelId]);
    cookie.set("im_livechat_session", JSON.stringify(channelInfo));
    pyEnv["mail.message"].create({
        author_id: pyEnv.adminPartnerId,
        body: "Old message in history",
        res_id: channelId,
        model: "discuss.channel",
        message_type: "comment",
    });
    start();
    await contains(".o-mail-Message-content", { text: "Old message in history" });
});

QUnit.test("previous operator prioritized", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultConfig();
    const userId = pyEnv["res.users"].create({ name: "John Doe", im_status: "online" });
    const previousOperatorId = pyEnv["res.partner"].create({ user_ids: [userId] });
    pyEnv["im_livechat.channel"].write([livechatChannelId], { user_ids: [Command.link(userId)] });
    cookie.set("im_livechat_previous_operator_pid", JSON.stringify(previousOperatorId));
    start();
    click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message-author", { text: "John Doe" });
});
