/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { openDiscuss, start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("thread");

QUnit.test("out of office message on direct chat with out of office partner", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        im_status: "leave_online",
        out_of_office_date_end: "2023-01-01",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".alert", { text: "Out of office until Jan 1, 2023" });
});
