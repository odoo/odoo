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
    const website_id = pyEnv["website"].create({ name: "General website" });
    const visitorId = pyEnv["website.visitor"].create({
        page_visit_history: JSON.stringify([
            ["Home", "2025-07-16 10:00:20"],
            ["Contact", "2025-07-16 10:20:20"],
        ]),
        website_id,
    });
    const guestId = pyEnv["mail.guest"].create({ name: `Visitor #${visitorId}` });
    // Do not add agent to the channel to ensure information is properly
    // displayed, even when the agent is not a member.
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_visitor_id: visitorId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("h6", { text: "Recent page views" });
    await contains("div > span", { text: "General website" });
    await contains("span", { text: "Home (21:00) → Contact (21:20)" });
});

test("Show recent conversations in channel info list", async () => {
    const pyEnv = await startServer();
    const visitorId = pyEnv["website.visitor"].create({
        website_id: pyEnv["website"].create({ name: "General website" }),
    });
    const customerPartnerId = pyEnv["res.partner"].create({
        name: "Bob",
        user_ids: [pyEnv["res.users"].create({ name: "Bob" })],
    });
    // At least two ongoing chats so that sort function ends up comparing two
    // ongoing chats.
    const channelId = pyEnv["discuss.channel"]
        .create([
            {
                channel_member_ids: [
                    Command.create({
                        partner_id: customerPartnerId,
                        livechat_member_type: "visitor",
                    }),
                ],
                channel_type: "livechat",
                livechat_status: "in_progress",
                livechat_visitor_id: visitorId,
            },
            {
                channel_member_ids: [
                    Command.create({
                        partner_id: customerPartnerId,
                        livechat_member_type: "visitor",
                    }),
                ],
                channel_type: "livechat",
                livechat_status: "in_progress",
                livechat_visitor_id: visitorId,
            },
            {
                channel_member_ids: [
                    Command.create({
                        partner_id: customerPartnerId,
                        livechat_member_type: "visitor",
                    }),
                    Command.create({
                        partner_id: serverState.partnerId,
                        livechat_member_type: "agent",
                    }),
                ],
                livechat_operator_id: serverState.partnerId,
                channel_type: "livechat",
                livechat_status: "in_progress",
                livechat_visitor_id: visitorId,
            },
        ])
        .at(-1);
    await start();
    await openDiscuss(channelId);
    await contains(".o-livechat-LivechatChannelInfoList-recentConversation", {
        count: 2,
        text: "Bob",
    });
});
