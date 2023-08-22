/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";

import { Command } from "@mail/../tests/helpers/command";
import { contains, start } from "@mail/../tests/helpers/test_utils";

QUnit.module("messaging service (patch)");

QUnit.test("Notify message received out of focus", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Livechat 1",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.adminPartnerId }),
            Command.create({ partner_id: pyEnv.publicPartnerId }),
        ],
    });
    const [channel] = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
    const { env } = await start({
        services: {
            presence: makeFakePresenceService({
                isOdooFocused() {
                    return false;
                },
            }),
        },
    });
    await pyEnv.withUser(pyEnv.publicUserId, () =>
        env.services.rpc("/im_livechat/chat_post", {
            message_content: "Hello",
            uuid: channel.uuid,
        })
    );
    await contains(".o_notification.border-info:contains(New message):contains(Hello)");
});
