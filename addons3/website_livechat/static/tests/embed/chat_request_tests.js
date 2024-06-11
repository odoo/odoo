/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start, loadDefaultConfig } from "@im_livechat/../tests/embed/helper/test_utils";

import { session } from "@web/session";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("chat request");

QUnit.test("chat request opens chat window", async (assert) => {
    const pyEnv = await startServer();
    const channelId = await loadDefaultConfig();
    const [channel] = pyEnv["im_livechat.channel"].searchRead([["id", "=", channelId]]);
    const [adminPartner] = pyEnv["res.partner"].searchRead([["id", "=", pyEnv.adminPartnerId]]);
    patchWithCleanup(session.livechatData, {
        options: {
            ...session.livechatData.options,
            chat_request_session: {
                folded: false,
                id: channel.id,
                operator_pid: [adminPartner.id, adminPartner.name],
                name: channel.name,
                uuid: channel.uuid,
                isChatRequest: true,
            },
        },
    });
    await start();
    assert.containsOnce($, ".o-mail-ChatWindow");
});
