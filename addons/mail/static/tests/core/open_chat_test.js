/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("Open Chat test", {});

QUnit.test("openChat: display notification for partner without user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { env } = await start();
    await env.services["mail.thread"].openChat({ partnerId });
    await contains(".o_notification.border-info", {
        text: "You can only chat with partners that have a dedicated user.",
    });
});

QUnit.test("openChat: display notification for wrong user", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].create({});
    const { env } = await start();
    // userId not in the server data
    await env.services["mail.thread"].openChat({ userId: 4242 });
    await contains(".o_notification.border-warning", {
        text: "You can only chat with existing users.",
    });
});

QUnit.test("openChat: open new chat for user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { env } = await start();
    await contains(".o-mail-ChatWindowContainer");
    await contains(".o-mail-ChatWindow", { count: 0 });
    env.services["mail.thread"].openChat({ partnerId });
    await contains(".o-mail-ChatWindow");
});

QUnit.test("openChat: open existing chat for user [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                partner_id: pyEnv.currentPartnerId,
                fold_state: "open",
                is_minimized: true,
            }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { env } = await start();
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:not(:focus)");
    env.services["mail.thread"].openChat({ partnerId });
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:focus");
});
