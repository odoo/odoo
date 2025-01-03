import { waitForChannels, waitNotifications } from "@bus/../tests/bus_test_helpers";
import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";
import { mockDate, tick } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { url } from "@web/core/utils/urls";
import { defineLivechatModels } from "./livechat_test_helpers";
import { press } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineLivechatModels();

test("Unknown visitor", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar .o-mail-DiscussSidebarCategory-livechat");
    await contains(".o-mail-DiscussSidebarChannel", { text: "Visitor 11" });
});

test("Known user with country", async () => {
    const pyEnv = await startServer();
    const countryId = pyEnv["res.country"].create({
        code: "be",
        name: "Belgium",
    });
    const partnerId = pyEnv["res.partner"].create({
        country_id: countryId,
        name: "Jean",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
        country_id: countryId,
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Jean (Belgium)" });
    await contains(".o-mail-DiscussSidebarChannel img[data-src*='country_flags/be.png']");
    await click(".o-mail-DiscussSidebarChannel", { text: "Jean (Belgium)" });
    await contains(".o-mail-Discuss-header img[data-src*='country_flags/be.png']");
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem img[data-src*='country_flags/be.png']");
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
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", { count: 2 });
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container",
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
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container",
        {
            count: 0,
        }
    );
});

test("Smiley face avatar for livechat item linked to a guest", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    const guest = pyEnv["mail.guest"].search_read([["id", "=", guestId]])[0];
    await contains(
        `.o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container img[data-src='${url(
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
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    const partner = pyEnv["res.partner"].search_read([["id", "=", partnerId]])[0];
    await contains(
        `.o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container img[data-src='${url(
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
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({
                message_unread_counter: 10,
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId }),
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
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
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

test("Counter should have correct value of unread threads if category is folded and with unread messages", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId }),
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
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container"
    );
    // fold the livechat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});

test("Open manually by clicking the title", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-01 10:00:00",
            }),
            Command.create({ guest_id: guestId, last_interest_dt: "2021-01-01 10:00:00" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    // first, close the live chat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat");
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container",
        {
            count: 0,
        }
    );
    // open the livechat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container"
    );
});

test("Category item should be invisible if the category is closed", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container"
    );
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container",
        {
            count: 0,
        }
    );
});

test("Active category item should be visible even if the category is closed", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-01 10:00:00",
            }),
            Command.create({ guest_id: guestId, last_interest_dt: "2021-01-01 10:00:00" }),
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
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: pyEnv["mail.guest"].create({ name: "Visitor 11" }) }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        create_uid: serverState.publicUserId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Visitor 11" });
    await click(".o-mail-DiscussSidebarChannel [title='Leave Channel']");
    await click("button:contains(Leave Conversation)");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0, text: "Visitor 11" });
});

test("Message unread counter", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({
                partner_id: serverState.partnerId,
                last_interest_dt: "2021-01-03 10:00:00",
            }),
            Command.create({ guest_id: guestId, last_interest_dt: "2021-01-03 10:00:00" }),
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

test("unknown livechat can be displayed and interacted with", async () => {
    mockDate("2023-01-03 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: partnerId, last_interest_dt: "2021-01-01 10:00:00" }),
        ],
        channel_type: "livechat",
        livechat_active: true,
        livechat_operator_id: partnerId,
        create_uid: serverState.publicUserId,
    });
    const env = await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarCategory-livechat", { count: 0 });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await openDiscuss(channelId);
    await waitForChannels([`discuss.channel_${channelId}`]);
    await contains(".o-mail-DiscussSidebarChannel.o-active", { text: "Jane" });
    await insertText(".o-mail-Composer-input", "Hello", { replace: true });
    await press("Enter");
    await contains(".o-mail-Message", { text: "Hello" });
    await waitNotifications([env, "discuss.channel/new_message"]);
    await click("button", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel:not(.o-active)", { text: "Jane" });
    await click("[title='Leave Channel']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "Jane" }],
    });
    await click("button:contains('Leave Conversation')");
    await contains(".o-mail-DiscussSidebarCategory-livechat", { count: 0 });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});

test("Local sidebar category state is shared between tabs", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        livechat_operator_id: serverState.user,
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(undefined, { target: env1 });
    await openDiscuss(undefined, { target: env2 });
    await contains(".o-mail-DiscussSidebarCategory-livechat .oi-chevron-down", { target: env1 });
    await contains(".o-mail-DiscussSidebarCategory-livechat .oi-chevron-down", { target: env2 });
    await click(".o-mail-DiscussSidebarCategory-livechat .btn", { target: env1 });
    await contains(".o-mail-DiscussSidebarCategory-livechat .oi-chevron-right", { target: env1 });
    await contains(".o-mail-DiscussSidebarCategory-livechat .oi-chevron-right", { target: env2 });
});
