import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { advanceTime, describe, test } from "@odoo/hoot";
import { mockDate, tick } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { url } from "@web/core/utils/urls";
import { defineLivechatModels } from "./livechat_test_helpers";
import { browser } from "@web/core/browser/browser";
import { waitFor, waitForNone } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineLivechatModels();

test("Unknown visitor", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar .o-mail-DiscussSidebarCategory-livechat");
    await contains(".o-mail-DiscussSidebarChannel", { text: "Visitor 11" });
});

test("Do not show channel when visitor is typing", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], { im_status: "online" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [serverState.userId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                livechat_member_type: "agent",
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", { count: 2 });
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarCategory-channels",
        {
            count: 0,
        }
    );
    // simulate livechat visitor typing
    const channel = pyEnv["discuss.channel"].search_read([["id", "=", channelId]])[0];
    await withGuest(guestId, () =>
        rpc("/discuss/channel/notify_typing", {
            is_typing: true,
            channel_id: channel.id,
        })
    );
    // weak test, no guaranteed that we waited long enough for the livechat to potentially appear
    await tick();
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarCategory-channels",
        {
            count: 0,
        }
    );
});

test("Smiley face avatar for livechat item linked to a guest", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    const guest = pyEnv["mail.guest"].search_read([["id", "=", guestId]])[0];
    await contains(
        `.o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarCategory-channels img[data-src='${url(
            `/web/image/mail.guest/${guestId}/avatar_128?unique=${
                deserializeDateTime(guest.write_date).ts
            }`
        )}']`
    );
});

test("Partner profile picture for livechat item linked to a partner", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jean" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ partner_id: partnerId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    const partner = pyEnv["res.partner"].search_read([["id", "=", partnerId]])[0];
    await contains(
        `.o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarCategory-channels img[data-src='${url(
            `/web/image/res.partner/${partnerId}/avatar_128?unique=${
                deserializeDateTime(partner.write_date).ts
            }`
        )}']`
    );
});

test("No counter if the category is unfolded and with unread messages", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                message_unread_counter: 10,
                livechat_member_type: "agent",
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-livechat");
    await contains(".o-mail-DiscussSidebarCategory-livechat .o-mail-Discuss-category-counter", {
        count: 0,
    });
});

test("No counter if category is folded and without unread messages", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-livechat");
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat .o-discuss-badge", { count: 0 });
});

test("Counter should have count of unread conversations if category is folded and with unread messages", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                livechat_member_type: "agent",
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    pyEnv["mail.message"].create({
        author_guest_id: guestId,
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss();
    // first, close the live chat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat .o-discuss-badge", { text: "1" });
});

test("Close manually by clicking the title", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarCategory-channels"
    );
    // fold the livechat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});

test("Open manually by clicking the title, invisible channels when closed", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-01 10:00:00",
                livechat_member_type: "agent",
            }),
            Command.create({
                guest_id: guestId,
                last_interest_dt: "2021-01-01 10:00:00",
                livechat_member_type: "visitor",
            }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    const channelSelector =
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarCategory-channels:text(Visitor 11)";
    await waitFor(channelSelector);
    // first, close the live chat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat");
    await waitForNone(channelSelector);
    // open the livechat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await waitFor(channelSelector);
});

test("Active category item should be visible even if the category is closed", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-01 10:00:00",
                livechat_member_type: "agent",
            }),
            Command.create({
                guest_id: guestId,
                last_interest_dt: "2021-01-01 10:00:00",
                livechat_member_type: "visitor",
            }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel", { text: "Visitor 11" });
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Visitor 11" });
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarChannel", { text: "Visitor 11" });
});

test("Clicking on leave button leaves the channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                guest_id: pyEnv["mail.guest"].create({ name: "Visitor 11" }),
                livechat_member_type: "visitor",
            }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        create_uid: serverState.publicUserId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Visitor 11" });
    await click("[title='Chat Actions']");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await click("button:contains(Leave Conversation)");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Visitor 11" });
});

test("Message unread counter", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 10:00:00",
                livechat_member_type: "agent",
            }),
            Command.create({
                guest_id: guestId,
                last_interest_dt: "2021-01-03 10:00:00",
                livechat_member_type: "visitor",
            }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    withGuest(guestId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "hu",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-DiscussSidebarChannel .badge", { text: "1" });
});

