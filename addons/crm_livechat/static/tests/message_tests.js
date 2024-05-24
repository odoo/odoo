/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("message");

QUnit.test("Can open lead from internal link", async function () {
    const pyEnv = await startServer();
    const { openDiscuss } = await start();
    const livechatChannelId = pyEnv["im_livechat.channel"].create({ name: "YourWebsite.com" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor",
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.currentPartnerId,
        name: "Visitor, Mitchell Admin",
    });
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/lead My Lead");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click('.o_mail_notification a[data-oe-model="crm.lead"]');
    await contains(".o-mail-ChatWindow-header", { text: "Mitchell Admin" });
    await contains(".o_form_view .o_last_breadcrumb_item span", { text: "My Lead" });
});
