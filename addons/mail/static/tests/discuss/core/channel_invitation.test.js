import {
    actionPanel,
    click,
    contains as mailContains,
    defineMailModels,
    insertText,
    mockGetMedia,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
    MENU_ACTIVE_IDS,
    pasteMulti,
} from "@mail/../tests/mail_test_helpers";
import { describe, queryOne, test, waitFor, waitForNone } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    Command,
    contains,
    getService,
    onRpc,
    serverState,
    withUser,
} from "@web/../tests/web_test_helpers";
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
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await contains("button[title='Add People']:count(1)").click();
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
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Invite People'):count(1)").click();
    const invitePanel = actionPanel('Invite people to the channel "TestChannel"');
    await waitFor(`${invitePanel}:count(1)`);
    await contains(
        ".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner')):count(1)"
    ).click();
    await contains(`${invitePanel} button:text('Invite'):enabled:count(1)`).click();
    await waitForNone(invitePanel);
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
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await contains("button[title='Add People']:count(1)").click();
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
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
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
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await contains("button[title='Add People']:count(1)").click();
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
    await contains(".o-mail-DiscussContent-header button[title='Invite People']:count(1)").click();
    await waitFor(`${actionPanel("Invite people")}:count(1)`);
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await contains(
        ".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2')):count(1)"
    ).click();
    await contains("button:text('Create Group Chat'):enabled:count(1)").click();
    await waitForNone(actionPanel("Invite people"));
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
    await contains(".o-mail-MessagingMenu-tab[data-id='chat']:count(1)").click();
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
    await contains(".o-mail-DiscussContent-header button[title='Invite People']:count(1)").click();
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner");
    await contains(
        ".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner')):count(1)"
    ).click();
    await contains("button:contains('Go to Conversation'):enabled:count(1)").click();
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

test("invite email from chat invites it to the new group chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(chatId);
    await click(".o-mail-DiscussContent-header button[title='Invite People']");
    await insertText(".o-discuss-ChannelInvitation-search", "john@test.com");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('john@test.com'))");
    await click("button:text('Create Group Chat'):enabled");
    await waitFor(".o-discuss-ChannelMember:has(:text('john@test.com')):count(1)");
    await waitFor(".o-discuss-ChannelMember:has(:text('Invitation Pending')):count(1)");
});

test("Create group chat transfers active call to new group chat", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "TestPartner1" },
        { name: "TestPartner2" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-header button[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard:count(1)");
    await contains(".o-discuss-CallActionList button[title='Turn camera on']:count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Turn camera off']:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='Mute']:count(1)");
    await contains(".o-discuss-CallActionList button[title='Voice Settings']:count(1)").click();
    await contains(".o-discuss-QuickVoiceSettings button:text('Deafen'):count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Undeafen']:count(1)");

    await contains(".o-mail-DiscussContent-header button[title='Invite People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:text('TestPartner2'):count(1)").click();
    await contains(
        ".o-discuss-ChannelInvitation-invitationBox button:text('Create Group Chat'):enabled:count(1)"
    ).click();
    await waitFor(
        ".o-mail-DiscussContent-threadName:value('Mitchell Admin, TestPartner1, and TestPartner2'):count(1)"
    );
    await waitFor(".o-discuss-CallParticipantCard:count(1)");
    await waitFor(".o-discuss-CallActionList button[title='Turn camera off']:count(1)");
    // undeafening must give the microphone back, as it would have in the old call
    await contains(".o-discuss-CallActionList button[title='Undeafen']:count(1)").click();
    await waitFor(".o-discuss-CallActionList button[title='Mute']:count(1)");

    await openDiscuss(channelId);
    // only shown once the old chat's call is empty
    await waitFor(".o-mail-DiscussContent-header button[title='Start Call']:count(1)");
});

test("Create group chat does not transfer call when in another channel's call", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "TestPartner1" },
        { name: "TestPartner2" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const generalId = pyEnv["discuss.channel"].create({ name: "General" });
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "chat",
    });
    const [memberId_1] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", chatId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: memberId_1,
        channel_id: chatId,
    });
    await start();
    await openDiscuss(generalId);
    await contains(".o-mail-DiscussContent-header button[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard:count(1)");

    await openDiscuss(chatId);
    await waitFor(".o-mail-DiscussContent-header button[title='Join the Call']:count(1)");
    await contains(".o-mail-DiscussContent-header button[title='Invite People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:text('TestPartner2'):count(1)").click();
    await contains(
        ".o-discuss-ChannelInvitation-invitationBox button:text('Create Group Chat'):enabled:count(1)"
    ).click();
    await waitFor(
        ".o-mail-DiscussContent-threadName:value('Mitchell Admin, TestPartner1, and TestPartner2'):count(1)"
    );
    await waitFor(".o-mail-DiscussContent-header button[title='Start Call']:count(1)");

    await openDiscuss(generalId);
    await waitFor(".o-discuss-CallParticipantCard:count(1)");
});

