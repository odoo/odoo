/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

QUnit.module("thread_icon");

QUnit.test("thread icon of a chat when correspondent is on leave & online", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        im_status: "leave_online",
        name: "Demo",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        $,
        ".o-mail-DiscussSidebarChannel:contains(Demo) .o-mail-ThreadIcon .fa-plane[title='Online']"
    );
});

QUnit.test("thread icon of a chat when correspondent is on leave & away", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        im_status: "leave_away",
        name: "Demo",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        $,
        ".o-mail-DiscussSidebarChannel:contains(Demo) .o-mail-ThreadIcon .fa-plane[title='Away']"
    );
});

QUnit.test("thread icon of a chat when correspondent is on leave & offline", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        im_status: "leave_offline",
        name: "Demo",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        $,
        ".o-mail-DiscussSidebarChannel:contains(Demo) .o-mail-ThreadIcon .fa-plane[title='Out of office']"
    );
});
