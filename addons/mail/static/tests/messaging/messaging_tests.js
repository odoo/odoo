/** @odoo-module **/

import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { Command } from "@mail/../tests/helpers/command";

QUnit.module("messaging");

QUnit.test(
    "Receiving a new message out of discuss app should open a chat window",
    async (assert) => {
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
        await afterNextRender(() =>
            env.services.rpc("/mail/message/post", {
                context: { mockedUserId: userId },
                post_data: { body: "new message", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
        assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Dumbledore)");
    }
);

QUnit.test(
    "Receiving a new message in discuss app should open a chat window after leaving discuss app",
    async (assert) => {
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
        env.services.rpc("/mail/message/post", {
            context: { mockedUserId: userId },
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        });
        // leaving discuss.
        await openFormView("res.partner", partnerId);
        assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Dumbledore)");
    }
);

QUnit.test(
    "Posting a message in discuss app should not open a chat window after leaving discuss app",
    async (assert) => {
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
        await click(".o-mail-Composer-send");
        // leaving discuss.
        await openFormView("res.partner", partnerId);
        assert.containsNone($, ".o-mail-ChatWindow-header:contains(Dumbledore)");
    }
);
