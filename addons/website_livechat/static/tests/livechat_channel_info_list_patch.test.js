import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { click, describe, expect, mockDate, test, waitFor, waitForNone } from "@odoo/hoot";
import { Command, mockService, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";
import { defineWebsiteLivechatModels } from "./website_livechat_test_helpers";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("shows recent page views", async () => {
    mockDate("2025-07-16 12:00:00", 0);
    const pyEnv = await startServer();
    const website_id = pyEnv["website"].create({ name: "General website" });
    const [page1, page2] = pyEnv["website.page"].create([{ name: "Home" }, { name: "Contact" }]);
    const visitorId = pyEnv["website.visitor"].create({ website_id });
    pyEnv["website.track"].create([
        {
            page_id: page1,
            url: "https://example.com/0",
            visitor_id: visitorId,
            visit_datetime: "2025-07-16 10:00:20",
        },
        {
            page_id: page1,
            url: "https://example.com/1",
            visitor_id: visitorId,
            visit_datetime: "2025-07-16 10:10:20",
        },
        {
            page_id: page2,
            url: "javascript:alert(1)",
            visitor_id: visitorId,
            visit_datetime: "2025-07-16 10:20:20",
        },
        {
            url: "https://example.com/3",
            visitor_id: visitorId,
            visit_datetime: "2025-07-16 10:30:20",
        },
    ]);
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
    mockService("action", {
        doAction(action, options) {
            if (action !== "website.website_visitor_page_action") {
                return super.doAction(...arguments);
            }
            expect(options.additionalContext).toEqual({
                active_id: visitorId,
                search_default_type_url: 1,
            });
            expect(options.newWindow).toBe(true);
            expect.step("view all page views");
        },
    });
    const env = await start();
    await openDiscuss(channelId);
    await waitFor(".o-livechat-WebsiteHistory h6:text('Recent page views')");
    await waitFor(".o-livechat-WebsiteName:text('General website')");
    await waitFor(".o-livechat-WebsiteHistory a:count(3)");
    await waitFor(
        ".o-livechat-WebsiteHistory a:nth-child(1)" +
            "[href='https://example.com/3']" +
            ":has(.fw-bold:text('/3'))" +
            ":has(.small:text('Jul 16, 10:30 AM'))"
    );
    await waitFor(
        ".o-livechat-WebsiteHistory a:nth-child(2):not([href])" +
            ":has(.text-warning[data-icon='warning'][data-tooltip='Unsafe link'])" +
            ":has(.fw-bold:text('Contact'))" +
            ":has(.small:text('Jul 16, 10:20 AM'))"
    );
    await waitFor(
        ".o-livechat-WebsiteHistory a:nth-child(3)" +
            "[href='https://example.com/1']" +
            ":has(.fw-bold:text('Home'))" +
            ":has(.small:text('Jul 16, 10:10 AM'))"
    );
    await waitFor(".o-livechat-WebsiteHistory .badge:text('4')");
    await waitForNone(".o-livechat-BrowsingHistory");
    await click(
        ".o-livechat-WebsiteHistory button[aria-label='View all page views (opens in a new tab)']"
    );
    await expect.waitForSteps(["view all page views"]);
    const store = env.services["mail.store"];
    store.has_multi_website = false;
    await waitForNone(".o-livechat-WebsiteName");
});

test("shows browsing history when the conversation has no website visitor", async () => {
    const pyEnv = await startServer();
    const partnerId = serverState.partnerId;
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
    });
    let requestId;
    onRpc("discuss.channel", "request_browsing_history", ({ args }) => {
        expect(args[0]).toEqual([channelId]);
        requestId = args[1];
        expect.step("history requested");
    });
    await start();
    await openDiscuss(channelId);
    await expect.waitForSteps(["history requested"]);
    await waitFor(".o-livechat-BrowsingHistory div:text('Loading recent page views...')");
    await waitForNone(".o-livechat-WebsiteHistory");
    await withGuest(guestId, () =>
        rpc("/im_livechat/history", {
            channel_id: channelId,
            request_id: requestId,
            pid: partnerId,
            page_history: [
                {
                    url: "https://example.com/contact",
                    title: "Contact",
                    visit_datetime: "2026-06-07T06:07:00.000Z",
                },
            ],
        })
    );
    await waitFor(
        '.o-livechat-BrowsingHistory a[href="https://example.com/contact"] .fw-bold:text("Contact")'
    );
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
    const channelIds = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [],
            channel_type: "livechat",
            description: "question about the live chat app",
            livechat_status: "in_progress",
            livechat_visitor_id: visitorId,
        },
        {
            channel_member_ids: [],
            channel_type: "livechat",
            description: "question about the discuss app",
            livechat_status: "in_progress",
            livechat_visitor_id: visitorId,
        },
        {
            channel_member_ids: [],
            channel_type: "livechat",
            livechat_status: "in_progress",
            livechat_visitor_id: visitorId,
        },
    ]);
    pyEnv["discuss.channel.member"].create([
        {
            channel_id: channelIds[0],
            livechat_member_type: "visitor",
            partner_id: customerPartnerId,
        },
        {
            channel_id: channelIds[1],
            livechat_member_type: "visitor",
            partner_id: customerPartnerId,
        },
        {
            channel_id: channelIds[2],
            livechat_member_type: "visitor",
            partner_id: customerPartnerId,
        },
        {
            channel_id: channelIds[2],
            livechat_member_type: "agent",
            partner_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss(channelIds.at(-1));
    await contains(".o-livechat-LivechatChannelInfoList-recentConversation", {
        count: 2,
        text: "Conversation ongoing",
    });
    await waitFor(
        ".o-livechat-LivechatChannelInfoList-recentConversation :text('question about the discuss app'):count(1)"
    );
    await waitFor(
        ".o-livechat-LivechatChannelInfoList-recentConversation :text('question about the live chat app'):count(1)"
    );
});
