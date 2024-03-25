/* @odoo-module */

import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";
import { Command } from "@mail/../tests/helpers/command";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { rpc } from "@web/core/network/rpc";
import { contains } from "@web/../tests/utils";

QUnit.module("out of focus");

QUnit.test("Spaces in notifications are not encoded", async () => {
    const pyEnv = await startServer();
    const bobUserId = pyEnv["res.users"].create({ name: "bob" });
    const bobPartnerId = pyEnv["res.partner"].create({ name: "bob", user_ids: [bobUserId] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
    });
    const { openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    await openDiscuss();
    pyEnv.withUser(bobUserId, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello world!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o_notification:has(.o_notification_bar.bg-info)", { text: "Hello world!" });
});
