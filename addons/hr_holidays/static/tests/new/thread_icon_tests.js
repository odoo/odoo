/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("thread_icon");

QUnit.test(
    "thread icon of a chat when correspondent is on leave & online",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            im_status: "leave_online",
            name: "Demo",
        });
        pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(
            document.body,
            ".o-mail-category-item:contains(Demo) .o-mail-chatwindow-icon .fa-plane[title='Online']"
        );
    }
);

QUnit.test("thread icon of a chat when correspondent is on leave & away", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        im_status: "leave_away",
        name: "Demo",
    });
    pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        document.body,
        ".o-mail-category-item:contains(Demo) .o-mail-chatwindow-icon .fa-plane[title='Away']"
    );
});

QUnit.test(
    "thread icon of a chat when correspondent is on leave & offline",
    async function (assert) {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            im_status: "leave_offline",
            name: "Demo",
        });
        pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce(
            document.body,
            ".o-mail-category-item:contains(Demo) .o-mail-chatwindow-icon .fa-plane[title='Out of office']"
        );
    }
);
