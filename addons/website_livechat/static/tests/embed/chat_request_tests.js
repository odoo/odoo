/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start, loadDefaultConfig } from "@im_livechat/../tests/embed/helper/test_utils";

import { Command } from "@mail/../tests/helpers/command";

import { session } from "@web/session";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("chat request");

QUnit.test("chat request opens chat window", async (assert) => {
    const pyEnv = await startServer();
    const livechatId = await loadDefaultConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv.cookie.set("dgid", guestId);
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.adminPartnerId }),
            Command.create({ guest_id: guestId, fold_state: "open" }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatId,
        livechat_operator_id: pyEnv.adminPartnerId,
    });
    const [channel] = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
    patchWithCleanup(session.livechatData, {
        options: {
            ...session.livechatData.options,
            force_thread: { id: channel.id, model: "discuss.channel" },
        },
    });
    await start();
    assert.containsOnce($, ".o-mail-ChatWindow");
});
