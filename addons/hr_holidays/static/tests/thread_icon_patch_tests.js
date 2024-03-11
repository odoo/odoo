/* @odoo-module */

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { openDiscuss, start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("thread_icon");

QUnit.test("thread icon of a chat when correspondent is on leave & online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        im_status: "leave_online",
        name: "Demo",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [".o-mail-ThreadIcon .fa-plane[title='Online']"],
        text: "Demo",
    });
});

QUnit.test("thread icon of a chat when correspondent is on leave & away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        im_status: "leave_away",
        name: "Demo",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [".o-mail-ThreadIcon .fa-plane[title='Away']"],
        text: "Demo",
    });
});

QUnit.test("thread icon of a chat when correspondent is on leave & offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        im_status: "leave_offline",
        name: "Demo",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [".o-mail-ThreadIcon .fa-plane[title='Out of office']"],
        text: "Demo",
    });
});
