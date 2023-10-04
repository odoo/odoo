/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";
import { contains, click } from "@web/../tests/utils";

QUnit.module("Thread Readonly");

QUnit.test("The rendering of threads depends on the readonly property", async () => {
    const pyEnv = await startServer();
    const adminGroupId = pyEnv["res.groups"].create({ name: "livechat_admin" });
    pyEnv.currentUser.groups_id.push(adminGroupId);
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 20" });
    const userId = pyEnv["res.users"].create({ name: "James" });
    const operatorId = pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const standardChannelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 20",
        name: "Visitor 20",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    pyEnv["mail.message"].create({
        body: "<p>Not Readonly</p>",
        model: "discuss.channel",
        res_id: standardChannelId,
    });
    const readonlyChannelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 30",
        name: "Visitor 30",
        channel_member_ids: [
            Command.create({ partner_id: operatorId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: operatorId,
    });
    pyEnv["mail.message"].create({
        body: "<p>Readonly</p>",
        model: "discuss.channel",
        res_id: readonlyChannelId,
    });
    const { env, openDiscuss } = await start();
    // Open discuss from Livechat to trigger conditional rendering.
    env.services["menu"].getCurrentApp = () => ({
        xmlid: "im_livechat.menu_livechat_root",
    });
    openDiscuss(standardChannelId);
    await contains(".o-mail-Message-actions");
    await contains(".o-mail-Composer");
    await contains("button[name='call']");
    await contains("button[name='add-users']");
    await contains("button[name='settings']");
    await click("button[name='member-list']");
    await contains("button", { text: "Invite a User" });
    openDiscuss(readonlyChannelId);
    await contains(".o-mail-Message-actions", { count: 0 });
    await contains(".o-mail-Composer", { count: 0 });
    await contains("button[name='call']", { count: 0 });
    await contains("button[name='add-users']", { count: 0 });
    await contains("button[name='settings']", { count: 0 });
    await click("button[name='member-list']");
    await contains("button", { count: 0, text: "Invite a User" });
});
