/** @odoo-module */

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

QUnit.module("message (patch)");

QUnit.test("redirect to author (open profile) in livechat", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
    });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Message img[title='Open profile']");
});
