/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("channel member list");

QUnit.test("on leave members are categorised correctly in online/offline", async () => {
    const pyEnv = await startServer();
    const [partnerId1, partnerId2, partnerId3] = pyEnv["res.partner"].create([
        { name: "Online Partner", im_status: "online" },
        { name: "On Leave Online", im_status: "leave_online" },
        { name: "On Leave Idle", im_status: "leave_away" },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId1 }),
            Command.create({ partner_id: partnerId2 }),
            Command.create({ partner_id: partnerId3 }),
        ],
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMemberList h6", { text: "Online - 3" });
    await contains(".o-discuss-ChannelMemberList h6", { text: "Offline - 1" });
});
