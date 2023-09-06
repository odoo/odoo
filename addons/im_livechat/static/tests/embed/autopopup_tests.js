/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start, setCookie, loadDefaultConfig } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";
import { contains } from "@mail/../tests/helpers/test_utils";

QUnit.module("autopopup");

QUnit.test("persisted session", async () => {
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
    setCookie("im_livechat_session", JSON.stringify(channelInfo));
    start();
    await contains(".o-mail-ChatWindow");
});

QUnit.test("rule received in init", async () => {
    await startServer();
    await loadDefaultConfig();
    start({
        mockRPC(route) {
            if (route === "/im_livechat/init") {
                return {
                    available_for_me: true,
                    rule: { action: "auto_popup", auto_popup_delay: 0 },
                };
            }
        },
    });
    await contains(".o-mail-ChatWindow");
});
