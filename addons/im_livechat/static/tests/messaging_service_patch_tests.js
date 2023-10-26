/* @odoo-module */

import { rpc } from "@web/core/network/rpc";

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("messaging service (patch)");

QUnit.test("Notify message received out of focus", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "Livechat 1",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.adminPartnerId }),
            Command.create({ guest_id: guestId }),
        ],
    });
    const [channel] = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
    await start({
        services: {
            presence: makeFakePresenceService({
                isOdooFocused() {
                    return false;
                },
            }),
        },
    });
    await pyEnv.withGuest(guestId, () =>
        rpc("/im_livechat/chat_post", {
            message_content: "Hello",
            uuid: channel.uuid,
        })
    );
    await contains(".o_notification:has(.o_notification_bar.bg-info)", { text: "Hello" });
});
