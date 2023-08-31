/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { click, contains, start } from "@mail/../tests/helpers/test_utils";

QUnit.module("Thread model");

QUnit.test("Thread name unchanged when inviting new users", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #20",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: pyEnv.publicPartnerId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss-threadName[title='Visitor #20']");
    await click("button[title='Add Users']");
    await click(".o-discuss-ChannelInvitation-selectable:contains(James) input");
    await click("button:contains(Invite):not(:disabled)");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await click("button[title='Show Member List']");
    await contains(".o-discuss-ChannelMember", { text: "James" });
    await contains(".o-mail-Discuss-threadName[title='Visitor #20']");
});