test("Local sidebar category state is shared between tabs", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                guest_id: pyEnv["mail.guest"].create({ name: "Visitor #12" }),
                livechat_member_type: "visitor",
            }),
        ],
        livechat_operator_id: serverState.user,
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(undefined, { target: env1 });
    await openDiscuss(undefined, { target: env2 });
    await contains(`${env1.selector} .o-mail-DiscussSidebarCategory-livechat .oi-chevron-down`);
    await contains(`${env2.selector} .o-mail-DiscussSidebarCategory-livechat .oi-chevron-down`);
    await click(`${env1.selector} .o-mail-DiscussSidebarCategory-livechat .btn`);
    await contains(`${env1.selector} .o-mail-DiscussSidebarCategory-livechat .oi-chevron-right`);
    await contains(`${env2.selector} .o-mail-DiscussSidebarCategory-livechat .oi-chevron-right`);
});

test("live chat is displayed below its category", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = pyEnv["im_livechat.channel"].create({ name: "Helpdesk" });
    browser.localStorage.setItem(
        `discuss_sidebar_category_im_livechat.category_${livechatChannelId}_open`,
        false
    );
    pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                guest_id: pyEnv["mail.guest"].create({ name: "Visitor #12" }),
                livechat_member_type: "visitor",
            }),
        ],
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarCategory .btn", { text: "Helpdesk" });
    await contains(
        ".o-mail-DiscussSidebarCategory:contains(Helpdesk) + .o-mail-DiscussSidebarCategory-channels:contains(Visitor #12)"
    );
});

test("looking for help category is sorted by looking for help duration", async () => {
    mockDate("2023-01-03 14:00:00");
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const guestIds = pyEnv["mail.guest"].create([
        { name: "Visitor #1" },
        { name: "Visitor #2" },
        { name: "Visitor #3" },
        { name: "Visitor #4" },
    ]);
    const channelIds = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [],
            channel_type: "livechat",
            livechat_looking_for_help_since_dt: "2023-01-03 13:00:00",
            livechat_status: "need_help",
        },
        {
            channel_member_ids: [],
            channel_type: "livechat",
            livechat_looking_for_help_since_dt: "2023-01-03 11:00:00",
            livechat_status: "need_help",
        },
        {
            channel_member_ids: [],
            channel_type: "livechat",
            livechat_looking_for_help_since_dt: "2023-01-03 14:00:00",
            livechat_status: "need_help",
        },
        {
            channel_member_ids: [],
            channel_type: "livechat",
            livechat_looking_for_help_since_dt: "2023-01-03 13:58:00",
            livechat_status: "need_help",
        },
    ]);
    pyEnv["discuss.channel.member"].create([
        { guest_id: guestIds[0], channel_id: channelIds[0], livechat_member_type: "visitor" },
        { guest_id: guestIds[1], channel_id: channelIds[1], livechat_member_type: "visitor" },
        { guest_id: guestIds[2], channel_id: channelIds[2], livechat_member_type: "visitor" },
        { guest_id: guestIds[3], channel_id: channelIds[3], livechat_member_type: "visitor" },
    ]);
    await start();
    await openDiscuss();
    await waitFor(`
        .o-mail-DiscussSidebarChannel-container:has(:text(Visitor #2))
        + .o-mail-DiscussSidebarChannel-container:has(:text(Visitor #1)) 
        + .o-mail-DiscussSidebarChannel-container:has(:text(Visitor #4))
        + .o-mail-DiscussSidebarChannel-container:has(:text(Visitor #3))
    `);
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #2)) .o-livechat-LookingForHelp-timer:text(3h)"
    );
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(1h)"
    );
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #4)) .o-livechat-LookingForHelp-timer:text(2m)"
    );
    // The timer is not shown for chats newer than one minute to avoid excessive movement in the sidebar.
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #3)) .o-livechat-LookingForHelp-timer:text(< 1m)"
    );
});

test("show looking for help duration in the sidebar", async () => {
    mockDate("2023-01-03 14:00:00");
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #1" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        channel_type: "livechat",
        livechat_looking_for_help_since_dt: "2023-01-03 14:00:00",
        livechat_status: "need_help",
    });
    pyEnv["discuss.channel.member"].create([
        { guest_id: guestId, channel_id: channelId, livechat_member_type: "visitor" },
    ]);
    await start();
    await openDiscuss();
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(< 1m)"
    );
    await advanceTime(60_000);
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(1m)"
    );
    await advanceTime(60_000 * 9);
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(10m)"
    );
    await advanceTime(60_000 * 50);
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(1h)"
    );
    await advanceTime(60_000 * 60 * 23);
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(1d)"
    );
    await advanceTime(60_000 * 60 * 24);
    await waitFor(
        ".o-mail-DiscussSidebarChannel-container:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(2d)"
    );
});
