/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";
import { contains, click } from "@web/../tests/utils";

QUnit.module("Thread Readonly");

QUnit.test("Rendering of readonly threads in Discuss", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const userId = pyEnv["res.users"].create({ name: "James" });
    const operatorId = pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        name: "Visitor 20",
        channel_member_ids: [
            Command.create({ partner_id: operatorId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: operatorId,
    });
    const { env, openDiscuss } = await start();
    // If readonly thread is opened outside Livechat, the inbox is mounted.
    openDiscuss(channelId);
    await contains(".o-mail-Thread-empty");
    env.services["menu"].getCurrentApp = () => ({
        xmlid: "im_livechat.menu_livechat_root",
    });
    openDiscuss(channelId);
    // Listening to opened readonly threads.
    pyEnv.withUser(userId, () =>
        env.services.rpc("/mail/message/post", {
            post_data: { body: "Hello!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message-body", { text: "Hello!" });
    await contains(".o-mail-Message-actions", { count: 0 });
    await contains(".o-mail-Composer", { count: 0 });
    await contains("button[name='call']", { count: 0 });
    await contains("button[name='add-users']", { count: 0 });
    await contains("button[name='settings']", { count: 0 });
    await click("button[name='member-list']");
    await contains("button", { count: 0, text: "Invite a User" });
});
