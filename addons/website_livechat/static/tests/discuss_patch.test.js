import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { defineWebsiteLivechatModels } from "./website_livechat_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("Discuss header shows visitor info", async () => {
    const pyEnv = await startServer();
    const website_id = pyEnv["website"].create({ name: "General website" });
    const lang_id = pyEnv["res.lang"].create({ name: "English" });
    const visitorId = pyEnv["website.visitor"].create({
        history: "Home → Contact",
        website_id,
        lang_id,
    });
    const guestId = pyEnv["mail.guest"].create({ name: `Visitor #${visitorId}` });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: `Visitor #${visitorId}`,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_visitor_id: visitorId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss-header .o-website_livechat-Visitor-avatar");
    await contains(".o-mail-Discuss-header span[title='Language']", {
        text: "English",
    });
});
