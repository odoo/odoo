import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
    MENU_ACTIVE_IDS,
    pasteMulti,
    selectText,
} from "@mail/../tests/mail_test_helpers";
import {
    parseHtmlClipboard,
    parseTextClipboard,
} from "@mail/discuss/core/common/channel_invitation_clipboard";
import { describe, expect, test } from "@odoo/hoot";
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
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
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Invite People')");
    await contains(".o-discuss-ChannelInvitation");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner'))");
    await click(".o-discuss-ChannelInvitation [title='Invite']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    const [{ date }] = pyEnv["mail.message"].search_read([["res_id", "=", channelId]]);
    const time = deserializeDateTime(date).toLocaleString(luxon.DateTime.TIME_SIMPLE, {
        locale: user.lang,
    });
    await contains(
        `.o-mail-Thread .o-mail-NotificationMessage:text('Mitchell Admin invited TestPartner to the channel${time}')`
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("button[title='Add People']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2'))");
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("button[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2'))");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2')).o-selected");
    const selectedButtonsSelector = ".o-discuss-ChannelInvitation-selectedList button";
    await contains(selectedButtonsSelector);
    await contains(".o-discuss-ChannelInvitation-selectedList button:text(TestPartner2)");
    await contains(
        ".o-discuss-ChannelInvitation-selectedList button:text(TestPartner2) [data-icon='close_small']"
    );
    await click(".o-discuss-ChannelInvitation-selectedList button:text(TestPartner2)");
    await click(
        ".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2')):not(.o-selected)"
    );
    await contains(selectedButtonsSelector, { count: 0 });
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("button[title='Add People']");
    await contains(
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
    await contains(".o-discuss-ChannelInvitation");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner2");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner2'))");
    await click("button[title='Create Group Chat']:enabled");
    await contains(".o-discuss-ChannelInvitation", { count: 0 });
    await contains(
        ".o-mail-NotificationItem:has(:text('Mitchell Admin, TestPartner, and TestPartner2'))"
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
    await contains(".o-mail-NotificationItem:has(:text('General'))");
    await click(".o-mail-MessagingMenu-tab[data-id='chat']");
    await contains(".o-mail-MessagingMenu-tab:has(:text('Chats')).active");
    await contains(".o-mail-NotificationItem:has(:text('Jane and Mitchell Admin'))", {
        count: 0,
    });
    const currentUserId = serverState.userId;
    await withUser(userId, () =>
        getService("mail.store").fetchStoreData("/discuss/channel/add_members", {
            channel_id: channelId,
            user_ids: [currentUserId],
        })
    );
    await contains(".o-mail-NotificationItem:has(:text('Jane and Mitchell Admin'))");
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
    await contains(".o-mail-NotificationItem:has(:text('Mitchell Admin'))"); // self-chat
    await contains(".o-mail-NotificationItem:has(:text('TestPartner and Mitchell Admin'))");
    await contains(".o-mail-NotificationItem:has(:text('TestGuest and Mitchell Admin'))");
    await contains(".o-mail-NotificationItem:has(:text('TestPartner'))");
    await click(".o-mail-DiscussContent-header button[title='Invite People']");
    await insertText(".o-discuss-ChannelInvitation-search", "TestPartner");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('TestPartner'))");
    await click("button:contains('Go to Conversation'):enabled");
    await contains(".o-mail-NotificationItem.o-active:has(:text('TestPartner'))");
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
    await contains(".modal-title:text('Mitchell Admin and Demo')");
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
    await contains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3" });
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
    await contains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3" });
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
        "text/plain": "test1\ntest2\n test3",
    });
    await contains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3,test4" });
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
    await selectText(".o-discuss-ChannelInvitation-search", { start: 1, end: 4 });
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test2\ntest3",
    });
    await contains(".o-discuss-ChannelInvitation-search", { value: "t,test2,test3,1" });
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
    await selectText(".o-discuss-ChannelInvitation-search", { start: 6, end: 11 });
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test4\ntest5",
    });
    await contains(".o-discuss-ChannelInvitation-search", { value: "test1,test4,test5,test3" });
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
    await selectText(".o-discuss-ChannelInvitation-search", { start: 0, end: 0 });
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test3\ntest4",
    });
    await contains(".o-discuss-ChannelInvitation-search", { value: "test3,test4,test1,test2" });
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
    await selectText(".o-discuss-ChannelInvitation-search", { start: 11, end: 11 });
    await pasteMulti(".o-discuss-ChannelInvitation-search", {
        "text/plain": "test3\ntest4",
    });
    await contains(".o-discuss-ChannelInvitation-search", { value: "test1,test2,test3,test4" });
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
    await contains(".o-discuss-ChannelInvitation-search", { value: "test4,test5,test6" });
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
    await contains(".o-discuss-ChannelInvitation-search", { value: "test7,test8,test9" });
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
    await contains(".o-discuss-ChannelInvitation-search", { value: "test4,test5,test6" });
});

test("Empty lines filtered when pasting a list of emails (HTML) in the invite form", async () => {
    const htmlTableWithEmptyLines = `<table><tr><td>test1</td></tr>
                        <tr><td>test2</td></tr>
                        <tr><td></td></tr>
                        <tr><td>test3</td></tr>
                    </table>`;
    expect(parseHtmlClipboard(htmlTableWithEmptyLines)).toBe("test1,test2,test3");
});

test("Document with multiple tables should not be parsed", async () => {
    const htmlTableWithMultipleTables = `<table><tr><td>test1</td></tr>
                        <tr><td>test2</td></tr>
                        <tr><td>test3</td></tr>
                    </table>
                    <table><tr><td>test4</td></tr>
                        <tr><td>test5</td></tr>
                        <tr><td>test6</td></tr>
                    </table>`;
    expect(parseHtmlClipboard(htmlTableWithMultipleTables)).toBe(null);
});

test("Empty lines filtered when pasting a list of emails (plain text) in the invite form", async () => {
    const plainTextWithEmptyLines = "test1\n\ntest2\n test3";
    expect(parseTextClipboard(plainTextWithEmptyLines)).toBe("test1,test2,test3");
});

test("Lines should be trimmed when pasting a list of emails (HTML) in the invite form", async () => {
    const htmlTableWithSpaces = `<table><tr><td>test1</td></tr>
                        <tr><td> test2 </td></tr>
                        <tr><td>test3</td></tr>
                    </table>`;
    expect(parseHtmlClipboard(htmlTableWithSpaces)).toBe("test1,test2,test3");
});

test("Lines should be trimmed when pasting a list of emails (plain text) in the invite form", async () => {
    const plainTextWithSpaces = "test1\n test2 \n test3";
    expect(parseTextClipboard(plainTextWithSpaces)).toBe("test1,test2,test3");
});