test("Create group chat joins the call of the chat when not in a call", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "TestPartner1" },
        { name: "TestPartner2" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const chatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "chat",
    });
    const [memberId_1] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", chatId],
        ["partner_id", "=", partnerId_1],
    ]);
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: memberId_1,
        channel_id: chatId,
    });
    await start();
    await openDiscuss(chatId);
    await waitFor(".o-mail-DiscussContent-header button[title='Join the Call']:count(1)");
    await contains(".o-mail-DiscussContent-header button[title='Invite People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:text('TestPartner2'):count(1)").click();
    await contains(
        ".o-discuss-ChannelInvitation-invitationBox button:text('Create Group Chat'):enabled:count(1)"
    ).click();
    await waitFor(
        ".o-mail-DiscussContent-threadName:value('Mitchell Admin, TestPartner1, and TestPartner2'):count(1)"
    );
    await waitFor(".o-discuss-CallParticipantCard:count(1)");
});

test("Create group chat from the meeting view stays in the meeting view", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "TestPartner1" },
        { name: "TestPartner2" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId_1 }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(
        ".o-mail-DiscussContent-header button[title='Start Video Call']:count(1)"
    ).click();
    await contains(".o-mail-Meeting button[title='More']:count(1)").click();
    await contains(".o-mail-ActionList-button[name='invite-people']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:text('TestPartner2'):count(1)").click();
    await contains(
        ".o-discuss-ChannelInvitation-invitationBox button:text('Create Group Chat'):enabled:count(1)"
    ).click();
    await waitFor(
        ".o-mail-DiscussContent-threadName:value('Mitchell Admin, TestPartner1, and TestPartner2'):count(1)"
    );
    await waitFor(".o-mail-Meeting .o-discuss-CallParticipantCard:count(1)");
});

test("Go to conversation from self chat transfers active call to the existing chat", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const [selfChatId] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
    ]);
    await start();
    await openDiscuss(selfChatId);
    await contains(".o-mail-DiscussContent-header button[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-CallParticipantCard:count(1)");

    await contains(".o-mail-DiscussContent-header button[title='Invite People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:text('TestPartner'):count(1)").click();
    await contains(
        ".o-discuss-ChannelInvitation-invitationBox button:text('Go to conversation'):enabled:count(1)"
    ).click();
    await waitFor(".o-mail-DiscussContent-threadName:value('TestPartner'):count(1)");
    await waitFor(".o-discuss-CallParticipantCard:count(1)");
});

test("Pasted list of emails in the invite form should be joined with commas", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test1\ntest2\n test3",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3" });
});

