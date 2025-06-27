import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { press } from "@odoo/hoot-dom";
import { defineCrmLivechatModels } from "./crm_livechat_test_helpers";

describe.current.tags("desktop");
defineCrmLivechatModels();

test("Can open lead from internal link", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/lead My Lead");
    await press("Enter");
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click('.o_mail_notification a[data-oe-model="crm.lead"]');
    await contains(".o-mail-ChatWindow-header", { text: "Visitor" });
    await contains(".o_form_view .o_last_breadcrumb_item span", { text: "My Lead" });
});
