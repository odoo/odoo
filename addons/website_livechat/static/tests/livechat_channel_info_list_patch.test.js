import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockTimeZone } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineWebsiteLivechatModels } from "./website_livechat_test_helpers";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("shows language, country and recent page views", async () => {
    mockTimeZone(11);
    const pyEnv = await startServer();
    const country_id = pyEnv["res.country"].create({ code: "BE" });
    const lang_id = pyEnv["res.lang"].create({ name: "English" });
    const website_id = pyEnv["website"].create({ name: "General website" });
    const visitorId = pyEnv["website.visitor"].create({
        country_id,
        page_visit_history: JSON.stringify([
            ["Home", "2025-07-16 10:00:20"],
            ["Contact", "2025-07-16 10:20:20"],
        ]),
        lang_id,
        website_id,
    });
    const guestId = pyEnv["mail.guest"].create({ name: `Visitor #${visitorId}` });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        country_id,
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_visitor_id: visitorId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("h6", { text: "Country & Language" });
    await contains("span[title='Language']", { text: "English" });
    const [country] = pyEnv["res.country"].search_read([["id", "=", country_id]]);
    await contains(`.o_country_flag[data-src*='/country_flags/${country.code.toLowerCase()}.png']`);
    await contains("h6", { text: "Recent page views" });
    await contains("div > span", { text: "General website" });
    await contains("span", { text: "Home (21:00) → Contact (21:20)" });
});
