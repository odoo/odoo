/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("messaging");

QUnit.test("Receiving a new message out of discuss app should open a chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { env } = await start();
    // simulate receving new message
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-ChatWindow", { text: "Dumbledore" });
});

QUnit.test(
    "Receiving a new message in discuss app should open a chat window after leaving discuss app",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        const { env, openDiscuss, openFormView } = await start();
        await openDiscuss();
        // simulate receiving new message
        pyEnv.withUser(userId, () =>
            env.services.rpc("/mail/message/post", {
                post_data: { body: "new message", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        // leaving discuss.
        await openFormView("res.partner", partnerId);
        await contains(".o-mail-ChatWindow", { text: "Dumbledore" });
    }
);

QUnit.test(
    "Posting a message in discuss app should not open a chat window after leaving discuss app",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        });
        const { openDiscuss, openFormView } = await start();
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "test https://www.odoo.com/");
        await click(".o-mail-Composer-send:enabled");
        // leaving discuss.
        await openFormView("res.partner", partnerId);
        // weak test, no guarantee that we waited long enough for the potential chat window to open
        await contains(".o-mail-ChatWindow", { count: 0, text: "Dumbledore" });
    }
);
