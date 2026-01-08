/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("message");

QUnit.test("Can open lead from internal link", async function (assert) {
    const pyEnv = await startServer();
    const { openDiscuss } = await start();

    await openDiscuss(pyEnv["discuss.channel"].create({
        name: "Visitor, Mitchell Admin",
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_channel_id: pyEnv["im_livechat.channel"].create({
            name: "YourWebsite.com"
        }),
        channel_type: "livechat",
        anonymous_name: "Visitor"
    }));

    await insertText(".o-mail-Composer-input", "/lead My Lead");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click('.o_mail_notification a[data-oe-model="crm.lead"]');
    await contains(".o-mail-ChatWindow-header", { text: "Your Company Mitchell Admin" });
    await contains(".o_form_view .o_last_breadcrumb_item span", { text: "My Lead" });
});
