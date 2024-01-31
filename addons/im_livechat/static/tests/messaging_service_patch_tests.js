/* @odoo-module */

import { rpc } from "@web/core/network/rpc";

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { assertSteps, contains, step } from "@web/../tests/utils";

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
        async mockRPC(route, args, originalRpc) {
            if (route === "/mail/action" && args.init_messaging) {
                const res = await originalRpc(...arguments);
                step(`/mail/action - ${JSON.stringify(args)}`);
                return res;
            }
        },
        services: {
            presence: makeFakePresenceService({
                isOdooFocused() {
                    return false;
                },
            }),
        },
    });
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: pyEnv.currentUserId },
        })}`,
    ]);
    // send after init_messaging because bus subscription is done after init_messaging
    await pyEnv.withGuest(guestId, () =>
        rpc("/im_livechat/chat_post", {
            message_content: "Hello",
            uuid: channel.uuid,
        })
    );
    await contains(".o_notification:has(.o_notification_bar.bg-info)", { text: "Hello" });
});
