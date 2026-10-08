import {
    click,
    contains as mailContains,
    defineMailModels,
    insertText,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
    MENU_ACTIVE_IDS,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, getService, serverState, withUser } from "@web/../tests/web_test_helpers";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";

describe.current.tags("desktop");
defineMailModels();

test("Can invite people from member panel", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await click("button[title='Add People']");
});

test("can invite users in channel from chat window", async () => {
    mockDate("2025-01-01 12:00:00", +1);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_type: "channel",
    });
    setupChatHub({ opened: [channelId] });
    await start();
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Invite People')");
    await waitFor(".o-discuss-ChannelInvitation:count(1)");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner'))");
    await click(".o-discuss-ChannelInvitation button:text('Invite'):enabled");
    await waitForNone(".o-discuss-ChannelInvitation");
    const [{ date }] = pyEnv["mail.message"].search_read([["res_id", "=", channelId]]);
    const time = deserializeDateTime(date).toLocaleString(luxon.DateTime.TIME_SIMPLE, {
        locale: user.lang,
    });
    await waitFor(
        `.o-mail-Thread .o-mail-NotificationMessage:text('Mitchell Admin invited TestPartner to the channel${time}'):count(1)`
    );
});

test("should be able to search for a new user to invite from an existing chat", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const partnerId_2 = pyEnv["res.partner"].create({
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    pyEnv["res.users"].create({ partner_id: partnerId_1 });
    pyEnv["res.users"].create({ partner_id: partnerId_2 });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await click("button[title='Add People']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await waitFor(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2')):count(1)");
});

test("Can quick unselect people from the channel invitation", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const partnerId_2 = pyEnv["res.partner"].create({
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    pyEnv["res.users"].create({ partner_id: partnerId_1 });
    pyEnv["res.users"].create({ partner_id: partnerId_2 });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await click("button[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2'))");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2')).o-selected");
    const selectedButtonsSelector = ".o-discuss-ChannelInvitation-selectedList button";
    await waitFor(`${selectedButtonsSelector}:count(1)`);
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(TestPartner2):count(1)");
    await waitFor(
        ".o-discuss-ChannelInvitation-selectedList button:text(TestPartner2) [data-icon='close_small']:count(1)"
    );
    await click(".o-discuss-ChannelInvitation-selectedList button:text(TestPartner2)");
    await click(
        ".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2')):not(.o-selected)"
    );
    await waitForNone(selectedButtonsSelector);
});

test("Invitation form should display channel group restriction", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const groupId = pyEnv["res.groups"].create({
        name: "testGroup",
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_type: "channel",
        group_public_id: groupId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMemberList:count(1)"); // wait for auto-open of this panel
    await click("button[title='Add People']");
    await mailContains(
        ".o-discuss-ChannelInvitation div:text('Access restricted to group \"testGroup\"')",
        {
            after: ["button [data-icon='content_copy']"],
        }
    );
});

test("should be able to create a new group chat from an existing chat", async () => {
    const pyEnv = await startServer();
    const partnerId_1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    const partnerId_2 = pyEnv["res.partner"].create({
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    pyEnv["res.users"].create({ partner_id: partnerId_1 });
    pyEnv["res.users"].create({ partner_id: partnerId_2 });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChannel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-DiscussContent-header button[title='Invite People']");
    await waitFor(".o-discuss-ChannelInvitation:count(1)");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2'))");
    await click("button:text('Create Group Chat'):enabled");
    await waitForNone(".o-discuss-ChannelInvitation");
    await waitFor(
        ".o-mail-NotificationItem:has(:text('Mitchell Admin, TestPartner, and TestPartner2')):count(1)"
    );
});

test("unnamed group chat should display correct name just after being invited", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        email: "jane@example.com",
        name: "Jane",
    });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const [, channelId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [Command.create({ partner_id: partnerId })],
            channel_type: "group",
        },
    ]);
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await waitFor(".o-mail-NotificationItem:has(:text('General')):count(1)");
    await click(".o-mail-MessagingMenu-tab[data-id='chat']");
    await waitFor(".o-mail-MessagingMenu-tab:has(:text('Chats')).active:count(1)");
    await waitForNone(".o-mail-NotificationItem:has(:text('Jane and Mitchell Admin'))");
    const currentUserId = serverState.userId;
    await withUser(userId, () =>
        getService("mail.store").fetchStoreData("/discuss/channel/add_members", {
            channel_id: channelId,
            user_ids: [currentUserId],
        })
    );
    await waitFor(".o-mail-NotificationItem:has(:text('Jane and Mitchell Admin')):count(1)");
});

test("invite user to self chat opens DM chat with user", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "TestGuest" });
    const partnerId_1 = pyEnv["res.partner"].create({
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    pyEnv["res.users"].create({ partner_id: partnerId_1 });
    const [selfChatId] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: partnerId_1 }),
                Command.create({ partner_id: serverState.partnerId }),
            ],
            channel_type: "group",
        },
        {
            // group chat with guest as correspondent for coverage of no crash
            channel_member_ids: [
                Command.create({ guest_id: guestId }),
                Command.create({ partner_id: serverState.partnerId }),
            ],
            channel_type: "group",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId_1 }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss(selfChatId);
    await waitFor(".o-mail-NotificationItem:has(:text('Mitchell Admin')):count(1)"); // self-chat
    await waitFor(".o-mail-NotificationItem:has(:text('TestPartner and Mitchell Admin')):count(1)");
    await waitFor(".o-mail-NotificationItem:has(:text('TestGuest and Mitchell Admin')):count(1)");
    await waitFor(".o-mail-NotificationItem:has(:text('TestPartner')):count(1)");
    await click(".o-mail-DiscussContent-header button[title='Invite People']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner'))");
    await click("button:contains('Go to Conversation'):enabled");
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('TestPartner')):count(1)");
});

test("Invite sidebar action has the correct title for group chats", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await waitFor(".modal-title:text('Mitchell Admin and Demo'):count(1)");
});
