import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { advanceTime, describe, test, tick } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { url } from "@web/core/utils/urls";
import { defineLivechatModels } from "./livechat_test_helpers";
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
    });
    await start();
    await openDiscuss("tab:livechat");
    await contains(".o-mail-MessagingMenuItem:has(:text('Visitor 11'))");
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
    });
    await start();
    await openDiscuss("tab:livechat");
    await contains(".o-mail-MessagingMenuEmpty:has(:text('No Livechat Session!'))");
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
    await contains(".o-mail-MessagingMenuEmpty:has(:text('No Livechat Session!'))");
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
    });
    await start();
    await openDiscuss("tab:livechat");
    const guest = pyEnv["mail.guest"].search_read([["id", "=", guestId]])[0];
    await contains(
        `.o-mail-MessagingMenuItem img[data-src='${url(
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
    });
    await start();
    await openDiscuss(channelId);
    const partner = pyEnv["res.partner"].search_read([["id", "=", partnerId]])[0];
    await contains(
        `.o-mail-MessagingMenuItem img[data-src='${url(
            `/web/image/res.partner/${partnerId}/avatar_128?unique=${
                deserializeDateTime(partner.write_date).ts
            }`
        )}']`
    );
});

test("Clicking on leave button leaves the channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                guest_id: pyEnv["mail.guest"].create({ name: "Visitor 11" }),
                livechat_member_type: "visitor",
            }),
        ],
        channel_type: "livechat",
        create_uid: serverState.publicUserId,
    });
    pyEnv["mail.message"].create({
        body: "Last message from Visitor",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss("tab:livechat");
    await contains(".o-mail-MessagingMenuItem:has(:text('Visitor 11'))");
    await click("[title='Chat Actions']");
    await click(".o-dropdown-item:contains('Close Conversation')");
    await contains(
        ".modal-header:has(:text('Closing this will end the live chat with Visitor 11. Are you sure you want to proceed?'))"
    );
    await contains(".modal-body .o-mail-Message-body:has(:text('Last message from Visitor'))");
    await click("button:contains(Close Conversation)");
    await contains(".o-mail-MessagingMenuEmpty");
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
    await contains(".o-mail-MessagingMenu-tab:has(:text('Live Chats')) .badge:text(1)");
});

test("looking for help shows self chats first", async () => {
    mockDate("2023-01-03 14:00:00");
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const [guestId1, guestId2] = pyEnv["mail.guest"].create([
        { name: "Visitor #1" },
        { name: "Visitor #2" },
    ]);
    const nonSelfChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        channel_type: "livechat",
        last_interest_dt: "2023-01-03 13:58:00",
        livechat_looking_for_help_since_dt: "2023-01-03 13:58:00",
        livechat_status: "need_help",
    });
    pyEnv["discuss.channel.member"].create({
        guest_id: guestId1,
        channel_id: nonSelfChannelId,
        livechat_member_type: "visitor",
    });
    const selfChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                livechat_member_type: "agent",
                last_interest_dt: "2023-01-03 11:00:00",
            }),
        ],
        channel_type: "livechat",
        last_interest_dt: "2023-01-03 11:00:00",
        livechat_looking_for_help_since_dt: "2023-01-03 11:00:00",
        livechat_status: "need_help",
    });
    pyEnv["discuss.channel.member"].create({
        guest_id: guestId2,
        channel_id: selfChannelId,
        livechat_member_type: "visitor",
    });
    await start();
    await openDiscuss(nonSelfChannelId);
    await click("button:text('Help needed')");
    await waitFor(`
        .o-mail-MessagingMenuItem:has(:text('Visitor #2'))
        + .o-mail-MessagingMenuItem:has(:text('Visitor #1'))
    `);
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
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(< 1m)"
    );
    await advanceTime(60_000);
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(1m)"
    );
    await advanceTime(60_000 * 9);
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(10m)"
    );
    await advanceTime(60_000 * 50);
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(1h)"
    );
    await advanceTime(60_000 * 60 * 23);
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(1d)"
    );
    await advanceTime(60_000 * 60 * 24);
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(2d)"
    );
    await click("button[name='join-channel']");
    await contains(".o-livechat-LivechatStatusSelection .active:text('In Progress')");
    await waitForNone(
        ".o-mail-MessagingMenuItem:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer"
    );
});

test("show looking for help duration when the agent is a member of the chat", async () => {
    mockDate("2023-01-03 14:00:00");
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        livechat_looking_for_help_since_dt: "2023-01-03 14:00:00",
        livechat_status: "need_help",
    });
    pyEnv["discuss.channel.member"].create([
        {
            guest_id: pyEnv["mail.guest"].create({ name: "Visitor #1" }),
            channel_id: channelId,
            livechat_member_type: "visitor",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-MessagingMenuItem:has(:text(Visitor #1)) .o-livechat-LookingForHelp-timer:text(< 1m)"
    );
});

test("sidebar: leave non-livechat channel removes it from sidebar", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "group",
    });
    await start();
    await openDiscuss();
    await click(".o-mail-NotificationItem:has(:text('General'))");
    await click(".o-mail-NotificationItem:has(:text('General')) .oi-ellipsis-h");
    await click(".o-dropdown-item:contains('Leave Channel')");
    await contains(
        ".modal-body:text('You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?')"
    );
    await click("button:text('Leave Conversation')");
    await contains(".o-mail-MessagingMenuItem:has(:text('General'))", { count: 0 });
});

test("show visitor language and country flag in sidebar", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Batman" });
    const countryId = pyEnv["res.country"].create({ code: "go", name: "Gotham" });
    const languageId = pyEnv["res.lang"].create({ code: "gu_IN", name: "Gujarati" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ partner_id: partnerId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        country_id: countryId,
        livechat_lang_id: languageId,
    });
    await start();
    await openDiscuss("tab:livechat");
    await contains(
        ".o-mail-MessagingMenuItem:has(:text('Batman GU')) .o-mail-CountryFlag[title='Gotham']"
    );
});
