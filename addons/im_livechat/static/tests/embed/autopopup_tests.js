/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start, setCookie, loadDefaultConfig } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";
import { waitUntil } from "@mail/../tests/helpers/test_utils";

import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("autopopup");

QUnit.test("persisted session", async (assert) => {
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
    await start();
    await waitUntil(".o-mail-ChatWindow");
    assert.containsOnce($, ".o-mail-ChatWindow");
});

QUnit.test("rule received in init", async (assert) => {
    await startServer();
    await loadDefaultConfig();
    await start({
        mockRPC(route) {
            if (route === "/im_livechat/init") {
                return {
                    available_for_me: true,
                    rule: { action: "auto_popup", auto_popup_delay: 0 },
                };
            }
        },
    });
    await nextTick();
    assert.containsOnce($, ".o-mail-ChatWindow");
});