test("Pasted html table of emails (coming from spreadsheets) in the invite form should be joined with commas", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/html": `<table><tr><td>test1</td></tr>
                        <tr><td>test2</td></tr>
                        <tr><td>test3</td></tr>
                    </table>`,
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3" });
});

test("Multi column pasted html table of emails should take all cells and be joined with commas", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/html": `<table><tr><td>test1</td><td>test2</td></tr>
                        <tr><td>test3</td><td>test4</td></tr>
                    </table>`,
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3,test4" });
});

test("Pasting on selected text, should replace the selection with the pasted text", async () => {
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
    await insertText(".o-discuss-ChannelInvitation-search", "test1");
    queryOne(".o-discuss-ChannelInvitation-search").setSelectionRange(1, 4);
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test2\ntest3",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "t,test2,test3,1" });
});

test("Pasting on selected text, should keep commas around the selection when replacing it with the pasted text", async () => {
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
    await insertText(".o-discuss-ChannelInvitation-search", "test1,test2,test3");
    queryOne(".o-discuss-ChannelInvitation-search").setSelectionRange(6, 11);
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test4\ntest5",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test1,test4,test5,test3" });
});

test("Pasting in front of existing text, should keep the existing text after the pasted text", async () => {
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
    await insertText(".o-discuss-ChannelInvitation-search", "test1,test2");
    queryOne(".o-discuss-ChannelInvitation-search").setSelectionRange(0, 0);
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test3\ntest4",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test3,test4,test1,test2" });
});

test("Pasting at the end of existing text, should keep the existing text before the pasted text", async () => {
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
    await insertText(".o-discuss-ChannelInvitation-search", "test1,test2");
    queryOne(".o-discuss-ChannelInvitation-search").setSelectionRange(11, 11);
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test3\ntest4",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3,test4" });
});

test("Pasting document with table should fallback to text/plain if it contains other elements", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/html": `<table><tr><td>test1</td></tr>
                        <tr><td>test2</td></tr>
                        <tr><td>test3</td></tr>
                    </table>
                    <p>other element</p>`,
        "text/plain": "test4\ntest5\n test6",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test4,test5,test6" });
});

test("Pasting document with multiple tables should fallback to text/plain", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/html": `<table><tr><td>test1</td></tr>
                        <tr><td>test2</td></tr>
                        <tr><td>test3</td></tr>
                    </table>
                    <table><tr><td>test4</td></tr>
                        <tr><td>test5</td></tr>
                        <tr><td>test6</td></tr>
                    </table>`,
        "text/plain": "test7\ntest8\n test9",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test7,test8,test9" });
});

test("Pasting html with no table should fallback to text/plain", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/html": `<p>test1</p>
                    <p>test2</p>
                    <p>test3</p>`,
        "text/plain": "test4\ntest5\n test6",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test4,test5,test6" });
});

test("Pasted html table drops empty cells and trims the others", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/html": `<table><tr><td>test1</td></tr>
                        <tr><td> test2 </td></tr>
                        <tr><td></td></tr>
                        <tr><td>test3</td></tr>
                    </table>`,
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3" });
});

test("Pasted plain text drops empty lines and trims the others", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test1\n\n test2 \n test3",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3" });
});

test("Pasted html cells are kept whole, spaces and commas included", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/html": `<table><tr><td>Doe, John</td></tr>
                        <tr><td>Jane Smith</td></tr>
                    </table>`,
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "Doe, John,Jane Smith" });
});

test("Pasted plain text lines are kept whole, spaces and commas included", async () => {
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "Doe, John\nJane Smith",
    });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "Doe, John,Jane Smith" });
});

test("Pasting several emails selects the partners they match instead of listing them as selectable", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo Partner",
        email: "demo@partner.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "demo@partner.com\nnew1@test.com",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(Demo Partner):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new1@test.com):count(1)");
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "" });
});

test("Pasting several brand-new emails selects them instead of listing them as selectable", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "new1@test.com\nnew2@test.com",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new1@test.com):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new2@test.com):count(1)");
});

test("Pasting emails separated by semicolons selects each of them", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "new1@test.com; new2@test.com",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new1@test.com):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new2@test.com):count(1)");
});

test("Pasting emails with a comma in their quoted name selects the partners they match", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create([
        { name: "John Doe", email: "john@test.com" },
        { name: "Jane Doe", email: "jane@test.com" },
    ]);
    pyEnv["res.users"].create(partnerIds.map((partner_id) => ({ partner_id })));
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": '"Doe, John" <john@test.com>,"Doe, Jane" <jane@test.com>',
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(John Doe):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(Jane Doe):count(1)");
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "" });
});

test("Pasting several entries keeps the ones that match nobody in the search", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo Partner",
        email: "demo@partner.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "demo@partner.com\nJohn Doe",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(Demo Partner):count(1)");
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "John Doe" });
});

test("Pasting several entries drops the ones of current members from the search", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo Partner",
        email: "demo@partner.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
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
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "demo@partner.com\nnew1@test.com",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new1@test.com):count(1)");
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "" });
});

test("Pasting an address that already received an invitation leaves it in the search with a hint", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    onRpc("res.partner", "search_for_channel_invite", ({ parent }) => {
        const result = parent();
        result.emails_already_sent = result.selectable_emails.filter(
            (email) => email === "sent@test.com"
        );
        return result;
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "sent@test.com\nnew1@test.com",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new1@test.com):count(1)");
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "sent@test.com" });
    await waitFor(
        ".o-discuss-ChannelInvitation-selectable:has(:text('sent@test.com')):has(:text('Invitation already sent to this address')):count(1)"
    );
});

test("Pasting a name holding a comma searches it as a name", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Doe, John", email: "john@test.com" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", { "text/plain": "Doe, John" });
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "Doe, John" });
    await waitFor(".o-discuss-ChannelInvitation-selectable:has(:text('Doe, John')):count(1)");
});

test("Pasting an address preceded by a name selects its partner", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo Partner",
        email: "demo@partner.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "Demo demo@partner.com\nnew1@test.com",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(Demo Partner):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new1@test.com):count(1)");
    await mailContains(".o-discuss-ChannelInvitation-search", { value: "" });
});

test("Pasting one address among names selects only the partner owning it", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create([
        { name: "Ann Smith", email: "ann@example.com" },
        { name: "Joann Miller", email: "joann@example.com" },
    ]);
    pyEnv["res.users"].create(partnerIds.map((partner_id) => ({ partner_id })));
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "Ann Smith\nann@example.com",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(Ann Smith):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:count(1)");
});

test("Typing several emails suggests them instead of selecting them", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo Partner",
        email: "demo@partner.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await insertText(".o-discuss-ChannelInvitation-search", "demo@partner.com,new1@test.com");
    await waitFor(
        ".o-discuss-ChannelInvitation-selectable:not(.o-selected):has(:text('Demo Partner')):count(1)"
    );
    await waitFor(
        ".o-discuss-ChannelInvitation-selectable:not(.o-selected):has(:text('new1@test.com')):count(1)"
    );
});

test("What a pasted list selected stays selected once the search text changes", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo Partner",
        email: "demo@partner.com",
    });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Chat Actions']");
    await click(".o-dropdown-item:text('Invite People')");
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "demo@partner.com\nnew1@test.com",
    });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(Demo Partner):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new1@test.com):count(1)");
    await insertText(".o-discuss-ChannelInvitation-search", "something else", { replace: true });
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(Demo Partner):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectedList button:text(new1@test.com):count(1)");
});
