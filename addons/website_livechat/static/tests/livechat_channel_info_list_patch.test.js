import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockTimeZone } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineWebsiteLivechatModels } from "./website_livechat_test_helpers";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("shows recent page views", async () => {
    mockTimeZone(11);
    const pyEnv = await startServer();
    const country_id = pyEnv["res.country"].create({ code: "BE" });
    const lang_id = pyEnv["res.lang"].create({ name: "English" });
    const website_id = pyEnv["website"].create({ name: "General website" });
    const page1 = pyEnv["website.page"].create({
        name: "Home",
    });
    const page2 = pyEnv["website.page"].create({
        name: "Contact",
    });
    const visitorId = pyEnv["website.visitor"].create({
        country_id,
        lang_id,
        website_id,
    });
    pyEnv["website.track"].create([
        { page_id: page1, visitor_id: visitorId, visit_datetime: "2025-07-16 10:00:20" },
        { page_id: page2, visitor_id: visitorId, visit_datetime: "2025-07-16 10:20:20" },
    ]);
    const guestId = pyEnv["mail.guest"].create({ name: `Visitor #${visitorId}` });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_visitor_id: visitorId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("h6", { text: "Recent page views" });
    await contains("div > span", { text: "General website" });
    await contains("span", { text: "Home (21:00) → Contact (21:20)" });
});
