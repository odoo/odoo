import {
    actionPanel,
    click,
    contains as mailContains,
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
import { describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    Command,
    contains,
    getService,
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
    await selectText(".o-discuss-ChannelInvitation-search", { start: 1, end: 4 });
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
    await selectText(".o-discuss-ChannelInvitation-search", { start: 6, end: 11 });
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
    await selectText(".o-discuss-ChannelInvitation-search", { start: 0, end: 0 });
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
    await selectText(".o-discuss-ChannelInvitation-search", { start: 11, end: 11 });
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

test("Multi-word value on a single line should be kept as one term when pasting plain text", async () => {
    const plainTextWithMultiWordLine = "John Doe\nJane Smith";
    expect(parseTextClipboard(plainTextWithMultiWordLine)).toBe("John Doe,Jane Smith");
});

test("A comma inside a pasted HTML cell is joined as-is, without escaping", async () => {
    const htmlTableWithComma = `<table><tr><td>Doe, John</td></tr>
                        <tr><td>alice@example.com</td></tr>
                    </table>`;
    expect(parseHtmlClipboard(htmlTableWithComma)).toBe("Doe, John,alice@example.com");
});

test("A comma inside a pasted plain text line is joined as-is, without escaping", async () => {
    const plainTextWithComma = "Doe, John\nalice@example.com";
    expect(parseTextClipboard(plainTextWithComma)).toBe("Doe, John,alice@example.com");
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
    await waitFor(".o-discuss-ChannelInvitation-selectable:has(:text('Demo Partner')):count(1)");
    await waitFor(".o-discuss-ChannelInvitation-selectable:has(:text('new1@test.com')):count(1)");
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
