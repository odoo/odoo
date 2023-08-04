/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("messaging service (patch)");

QUnit.test("Notify message received out of focus", async (assert) => {
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
            notification: makeFakeNotificationService((message, { title }) => {
                assert.step(`message - ${message}`);
                assert.step(`title - ${title}`);
            }),
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
    await nextTick();
    assert.verifySteps(["message - Hello", "title - New message"]);
});
