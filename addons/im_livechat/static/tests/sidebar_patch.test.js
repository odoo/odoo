const test = QUnit.test; // QUnit.test()

import { rpc } from "@web/core/network/rpc";

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { openDiscuss, start } from "@mail/../tests/helpers/test_utils";

import { url } from "@web/core/utils/urls";
import { nextTick } from "@web/../tests/helpers/utils";
import { deserializeDateTime } from "@web/core/l10n/dates";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("discuss sidebar (patch)");

test("Unknown visitor", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
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
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { text: "Jean (Belgium)" });
});

test("Do not show channel when visitor is typing", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([pyEnv.currentUserId], { im_status: "online" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [pyEnv.currentUserId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [
                0,
                0,
                {
                    is_pinned: false,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory", { count: 2 });
    await contains(".o-mail-DiscussSidebarCategory-livechat", { count: 0 });
    // simulate livechat visitor typing
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    await pyEnv.withGuest(guestId, () =>
        rpc("/im_livechat/notify_typing", {
            is_typing: true,
            channel_id: channel.id,
        })
    );
    // weak test, no guaranteed that we waited long enough for the livechat to potentially appear
    await nextTick();
    await contains(".o-mail-DiscussSidebarCategory-livechat", { count: 0 });
});

test("Smiley face avatar for livechat item linked to a guest", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss();
    const guest = pyEnv["mail.guest"].searchRead([["id", "=", guestId]])[0];
    await contains(
        `.o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel img[data-src='${url(
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
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss(channelId);
    const partner = pyEnv["res.partner"].searchRead([["id", "=", partnerId]])[0];
    await contains(
        `.o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel img[data-src='${url(
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
            [
                0,
                0,
                {
                    message_unread_counter: 10,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
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
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-livechat");
    await contains(".o-mail-DiscussSidebarCategory-livechat .o-discuss-badge", { count: 0 });
});

test("Counter should have correct value of unread threads if category is folded and with unread messages", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [
                0,
                0,
                {
                    message_unread_counter: 10,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat .o-discuss-badge", { text: "1" });
});

test("Close manually by clicking the title", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel");
    // fold the livechat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});

test("Open manually by clicking the title", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
    });
    await start();
    await openDiscuss();
    // first, close the live chat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat");
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel", {
        count: 0,
    });
    // open the livechat category
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel");
});

test("Category item should be invisible if the category is closed", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel");
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel", {
        count: 0,
    });
});

test("Active category item should be visible even if the category is closed", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel");
    await click(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel");
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel.o-active"
    );
    await click(".o-mail-DiscussSidebarCategory-livechat .btn");
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel");
});

test("Clicking on unpin button unpins the channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: pyEnv["mail.guest"].create({ name: "Visitor 11" }) }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebarChannel [title='Unpin Conversation']");
    await contains(".o_notification", { text: "You unpinned your conversation with Visitor 11" });
});

test("Message unread counter", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await openDiscuss();
    pyEnv.withGuest(guestId, () =>
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
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jane" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [[0, 0, { partner_id: partnerId }]],
        channel_type: "livechat",
        livechat_operator_id: partnerId,
    });
    await start();
    await openDiscuss();
    await contains("button.o-active", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarCategory-livechat", { count: 0 });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel.o-active",
        {
            text: "Jane",
        }
    );
    await insertText(".o-mail-Composer-input", "Hello", { replace: true });
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message", { text: "Hello" });
    await click("button", { text: "Inbox" });
    await contains(".o-mail-DiscussSidebarChannel:not(.o-active)", { text: "Jane" });
    await click("div[title='Unpin Conversation']", {
        parent: [".o-mail-DiscussSidebarChannel", { text: "Jane" }],
    });
    await contains(".o-mail-DiscussSidebarCategory-livechat", { count: 0 });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});
