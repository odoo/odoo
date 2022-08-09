/** @odoo-module **/

import {
    afterNextRender,
    isScrolledToBottom,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { destroy } from '@web/../tests/helpers/utils';

import { makeTestPromise, file } from 'web.test_utils';

import { makeFakePresenceService } from '@bus/../tests/helpers/mock_services';

const { createFile, inputFiles } = file;

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_tests.js');

QUnit.test('messaging not created', async function (assert) {
    assert.expect(1);

    const messagingBeforeCreationDeferred = makeTestPromise();
    const { openDiscuss } = await start({
        messagingBeforeCreationDeferred,
        waitUntilMessagingCondition: 'none'
    });
    await openDiscuss({ waitUntilMessagesLoaded: false });
    assert.containsOnce(document.body, '.o_DiscussContainer_spinner', "should display messaging not initialized");
    messagingBeforeCreationDeferred.resolve();
});

QUnit.test('discuss should be marked as opened if the component is already rendered and messaging becomes created afterwards', async function (assert) {
    assert.expect(1);

    const messagingBeforeCreationDeferred = makeTestPromise();
    const { env, openDiscuss } = await start({
        messagingBeforeCreationDeferred,
        waitUntilMessagingCondition: 'none',
    });
    await openDiscuss({ waitUntilMessagesLoaded: false });

    await afterNextRender(() => messagingBeforeCreationDeferred.resolve());
    const { messaging } = env.services.messaging.modelManager;
    assert.ok(
        messaging.discuss.discussView,
        "discuss should be marked as opened if the component is already rendered and messaging becomes created afterwards"
    );
});

QUnit.test('discuss should be marked as closed when the component is unmounted', async function (assert) {
    assert.expect(1);

    const { messaging, openDiscuss, webClient } = await start();
    await openDiscuss();

    await afterNextRender(() => destroy(webClient));
    assert.notOk(
        messaging.discuss.discussView,
        "discuss should be marked as closed when the component is unmounted"
    );
});

QUnit.test('messaging not initialized', async function (assert) {
    assert.expect(1);

    const { openDiscuss } = await start({
        async mockRPC(route) {
            if (route === '/mail/init_messaging') {
                await makeTestPromise(); // simulate messaging never initialized
            }
        },
        waitUntilMessagingCondition: 'created',
    });
    await openDiscuss({ waitUntilMessagesLoaded: false });
    assert.strictEqual(
        document.querySelectorAll('.o_DiscussContainer_spinner').length,
        1,
        "should display messaging not initialized"
    );
});

QUnit.test('messaging becomes initialized', async function (assert) {
    assert.expect(2);

    const messagingInitializedProm = makeTestPromise();

    const { openDiscuss } = await start({
        async mockRPC(route) {
            if (route === '/mail/init_messaging') {
                await messagingInitializedProm;
            }
        },
        waitUntilMessagingCondition: 'created',
    });
    await openDiscuss({ waitUntilMessagesLoaded: false });
    assert.strictEqual(
        document.querySelectorAll('.o_DiscussContainer_spinner').length,
        1,
        "should display messaging not initialized"
    );

    await afterNextRender(() => messagingInitializedProm.resolve());
    assert.strictEqual(
        document.querySelectorAll('.o_DiscussContainer_spinner').length,
        0,
        "should no longer display messaging not initialized"
    );
});

QUnit.test('basic rendering', async function (assert) {
    assert.expect(4);

    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll('.o_Discuss_sidebar').length,
        1,
        "should have a sidebar section"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Discuss_content').length,
        1,
        "should have content section"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Discuss_thread').length,
        1,
        "should have thread section inside content"
    );
    assert.ok(
        document.querySelector('.o_Discuss_thread').classList.contains('o_ThreadView'),
        "thread section should use ThreadView component"
    );
});

QUnit.test('basic rendering: sidebar', async function (assert) {
    assert.expect(18);

    const { messaging, openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_category`).length,
        3,
        "should have 3 groups in sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryMailbox`).length,
        1,
        "should have group 'Mailbox' in sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryMailbox .o_DiscussSidebarMailbox
        `).length,
        3,
        "should have 3 mailbox items"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryMailbox
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `).length,
        1,
        "should have inbox mailbox item"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryMailbox
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
        `).length,
        1,
        "should have starred mailbox item"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryMailbox
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.history.localId
            }"]
        `).length,
        1,
        "should have history mailbox item"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_sidebar .o_DiscussSidebar_separator`).length,
        2,
        "should have 2 separators (separating 'Start a meeting' button, mailboxes and channels, but that's not tested)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel`).length,
        1,
        "should have group 'Channel' in sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header
        `).length,
        1,
        "should have header in channel group"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_titleText
        `).textContent.trim(),
        "Channels"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_content`).length,
        1,
        "channel category should list items"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`).length,
        0,
        "channel category should have no item by default"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat`).length,
        1,
        "should have group 'Chat' in sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_header`).length,
        1,
        "channel category should have a header"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).length,
        1,
        "should have title in chat header"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title .o_DiscussSidebarCategory_titleText
        `).textContent.trim(),
        "Direct Messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_content`).length,
        1,
        "chat category should list items"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_item`).length,
        0,
        "chat category should have no item by default"
    );
});

QUnit.test('sidebar: basic mailbox rendering', async function (assert) {
    assert.expect(5);

    const { messaging, openDiscuss } = await start();
    await openDiscuss();
    const inbox = document.querySelector(`
        .o_DiscussSidebar_categoryMailbox
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.inbox.localId
        }"]
    `);
    assert.strictEqual(
        inbox.querySelectorAll(`:scope .o_ThreadIcon`).length,
        1,
        "mailbox should have an icon"
    );
    assert.strictEqual(
        inbox.querySelectorAll(`:scope .o_ThreadIcon_mailboxInbox`).length,
        1,
        "inbox should have 'inbox' icon"
    );
    assert.strictEqual(
        inbox.querySelectorAll(`:scope .o_DiscussSidebarMailbox_name`).length,
        1,
        "mailbox should have a name"
    );
    assert.strictEqual(
        inbox.querySelector(`:scope .o_DiscussSidebarMailbox_name`).textContent,
        "Inbox",
        "inbox should have name 'Inbox'"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).length,
        0,
        "should have no counter when equal to 0 (default value)"
    );
});

QUnit.test('sidebar: default active inbox', async function (assert) {
    assert.expect(1);

    const { messaging, openDiscuss } = await start();
    await openDiscuss();
    const inbox = document.querySelector(`
        .o_DiscussSidebar_categoryMailbox
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.inbox.localId
        }"]
    `);
    assert.ok(
        inbox.classList.contains('o-active'),
        "inbox should be active by default"
    );
});

QUnit.test('sidebar: change item', async function (assert) {
    assert.expect(4);

    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `).classList.contains('o-active'),
        "inbox should be active by default"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
        `).classList.contains('o-active'),
        "starred should be inactive by default"
    );

    await click(`
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.starred.localId
        }"]
    `);
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `).classList.contains('o-active'),
        "inbox mailbox should become inactive"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
        `).classList.contains('o-active'),
        "starred mailbox should become active");
});

QUnit.test('sidebar: inbox with counter', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['mail.notification'].create({ notification_type: 'inbox', res_partner_id: pyEnv.currentPartnerId });
    const { messaging, openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).length,
        1,
        "should display a counter (= have a counter when different from 0)"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).textContent,
        "1",
        "should have counter value"
    );
});

QUnit.test('sidebar: add channel', async function (assert) {
    assert.expect(3);

    const { click, openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryChannel
            .o_DiscussSidebarCategory_commandAdd
        `).length,
        1,
        "should be able to add channel from header"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_categoryChannel
            .o_DiscussSidebarCategory_commandAdd
        `).title,
        "Add or join a channel");

    await click(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_commandAdd`);
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_addingItemInput`).length,
        1,
        "should have item to add a new channel"
    );
});

QUnit.test('sidebar: basic channel rendering', async function (assert) {
    assert.expect(12);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "General" });
    const { click, openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`).length,
        1,
        "should have one channel item");
    let channel = document.querySelector(`
        .o_DiscussSidebar_categoryChannel
        .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
    `);
    assert.ok(
        channel,
        'channel 1 should be in sidebar'
    );
    assert.notOk(
        channel.classList.contains('o-active'),
        "should not be active by default"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_name`).length,
        1,
        "should have a name"
    );
    assert.strictEqual(
        channel.querySelector(`:scope .o_DiscussSidebarCategoryItem_name`).textContent,
        "General",
        "should have name value"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_commands`).length,
        1,
        "should have commands"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_command`).length,
        2,
        "should have 2 commands"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_commandSettings`).length,
        1,
        "should have 'settings' command"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_commandLeave`).length,
        1,
        "should have 'leave' command"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_counter`).length,
        0,
        "should have a counter when equals 0 (default value)"
    );

    await click(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`);
    channel = document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`);
    assert.hasClass(
        channel,
        'o-active',
        "channel should become active"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_ThreadView_composer`).length,
        1,
        "should have composer section inside thread content (can post message in channel)"
    );
});

QUnit.test('sidebar: channel rendering with needaction counter', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: "mail.channel",
        res_id: mailChannelId1
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1, // id of related message
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId, // must be for current partner
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    const channel = document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`);
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_counter`).length,
        1,
        "should have a counter when different from 0"
    );
    assert.strictEqual(
        channel.querySelector(`:scope .o_DiscussSidebarCategoryItem_counter`).textContent,
        "1",
        "should have counter value"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_command`).length,
        1,
        "should have single command"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_commandSettings`).length,
        1,
        "should have 'settings' command"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_commandLeave`).length,
        0,
        "should not have 'leave' command"
    );
});

QUnit.test('sidebar: public/private channel rendering', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        { name: "channel1", public: 'public' },
        { name: "channel2", public: 'private' },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`).length,
        2,
        "should have 2 channel items"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryChannel
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
        `).length,
        1,
        "should have channel 1"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryChannel
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
        `).length,
        1,
        "should have channel 2"
    );
    const channel1 = document.querySelector(`
        .o_DiscussSidebar_categoryChannel
        .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
    `);
    const channel2 = document.querySelector(`
        .o_DiscussSidebar_categoryChannel
        .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
    `);
    assert.ok(
        channel1.querySelectorAll(`:scope .o_ThreadIcon_channelPublic`).length,
        "channel1 (public) should have globe icon"
    );
    assert.strictEqual(
        channel2.querySelectorAll(`:scope .o_ThreadIcon_channelPrivate`).length,
        1,
        "channel2 (private) has lock icon"
    );
});

QUnit.test('sidebar: basic chat rendering', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat', // testing a chat is the goal of the test
        public: 'private', // expected value for testing a chat
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_item`).length,
        1,
        "should have one chat item"
    );
    const chat = document.querySelector(`
        .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
    `);
    assert.ok(chat, "should have channel 1 in the sidebar");
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_ThreadIcon`).length,
        1,
        "should have an icon"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_name`).length,
        1,
        "should have a name"
    );
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarCategoryItem_name`).textContent,
        "Demo",
        "should have correspondent name as name"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_commands`).length,
        1,
        "should have commands"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_command`).length,
        1,
        "should have 1 command"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_commandUnpin`).length,
        1,
        "should have 'unpin' command"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_counter`).length,
        0,
        "should have a counter when equals 0 (default value)"
    );
});

QUnit.test('sidebar: chat rendering with unread counter', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, {
                message_unread_counter: 100,
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
        channel_type: 'chat',
        public: 'private',
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    const chat = document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_item`);
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_counter`).length,
        1,
        "should have a counter when different from 0"
    );
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarCategoryItem_counter`).textContent,
        "100",
        "should have counter value"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_command`).length,
        0,
        "should have no command"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_commandUnpin`).length,
        0,
        "should not have 'unpin' command"
    );
});

QUnit.test('sidebar: chat im_status rendering', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2, resPartnerId3] = pyEnv['res.partner'].create([
        { im_status: 'offline', name: "Partner1" },
        { im_status: 'online', name: "Partner2" },
        { im_status: 'away', name: "Partner3" },
    ]);
    const [mailChannelId1, mailChannelId2, mailChannelId3] = pyEnv['mail.channel'].create([
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
            channel_type: 'chat',
            public: 'private',
        },
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId2 }],
            ],
            channel_type: 'chat',
            public: 'private',
        },
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId3 }],
            ],
            channel_type: 'chat',
            public: 'private',
        }
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_item`).length,
        3,
        "should have 3 chat items"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryChat
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
        `).length,
        1,
        "should have Partner 1"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryChat
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
        `).length,
        1,
        "should have Partner 2"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_categoryChat
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId3}"]
        `).length,
        1,
        "should have Partner 3"
    );
    const chat1 = document.querySelector(`
        .o_DiscussSidebar_categoryChat
        .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
    `);
    const chat2 = document.querySelector(`
        .o_DiscussSidebar_categoryChat
        .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
    `);
    const chat3 = document.querySelector(`
        .o_DiscussSidebar_categoryChat
        .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId3}"]
    `);
    assert.strictEqual(
        chat1.querySelectorAll(`:scope .o_ThreadIcon_offline`).length,
        1,
        "chat1 should have offline icon"
    );
    assert.strictEqual(
        chat2.querySelectorAll(`:scope .o_ThreadIcon_online`).length,
        1,
        "chat2 should have online icon"
    );
    assert.strictEqual(
        chat3.querySelectorAll(`:scope .o_ThreadIcon_away`).length,
        1,
        "chat3 should have away icon"
    );
});

QUnit.test('sidebar: chat custom name', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Marc Demo" });
    pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, {
                custom_channel_name: "Marc",
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
        public: 'private',
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    const chat = document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_item`);
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarCategoryItem_name`).textContent,
        "Marc",
        "chat should have custom name as name"
    );
});

QUnit.test('default thread rendering', async function (assert) {
    assert.expect(16);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `).length,
        1,
        "should have inbox mailbox in the sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
        `).length,
        1,
        "should have starred mailbox in the sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.history.localId
            }"]
        `).length,
        1,
        "should have history mailbox in the sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
        `).length,
        1,
        "should have channel 1 in the sidebar"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `).classList.contains('o-active'),
        "inbox mailbox should be active thread"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_empty
        `).length,
        1,
        "should have empty thread in inbox"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_empty
        `).textContent.trim(),
        "Congratulations, your inbox is empty  New messages appear here."
    );

    await click(`
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.starred.localId
        }"]
    `);
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
        `).classList.contains('o-active'),
        "starred mailbox should be active thread"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_empty
        `).length,
        1,
        "should have empty thread in starred"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_empty
        `).textContent.trim(),
        "No starred messages  You can mark any message as 'starred', and it shows up in this mailbox."
    );

    await click(`
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.history.localId
        }"]
    `);
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.history.localId
            }"]
        `).classList.contains('o-active'),
        "history mailbox should be active thread"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_empty
        `).length,
        1,
        "should have empty thread in starred"
    );
    assert.strictEqual(
        document.querySelector(`.o_Discuss_thread .o_MessageList_empty`).textContent.trim(),
        "No history messages  Messages marked as read will appear in the history."
    );

    await click(`
        .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
    `);
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
        `).classList.contains('o-active'),
        "channel 20 should be active thread"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_empty
        `).length,
        1,
        "should have empty thread in starred"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_empty
        `).textContent.trim(),
        "There are no messages in this conversation."
    );
});

QUnit.test('initially load messages from inbox', async function (assert) {
    assert.expect(3);

    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/inbox/messages') {
                assert.step('/mail/channel/messages');
                assert.strictEqual(
                    args.limit,
                    30,
                    "should fetch up to 30 messages"
                );
            }
        },
    });
    await openDiscuss();
    assert.verifySteps(['/mail/channel/messages']);
});

QUnit.test('default select thread in discuss params', async function (assert) {
    assert.expect(1);

    const { messaging, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: 'mail.box_starred',
            },
        }
    });
    await openDiscuss();
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
        `).classList.contains('o-active'),
        "starred mailbox should become active"
    );
});

QUnit.test('auto-select thread in discuss context', async function (assert) {
    assert.expect(1);

    const { messaging, openDiscuss } = await start({
        discuss: {
            context: {
                active_id: 'mail.box_starred',
            },
        },
    });
    await openDiscuss();
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
        `).classList.contains('o-active'),
        "starred mailbox should become active"
    );
});

QUnit.test('load single message from channel initially', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        date: "2019-04-20 10:00:00",
        model: 'mail.channel',
        res_id: mailChannelId1
    });
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
        async mockRPC(route, args) {
            if (route === '/mail/channel/messages') {
                assert.strictEqual(
                    args.limit,
                    30,
                    "should fetch up to 30 messages"
                );
            }
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_ThreadView_messageList`).length,
        1,
        "should have list of messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_separatorDate`).length,
        1,
        "should have a single date separator" // to check: may be client timezone dependent
    );
    assert.strictEqual(
        document.querySelector(`.o_Discuss_thread .o_MessageList_separatorLabelDate`).textContent,
        "April 20, 2019",
        "should display date day of messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_message`).length,
        1,
        "should have a single message"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_MessageList_message[data-message-id="${mailMessageId1}"]
        `).length,
        1,
        "should have message with Id 100"
    );
});

QUnit.test('open channel from active_id as channel id', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { openDiscuss } = await start({
        discuss: {
            context: {
                active_id: mailChannelId1,
            },
        }
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        `
            .o_Discuss_thread[data-thread-id="${mailChannelId1}"][data-thread-model="mail.channel"]
        `,
        "should have channel 1 open in Discuss when providing its active_id"
    );
});

QUnit.test('basic rendering of message', async function (assert) {
    // AKU TODO: should be in message-only tests
    assert.expect(15);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        author_id: resPartnerId1,
        body: "<p>body</p>",
        date: "2019-04-20 10:00:00",
        model: 'mail.channel',
        res_id: mailChannelId1
    });
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    const message = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
        .o_MessageList_message[data-message-id="${mailMessageId1}"]
    `);
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_sidebar`).length,
        1,
        "should have message sidebar of message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_authorAvatar`).length,
        1,
        "should have author avatar in sidebar of message"
    );
    assert.strictEqual(
        message.querySelector(`:scope .o_Message_authorAvatar`).dataset.src,
        `/mail/channel/${mailChannelId1}/partner/${resPartnerId1}/avatar_128`,
        "should have url of message in author avatar sidebar"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_core`).length,
        1,
        "should have core part of message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_header`).length,
        1,
        "should have header in core part of message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_authorName`).length,
        1,
        "should have author name in header of message"
    );
    assert.strictEqual(
        message.querySelector(`:scope .o_Message_authorName`).textContent,
        "Demo",
        "should have textually author name in header of message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_header .o_Message_date`).length,
        1,
        "should have date in header of message"
    );

    await click('.o_Message');
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_MessageActionList`).length,
        1,
        "should action list in message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_MessageActionView`).length,
        3,
        "should have 3 actions in action list of message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_MessageActionView_actionToggleStar`).length,
        1,
        "should have action to star message"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageActionView_actionReaction',
        "should have action to add a reaction"
    );
    assert.containsOnce(
        message,
        '.o_MessageActionView_actionReplyTo',
        "should have action to reply to message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_content`).length,
        1,
        "should have content in core part of message"
    );
    assert.strictEqual(
        message.querySelector(`:scope .o_Message_content`).textContent.trim(),
        "body",
        "should have body of message in content part of message"
    );
});

QUnit.test('should not be able to reply to temporary/transient messages', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    // these user interactions is to forge a transient message response from channel command "/who"
    await insertText('.o_ComposerTextInput_textarea', "/who");
    await click('.o_Composer_buttonSend');
    // click on message to show actions on the transient message resulting from the "/who" command
    await click('.o_Message');
    assert.containsNone(
        document.body,
        '.o_MessageActionView_actionReplyTo',
        "should not have action to reply to temporary/transient messages"
    );
});

QUnit.test('basic rendering of squashed message', async function (assert) {
    // messages are squashed when "close", e.g. less than 1 minute has elapsed
    // from messages of same author and same thread. Note that this should
    // be working in non-mailboxes
    // AKU TODO: should be message and/or message list-only tests
    assert.expect(12);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        {
            author_id: resPartnerId1, // must be same author as other message
            body: "<p>body1</p>", // random body, set for consistency
            date: "2019-04-20 10:00:00", // date must be within 1 min from other message
            message_type: 'comment', // must be a squash-able type-
            model: 'mail.channel', // to link message to channel
            res_id: mailChannelId1, // id of related channel
        },
        {
            author_id: resPartnerId1, // must be same author as other message
            body: "<p>body2</p>", // random body, will be asserted in the test
            date: "2019-04-20 10:00:30", // date must be within 1 min from other message
            message_type: 'comment', // must be a squash-able type
            model: 'mail.channel', // to link message to channel
            res_id: mailChannelId1, // id of related channel
        }
    ]);
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        2,
        "should have 2 messages"
    );
    const message1 = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
        .o_MessageList_message[data-message-id="${mailMessageId1}"]
    `);
    const message2 = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
        .o_MessageList_message[data-message-id="${mailMessageId2}"]
    `);
    assert.notOk(
        message1.classList.contains('o-squashed'),
        "message 1 should not be squashed"
    );
    assert.notOk(
        message1.querySelector(`:scope .o_Message_sidebar`).classList.contains('o-message-squashed'),
        "message 1 should not have squashed sidebar"
    );
    assert.ok(
        message2.classList.contains('o-squashed'),
        "message 2 should be squashed"
    );
    assert.ok(
        message2.querySelector(`:scope .o_Message_sidebar`).classList.contains('o-message-squashed'),
        "message 2 should have squashed sidebar"
    );

    await click('.o_Message.o-squashed');
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_Message_sidebar .o_Message_date`).length,
        1,
        "message 2 should have date in sidebar"
    );
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_MessageActionList`).length,
        1,
        "message 2 should have some actions"
    );
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_MessageActionView_actionToggleStar`).length,
        1,
        "message 2 should have star action in action list"
    );
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_Message_core`).length,
        1,
        "message 2 should have core part"
    );
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_Message_header`).length,
        0,
        "message 2 should have a header in core part"
    );
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_Message_content`).length,
        1,
        "message 2 should have some content in core part"
    );
    assert.strictEqual(
        message2.querySelector(`:scope .o_Message_content`).textContent.trim(),
        "body2",
        "message 2 should have body in content part"
    );
});

QUnit.test('inbox messages are never squashed', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        {
            author_id: resPartnerId1, // must be same author as other message
            body: "<p>body1</p>", // random body, set for consistency
            date: "2019-04-20 10:00:00", // date must be within 1 min from other message
            message_type: 'comment', // must be a squash-able type-
            model: 'mail.channel', // to link message to channel
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId], // for consistency
            res_id: mailChannelId1, // id of related channel
        },
        {
            author_id: resPartnerId1, // must be same author as other message
            body: "<p>body2</p>", // random body, will be asserted in the test
            date: "2019-04-20 10:00:30", // date must be within 1 min from other message
            message_type: 'comment', // must be a squash-able type
            model: 'mail.channel', // to link message to channel
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId], // for consistency
            res_id: mailChannelId1, // id of related channel
        }
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1,
            notification_status: 'sent',
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId,
        }, {
            mail_message_id: mailMessageId2,
            notification_status: 'sent',
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });

    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        2,
        "should have 2 messages"
    );
    const message1 = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
        .o_MessageList_message[data-message-id="${mailMessageId1}"]
    `);
    const message2 = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
        .o_MessageList_message[data-message-id="${mailMessageId2}"]
    `);
    assert.notOk(
        message1.classList.contains('o-squashed'),
        "message 1 should not be squashed"
    );
    assert.notOk(
        message2.classList.contains('o-squashed'),
        "message 2 should not be squashed"
    );
});

QUnit.test('load all messages from channel initially, less than fetch limit (29 < 30)', async function (assert) {
    // AKU TODO: thread specific test
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['res.partner'].create({});
    for (let i = 28; i >= 0; i--) {
        pyEnv['mail.message'].create({
            author_id: resPartnerId1,
            body: "not empty",
            date: "2019-04-20 10:00:00",
            model: 'mail.channel',
            res_id: mailChannelId1,
        });
    }
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
        async mockRPC(route, args) {
            if (route === '/mail/channel/messages') {
                assert.strictEqual(args.limit, 30, "should fetch up to 30 messages");
            }
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_separatorDate
        `).length,
        1,
        "should have a single date separator" // to check: may be client timezone dependent
    );
    assert.strictEqual(
        document.querySelector(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_separatorLabelDate
        `).textContent,
        "April 20, 2019",
        "should display date day of messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        29,
        "should have 29 messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_loadMore
        `).length,
        0,
        "should not have load more link"
    );
});

QUnit.test('load more messages from channel', async function (assert) {
    // AKU: thread specific test
    assert.expect(6);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['res.partner'].create({});
    for (let i = 0; i < 40; i++) {
        pyEnv['mail.message'].create({
            author_id: resPartnerId1,
            body: "not empty",
            date: "2019-04-20 10:00:00",
            model: 'mail.channel',
            res_id: mailChannelId1,
        });
    }
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_separatorDate
        `).length,
        1,
        "should have a single date separator" // to check: may be client timezone dependent
    );
    assert.strictEqual(
        document.querySelector(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_separatorLabelDate
        `).textContent,
        "April 20, 2019",
        "should display date day of messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        30,
        "should have 30 messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_loadMore
        `).length,
        1,
        "should have load more link"
    );

    await click(`.o_Discuss_thread .o_ThreadView_messageList .o_MessageList_loadMore`);
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        40,
        "should have 40 messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_loadMore
        `).length,
        0,
        "should not longer have load more link (all messages loaded)"
    );
});

QUnit.test('auto-scroll to bottom of thread', async function (assert) {
    // AKU TODO: thread specific test
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    for (let i = 1; i <= 25; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: 'mail.channel',
            res_id: mailChannelId1,
        });
    }
    const { afterEvent, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: openDiscuss,
        message: "should wait until channel scrolled to its last message initially",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        25,
        "should have 25 messages"
    );
    const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
    assert.ok(
        isScrolledToBottom(messageList),
        "should have scrolled to bottom of thread"
    );
});

QUnit.test('load more messages from channel (auto-load on scroll)', async function (assert) {
    // AKU TODO: thread specific test
    assert.expect(3);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    for (let i = 0; i < 40; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: 'mail.channel',
            res_id: mailChannelId1,
        });
    }
    const { afterEvent, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: openDiscuss,
        message: "should wait until channel scrolled to its last message initially",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        30,
        "should have 30 messages"
    );

    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => document.querySelector('.o_ThreadView_messageList').scrollTop = 0,
        message: "should wait until channel loaded more messages after scrolling to top",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === mailChannelId1
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        40,
        "should have 40 messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Dsiscuss_thread .o_ThreadView_messageList .o_MessageList_loadMore
        `).length,
        0,
        "should not longer have load more link (all messages loaded)"
    );
});

QUnit.test('new messages separator [REQUIRE FOCUS]', async function (assert) {
    // this test requires several messages so that the last message is not
    // visible. This is necessary in order to display 'new messages' and not
    // remove from DOM right away from seeing last message.
    // AKU TODO: thread specific test
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Foreigner partner" });
    const resUsersId1 = pyEnv['res.users'].create({
        name: "Foreigner user",
        partner_id: resPartnerId1,
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({ uuid: 'randomuuid' });
    let lastMessageId;
    for (let i = 1; i <= 25; i++) {
        lastMessageId = pyEnv['mail.message'].create({
            body: "not empty",
            model: 'mail.channel',
            res_id: mailChannelId1,
        });
    }
    const [mailChannelMemberId] = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId1], ['partner_id', '=', pyEnv.currentPartnerId]]);
    pyEnv['mail.channel.member'].write([mailChannelMemberId], { seen_message_id: lastMessageId });
    const { afterEvent, messaging, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: openDiscuss,
        message: "should wait until channel scrolled to its last message initially",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    assert.containsN(
        document.body,
        '.o_MessageList_message',
        25,
        "should have 25 messages"
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should not display 'new messages' separator"
    );
    // scroll to top
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`).scrollTop = 0;
        },
        message: "should wait until channel scrolled to top",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                scrollTop === 0
            );
        },
    });
    // composer is focused by default, we remove that focus
    document.querySelector('.o_ComposerTextInput_textarea').blur();
    // simulate receiving a message
    await afterNextRender(async () => messaging.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: resUsersId1,
            },
            message_content: "hu",
            uuid: 'randomuuid',
        },
    }));

    assert.containsN(
        document.body,
        '.o_MessageList_message',
        26,
        "should have 26 messages"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should display 'new messages' separator"
    );
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
            messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
        },
        message: "should wait until channel scrolled to bottom",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should still display 'new messages' separator as composer is not focused"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ComposerTextInput_textarea').focus()
    );
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should no longer display 'new messages' separator (message seen)"
    );
});

QUnit.test('restore thread scroll position', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([{ name: 'Channel1' }, { name: 'Channel2' }]);
    for (let i = 1; i <= 25; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: 'mail.channel',
            res_id: mailChannelId1,
        });
    }
    for (let i = 1; i <= 24; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: 'mail.channel',
            res_id: mailChannelId2,
        });
    }
    const { afterEvent, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: openDiscuss,
        message: "should wait until channel 1 scrolled to its last message",
        predicate: ({ thread }) => {
            return thread && thread.channel && thread.channel.id === mailChannelId1;
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        25,
        "should have 25 messages in channel 1"
    );
    const initialMessageList = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
    `);
    assert.ok(
        isScrolledToBottom(initialMessageList),
        "should have scrolled to bottom of channel 1 initially"
    );

    await afterNextRender(() => afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`).scrollTop = 0,
        message: "should wait until channel 1 changed its scroll position to top",
        predicate: ({ thread }) => {
            return thread && thread.channel && thread.channel.id === mailChannelId1;
        },
    }));
    assert.strictEqual(
        document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`).scrollTop,
        0,
        "should have scrolled to top of channel 1",
    );

    // Ensure scrollIntoView of channel 2 has enough time to complete before
    // going back to channel 1. Await is needed to prevent the scrollIntoView
    // initially planned for channel 2 to actually apply on channel 1.
    // task-2333535
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            // select channel 2
            document.querySelector(`
                .o_DiscussSidebar_categoryChannel
                .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
            `).click();
        },
        message: "should wait until channel 2 scrolled to its last message",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                thread &&
                thread.channel &&
                thread.channel.id === mailChannelId2 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        24,
        "should have 24 messages in channel 2"
    );

    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            // select channel 1
            document.querySelector(`
                .o_DiscussSidebar_categoryChannel
                .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
            `).click();
        },
        message: "should wait until channel 1 restored its scroll position",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.channel &&
                thread.channel.id === mailChannelId1 &&
                scrollTop === 0
            );
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`).scrollTop,
        0,
        "should have recovered scroll position of channel 1 (scroll to top)"
    );

    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            // select channel 2
            document.querySelector(`
                .o_DiscussSidebar_categoryChannel
                .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
            `).click();
        },
        message: "should wait until channel 2 recovered its scroll position (to bottom)",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                thread &&
                thread.channel &&
                thread.channel.id === mailChannelId2 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    const messageList = document.querySelector('.o_ThreadView_messageList');
    assert.ok(
        isScrolledToBottom(messageList),
        "should have recovered scroll position of channel 2 (scroll to bottom)"
    );
});

QUnit.test('redirect to author (open chat)', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        { name: "General" },
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
            channel_type: 'chat',
            public: 'private',
        }
    ]);
    const mailMessageId1 = pyEnv['mail.message'].create(
        {
            author_id: resPartnerId1,
            body: "not empty",
            model: 'mail.channel',
            res_id: mailChannelId1,
        }
    );
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_categoryChannel
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
        `).classList.contains('o-active'),
        "channel 'General' should be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebar_categoryChat
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
        `).classList.contains('o-active'),
        "Chat 'Demo' should not be active"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_Message`).length,
        1,
        "should have 1 message"
    );
    const msg1 = document.querySelector(`
        .o_Discuss_thread
        .o_Message[data-message-id="${mailMessageId1}"]
    `);
    assert.strictEqual(
        msg1.querySelectorAll(`:scope .o_Message_authorAvatar`).length,
        1,
        "message1 should have author image"
    );
    assert.ok(
        msg1.querySelector(`:scope .o_Message_authorAvatar`).classList.contains('o_redirect'),
        "message1 should have redirect to author"
    );

    await afterNextRender(() =>
        msg1.querySelector(`:scope .o_Message_authorAvatar`).click()
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebar_categoryChannel
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId1}"]
        `).classList.contains('o-active'),
        "channel 'General' should become inactive after author redirection"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_categoryChat
            .o_DiscussSidebarCategory_item[data-channel-id="${mailChannelId2}"]
        `).classList.contains('o-active'),
        "chat 'Demo' should become active after author redirection"
    );
});

QUnit.test('sidebar quick search', async function (assert) {
    // feature enables at 20 or more channels
    assert.expect(6);

    const pyEnv = await startServer();
    for (let id = 1; id <= 20; id++) {
        pyEnv['mail.channel'].create({ name: `channel${id}` });
    }
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`).length,
        20,
        "should have 20 channel items"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_sidebar input.o_DiscussSidebar_quickSearch`).length,
        1,
        "should have quick search in sidebar"
    );

    const quickSearch = document.querySelector(`
        .o_Discuss_sidebar input.o_DiscussSidebar_quickSearch
    `);
    await afterNextRender(() => {
        quickSearch.value = "1";
        const kevt1 = new window.KeyboardEvent('input');
        quickSearch.dispatchEvent(kevt1);
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`).length,
        11,
        "should have filtered to 11 channel items"
    );

    await afterNextRender(() => {
        quickSearch.value = "12";
        const kevt2 = new window.KeyboardEvent('input');
        quickSearch.dispatchEvent(kevt2);
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`).length,
        1,
        "should have filtered to a single channel item"
    );
    assert.strictEqual(
        Number(document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`).dataset.channelId),
        pyEnv['mail.channel'].search([['name', '=', 'channel12']])[0],
        "should have filtered to a single channel (channel12)"
    );

    await afterNextRender(() => {
        quickSearch.value = "123";
        const kevt3 = new window.KeyboardEvent('input');
        quickSearch.dispatchEvent(kevt3);
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item`).length,
        0,
        "should have filtered to no channel item"
    );
});

QUnit.test('basic top bar rendering', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "General" });
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelector(`
            .o_ThreadViewTopbar_threadName
        `).textContent,
        "Inbox",
        "display inbox in the top bar"
    );
    const markAllReadButton = document.querySelector(`.o_ThreadViewTopbar_markAllReadButton`);
    assert.isVisible(
        markAllReadButton,
        "should have visible button 'Mark all read' in the top bar of inbox"
    );
    assert.ok(
        markAllReadButton.disabled,
        "should have disabled button 'Mark all read' in the top bar of inbox (no messages)"
    );

    await click(`
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.starred.localId
        }"]
    `);
    assert.strictEqual(
        document.querySelector(`
            .o_ThreadViewTopbar_threadName
        `).textContent,
        "Starred",
        "display starred in the breadcrumb"
    );
    const unstarAllButton = document.querySelector(`.o_ThreadViewTopbar_unstarAllButton`);
    assert.isVisible(
        unstarAllButton,
        "should have visible button 'Unstar all' in the top bar of starred"
    );
    assert.ok(
        unstarAllButton.disabled,
        "should have disabled button 'Unstar all' in the top bar of starred (no messages)"
    );

    await click(`
        .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
    `);
    assert.strictEqual(
        document.querySelector(`
            .o_ThreadViewTopbar_threadName
        `).textContent,
        "General",
        "display general in the breadcrumb"
    );
    const inviteButton = document.querySelector(`.o_ThreadViewTopbar_inviteButton`);
    assert.isVisible(
        inviteButton,
        "should have button 'Invite' in the top bar of channel"
    );
});

QUnit.test('inbox: mark all messages as read', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        {
            body: "not empty",
            model: 'mail.channel',
            needaction: true,
            res_id: mailChannelId1,
        },
        {
            body: "not empty",
            model: 'mail.channel',
            needaction: true,
            res_id: mailChannelId1,
        }
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1, // id of related message
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId, // must be for current partner
        },
        {
            mail_message_id: mailMessageId2, // id of related message
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId, // must be for current partner
        }
    ]);
    const { messaging, openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).textContent,
        "2",
        "inbox should have counter of 2"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
            .o_DiscussSidebarCategoryItem_counter
        `).textContent,
        "2",
        "channel should have counter of 2"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        2,
        "should have 2 messages in inbox"
    );
    let markAllReadButton = document.querySelector(`.o_ThreadViewTopbar_markAllReadButton`);
    assert.notOk(
        markAllReadButton.disabled,
        "should have enabled button 'Mark all read' in the top bar of inbox (has messages)"
    );

    await afterNextRender(() => markAllReadButton.click());
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).length,
        0,
        "inbox should display no counter (= 0)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
            .o_DiscussSidebarCategoryItem_counter
        `).length,
        0,
        "channel should display no counter (= 0)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        0,
        "should have no message in inbox"
    );
    markAllReadButton = document.querySelector(`.o_ThreadViewTopbar_markAllReadButton`);
    assert.ok(
        markAllReadButton.disabled,
        "should have disabled button 'Mark all read' in the top bar of inbox (no messages)"
    );
});

QUnit.test('starred: unstar all', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    pyEnv['mail.message'].create([
        { body: "not empty", starred_partner_ids: [pyEnv.currentPartnerId] },
        { body: "not empty", starred_partner_ids: [pyEnv.currentPartnerId] }
    ]);
    const { messaging, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: 'mail.box_starred',
            },
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).textContent,
        "2",
        "starred should have counter of 2"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        2,
        "should have 2 messages in starred"
    );
    let unstarAllButton = document.querySelector(`.o_ThreadViewTopbar_unstarAllButton`);
    assert.notOk(
        unstarAllButton.disabled,
        "should have enabled button 'Unstar all' in the top bar starred (has messages)"
    );

    await afterNextRender(() => unstarAllButton.click());
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).length,
        0,
        "starred should display no counter (= 0)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        0,
        "should have no message in starred"
    );
    unstarAllButton = document.querySelector(`.o_ThreadViewTopbar_unstarAllButton`);
    assert.ok(
        unstarAllButton.disabled,
        "should have disabled button 'Unstar all' in the top bar of starred (no messages)"
    );
});

QUnit.test('toggle_star message', async function (assert) {
    assert.expect(16);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const { messaging, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
        async mockRPC(route, args) {
            if (args.method === 'toggle_message_starred') {
                assert.step('rpc:toggle_message_starred');
                assert.strictEqual(
                    args.args[0][0],
                    mailMessageId1,
                    "should have message Id in args"
                );
            }
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).length,
        0,
        "starred should display no counter (= 0)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        1,
        "should have 1 message in channel"
    );
    let message = document.querySelector(`.o_Discuss .o_Message`);
    assert.notOk(
        message.classList.contains('o-starred'),
        "message should not be starred"
    );
    await afterNextRender(() => message.click());
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_MessageActionView_actionToggleStar`).length,
        1,
        "message should have star action"
    );

    await afterNextRender(() => message.querySelector(`:scope .o_MessageActionView_actionToggleStar`).click());
    assert.verifySteps(['rpc:toggle_message_starred']);
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).textContent,
        "1",
        "starred should display a counter of 1"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        1,
        "should have kept 1 message in channel"
    );
    message = document.querySelector(`.o_Discuss .o_Message`);
    assert.ok(
        message.classList.contains('o-starred'),
        "message should be starred"
    );

    await afterNextRender(() => message.querySelector(`:scope .o_MessageActionView_actionToggleStar`).click());
    assert.verifySteps(['rpc:toggle_message_starred']);
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.starred.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).length,
        0,
        "starred should no longer display a counter (= 0)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        1,
        "should still have 1 message in channel"
    );
    message = document.querySelector(`.o_Discuss .o_Message`);
    assert.notOk(
        message.classList.contains('o-starred'),
        "message should no longer be starred"
    );
});

QUnit.test('composer state: text save and restore', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const [mailChannelId1] = pyEnv['mail.channel'].create([
        { name: "General" },
        { name: "Special" },
    ]);
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    // Write text in composer for #general
    await insertText('.o_ComposerTextInput_textarea', "A message");
    await click(`.o_DiscussSidebarCategoryItem[data-channel-name="Special"]`);
    await insertText('.o_ComposerTextInput_textarea', "An other message");
    // Switch back to #general
    await click(`.o_DiscussSidebarCategoryItem[data-channel-name="General"]`);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "A message",
        "should restore the input text"
    );

    await click(`.o_DiscussSidebarCategoryItem[data-channel-name="Special"]`);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "An other message",
        "should restore the input text"
    );
});

QUnit.test('composer state: attachments save and restore', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [mailChannelId1] = pyEnv['mail.channel'].create([
        { name: "General" },
        { name: "Special" },
    ]);
    const { messaging, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    const channels = document.querySelectorAll(`
        .o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_item
    `);
    // Add attachment in a message for #general
    await afterNextRender(async () => {
        const file = await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        });
        inputFiles(
            messaging.discuss.threadView.composerView.fileUploader.fileInput,
            [file]
        );
    });
    // Switch to #special
    await afterNextRender(() => channels[1].click());
    // Add attachments in a message for #special
    const files = [
        await createFile({
            content: 'hello2, world',
            contentType: 'text/plain',
            name: 'text2.txt',
        }),
        await createFile({
            content: 'hello3, world',
            contentType: 'text/plain',
            name: 'text3.txt',
        }),
        await createFile({
            content: 'hello4, world',
            contentType: 'text/plain',
            name: 'text4.txt',
        }),
    ];
    await afterNextRender(() =>
        inputFiles(
            messaging.discuss.threadView.composerView.fileUploader.fileInput,
            files
        )
    );
    // Switch back to #general
    await afterNextRender(() => channels[0].click());
    // Check attachment is reloaded
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`).length,
        1,
        "should have 1 attachment in the composer"
    );
    assert.strictEqual(
        document.querySelector(`.o_Composer .o_AttachmentCard`).dataset.id,
        messaging.models['Attachment'].findFromIdentifyingData({ id: 1 }).localId,
        "should have correct 1st attachment in the composer"
    );

    // Switch back to #special
    await afterNextRender(() => channels[1].click());
    // Check attachments are reloaded
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`).length,
        3,
        "should have 3 attachments in the composer"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`)[0].dataset.id,
        messaging.models['Attachment'].findFromIdentifyingData({ id: 2 }).localId,
        "should have attachment with id 2 as 1st attachment"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`)[1].dataset.id,
        messaging.models['Attachment'].findFromIdentifyingData({ id: 3 }).localId,
        "should have attachment with id 3 as 2nd attachment"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_AttachmentCard`)[2].dataset.id,
        messaging.models['Attachment'].findFromIdentifyingData({ id: 4 }).localId,
        "should have attachment with id 4 as 3rd attachment"
    );
});

QUnit.test('post a simple message', async function (assert) {
    assert.expect(16);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('message_post');
                assert.strictEqual(
                    args.thread_model,
                    'mail.channel',
                    "should post message to channel"
                );
                assert.strictEqual(
                    args.thread_id,
                    mailChannelId1,
                    "should post message to channel 1"
                );
                assert.strictEqual(
                    args.post_data.body,
                    "Test",
                    "should post with provided content in composer input"
                );
                assert.strictEqual(
                    args.post_data.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
                assert.strictEqual(
                    args.post_data.subtype_xmlid,
                    "mail.mt_comment",
                    "should set subtype_xmlid as 'comment'"
                );
            }
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_MessageList_empty`).length,
        1,
        "should display thread with no message initially"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        0,
        "should display no message initially"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "should have empty content initially"
    );

    // insert some HTML in editable
    await insertText('.o_ComposerTextInput_textarea', "Test");
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "Test",
        "should have inserted text in editable"
    );

    await click('.o_Composer_buttonSend');
    assert.verifySteps(['message_post']);
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "",
        "should have no content in composer input after posting message"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        1,
        "should display a message after posting message"
    );
    const [postedMessageId] = pyEnv['mail.message'].search([], { order: 'id DESC' });
    const message = document.querySelector(`.o_Message`);
    assert.strictEqual(
        parseInt(message.dataset.messageId),
        postedMessageId,
        "new message in thread should be linked to newly created message from message post"
    );
    assert.strictEqual(
        message.querySelector(`:scope .o_Message_authorName`).textContent,
        "Mitchell Admin",
        "new message in thread should be from current partner name"
    );
    assert.strictEqual(
        message.querySelector(`:scope .o_Message_content`).textContent,
        "Test",
        "new message in thread should have content typed from composer text input"
    );
});

QUnit.test('post message on channel with "Enter" keyboard shortcut', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in channel"
    );

    // insert some HTML in editable
    await insertText('.o_ComposerTextInput_textarea', "Test");
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { key: "Enter" });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have single message in channel after posting message from pressing 'Enter' in text input of composer"
    );
});

QUnit.test('do not post message on channel with "SHIFT-Enter" keyboard shortcut', async function (assert) {
    // Note that test doesn't assert SHIFT-Enter makes a newline, because this
    // default browser cannot be simulated with just dispatching
    // programmatically crafted events...
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in channel"
    );

    // insert some HTML in editable
    await insertText('.o_ComposerTextInput_textarea', "Test");
    const kevt = new window.KeyboardEvent('keydown', { key: "Enter", shiftKey: true });
    document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_Message',
        "should still not have any message in channel after pressing 'Shift-Enter' in text input of composer"
    );
});
QUnit.test('rendering of inbox message', async function (assert) {
    // AKU TODO: kinda message specific test
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Refactoring" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId], // for consistency
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until inbox displayed its messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread === messaging.inbox.thread
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should display a message"
    );
    const message = document.querySelector('.o_Message');
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_originThread`).length,
        1,
        "should display origin thread of message"
    );
    assert.strictEqual(
        message.querySelector(`:scope .o_Message_originThread`).textContent,
        " on Refactoring",
        "should display origin thread name"
    );
    await afterNextRender(() => message.click());
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_MessageActionView`).length,
        4,
        "should display 4 actions"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageActionView_actionReaction',
        "should have action to add a reaction"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_MessageActionView_actionToggleStar`).length,
        1,
        "should display star action"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_MessageActionView_actionReplyTo`).length,
        1,
        "should display reply action"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_MessageActionView_actionMarkAsRead`).length,
        1,
        "should display mark as read action"
    );
});

QUnit.test('mark channel as seen on last message visible [REQUIRE FOCUS]', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, {
                message_unread_counter: 1,
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const { afterEvent, openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]`,
        "should have discuss sidebar item with the channel"
    );
    assert.hasClass(
        document.querySelector(`
            .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
        `),
        'o-unread',
        "sidebar item of channel 1 should be unread"
    );

    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
            `).click();
        },
        message: "should wait until last seen by current partner message id changed",
        predicate: ({ thread }) => {
            return (
                thread.channel &&
                thread.channel.id === mailChannelId1 &&
                thread.lastSeenByCurrentPartnerMessageId === mailMessageId1
            );
        },
    }));
    assert.doesNotHaveClass(
        document.querySelector(`
            .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
        `),
        'o-unread',
        "sidebar item of channel 1 should not longer be unread"
    );
});

QUnit.test('receive new needaction messages', async function (assert) {
    assert.expect(12);

    const { messaging, openDiscuss, pyEnv } = await start();
    await openDiscuss();
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `),
        "should have inbox in sidebar"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `).classList.contains('o-active'),
        "inbox should be current discuss thread"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `),
        "inbox item in sidebar should not have any counter"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_Message`).length,
        0,
        "should have no messages in inbox initially"
    );

    // simulate receiving a new needaction message
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(pyEnv.currentPartner, 'mail.message/inbox', {
            'body': "not empty",
            'id': 100,
            'needaction_partner_ids': [pyEnv.currentPartnerId],
            'model': 'res.partner',
            'res_id': 20,
        });
    });
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `),
        "inbox item in sidebar should now have counter"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).textContent,
        '1',
        "inbox item in sidebar should have counter of '1'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_Message`).length,
        1,
        "should have one message in inbox"
    );
    assert.strictEqual(
        parseInt(document.querySelector(`.o_Discuss_thread .o_Message`).dataset.messageId),
        100,
        "should display newly received needaction message"
    );

    // simulate receiving another new needaction message
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(pyEnv.currentPartner, 'mail.message/inbox', {
            'body': "not empty",
            'id': 101,
            'needaction_partner_ids': [pyEnv.currentPartnerId],
            'model': 'res.partner',
            'res_id': 20,
        });
    });
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
            .o_DiscussSidebarMailbox_counter
        `).textContent,
        '2',
        "inbox item in sidebar should have counter of '2'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_Message`).length,
        2,
        "should have 2 messages in inbox"
    );
    assert.ok(
        document.querySelector(`
            .o_Discuss_thread
            .o_Message[data-message-id="100"]
        `),
        "should still display 1st needaction message"
    );
    assert.ok(
        document.querySelector(`
            .o_Discuss_thread
            .o_Message[data-message-id="101"]
        `),
        "should display 2nd needaction message"
    );
});

QUnit.test('reply to message from inbox (message linked to document)', async function (assert) {
    assert.expect(19);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Refactoring" });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        message_type: 'comment',
        needaction: true,
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1, // id of related message
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId, // must be for current partner
    });
    const { click, insertText, openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('message_post');
                assert.strictEqual(
                    args.thread_model,
                    'res.partner',
                    "should post message to record with model 'res.partner'"
                );
                assert.strictEqual(
                    args.thread_id,
                    resPartnerId1,
                    "should post message to record with Id 20"
                );
                assert.strictEqual(
                    args.post_data.body,
                    "Test",
                    "should post with provided content in composer input"
                );
                assert.strictEqual(
                    args.post_data.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
            }
        },
        services: {
            notification: makeFakeNotificationService(notification => {
                assert.ok(
                    true,
                    "should display a notification after posting reply"
                );
                assert.strictEqual(
                    notification,
                    "Message posted on \"Refactoring\"",
                    "notification should tell that message has been posted to the record 'Refactoring'"
                );
            }),
        },
    });
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should display a single message"
    );
    assert.strictEqual(
        parseInt(document.querySelector('.o_Message').dataset.messageId),
        mailMessageId1,
        "should display message with ID 100"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_originThread').textContent,
        " on Refactoring",
        "should display message originates from record 'Refactoring'"
    );

    await click('.o_Message');
    await click('.o_MessageActionView_actionReplyTo');
    assert.ok(
        document.querySelector('.o_Message').classList.contains('o-selected'),
        "message should be selected after clicking on reply icon"
    );
    assert.ok(
        document.querySelector('.o_Composer'),
        "should have composer after clicking on reply to message"
    );
    assert.strictEqual(
        document.querySelector(`.o_Composer_threadName`).textContent,
        " on: Refactoring",
        "composer should display origin thread name of message"
    );
    assert.strictEqual(
        document.activeElement,
        document.querySelector(`.o_ComposerTextInput_textarea`),
        "composer text input should be auto-focus"
    );

    await insertText('.o_ComposerTextInput_textarea', "Test");
    await click('.o_Composer_buttonSend');
    assert.verifySteps(['message_post']);
    assert.notOk(
        document.querySelector('.o_Composer'),
        "should no longer have composer after posting reply to message"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should still display a single message after posting reply"
    );
    assert.strictEqual(
        parseInt(document.querySelector('.o_Message').dataset.messageId),
        mailMessageId1,
        "should still display message with ID 100 after posting reply"
    );
    assert.notOk(
        document.querySelector('.o_Message').classList.contains('o-selected'),
        "message should not longer be selected after posting reply"
    );
});

QUnit.test('messages marked as read move to "History" mailbox', async function (assert) {
    assert.expect(10);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        {
            body: "not empty",
            model: 'mail.channel', // value to link message to channel
            needaction: true,
            res_id: mailChannelId1, // id of related channel
        },
        {
            body: "not empty",
            model: 'mail.channel', // value to link message to channel
            needaction: true,
            res_id: mailChannelId1, // id of related channel
        }
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1, // id of related message
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId, // must be for current partner
        },
        {
            mail_message_id: mailMessageId2, // id of related message
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId, // must be for current partner
        }
    ]);
    const { click, messaging, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: 'mail.box_history',
            },
        },
    });
    await openDiscuss();
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.history.localId
            }"]
        `).classList.contains('o-active'),
        "history mailbox should be active thread"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_empty`).length,
        1,
        "should have empty thread in history"
    );

    await click(`
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.inbox.localId
        }"]
    `);
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `).classList.contains('o-active'),
        "inbox mailbox should be active thread"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_empty`).length,
        0,
        "inbox mailbox should not be empty"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_message`).length,
        2,
        "inbox mailbox should have 2 messages"
    );

    await click('.o_ThreadViewTopbar_markAllReadButton');
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `).classList.contains('o-active'),
        "inbox mailbox should still be active after mark as read"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_empty`).length,
        1,
        "inbox mailbox should now be empty after mark as read"
    );

    await click(`
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.history.localId
        }"]
    `);
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.history.localId
            }"]
        `).classList.contains('o-active'),
        "history mailbox should be active"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_empty`).length,
        0,
        "history mailbox should not be empty after mark as read"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_message`).length,
        2,
        "history mailbox should have 2 messages"
    );
});

QUnit.test('mark a single message as read should only move this message to "History" mailbox', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        {
            body: "not empty",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
        },
        {
            body: "not empty",
            needaction: true,
            needaction_partner_ids: [pyEnv.currentPartnerId],
        }
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1,
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: mailMessageId2,
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId,
        }
    ]);
    const { click, messaging, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: 'mail.box_history',
            },
        },
    });
    await openDiscuss();
    assert.hasClass(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.history.localId
            }"]
        `),
        'o-active',
        "history mailbox should initially be the active thread"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageList_empty',
        "history mailbox should initially be empty"
    );

    await click(`
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.inbox.localId
        }"]
    `);
    assert.hasClass(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.inbox.localId
            }"]
        `),
        'o-active',
        "inbox mailbox should be active thread after clicking on it"
    );
    assert.containsN(
        document.body,
        '.o_Message',
        2,
        "inbox mailbox should have 2 messages"
    );

    await click(`
        .o_Message[data-message-id="${mailMessageId1}"]
    `);
    await click(`
        .o_Message[data-message-id="${mailMessageId1}"] .o_MessageActionView_actionMarkAsRead
    `);
    assert.containsOnce(
        document.body,
        '.o_Message',
        "inbox mailbox should have one less message after clicking mark as read"
    );
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-id="${mailMessageId2}"]`,
        "message still in inbox should be the one not marked as read"
    );

    await click(`
        .o_DiscussSidebarMailbox[data-mailbox-local-id="${
            messaging.history.localId
        }"]
    `);
    assert.hasClass(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                messaging.history.localId
            }"]
        `),
        'o-active',
        "history mailbox should be active after clicking on it"
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "history mailbox should have only 1 message after mark as read"
    );
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-id="${mailMessageId1}"]`,
        "message moved in history should be the one marked as read"
    );
});

QUnit.test('all messages in "Inbox" in "History" after marked all as read', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    for (let i = 0; i < 40; i++) {
        const currentMailMessageId = pyEnv['mail.message'].create({
            body: "not empty",
            needaction: true,
        });
        pyEnv['mail.notification'].create({
            mail_message_id: currentMailMessageId, // id of related message
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId, // must be for current partner
        });

    }
    const { afterEvent, click, messaging, openDiscuss } = await start();
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: openDiscuss,
        message: "should wait until inbox scrolled to its last message initially",
        predicate: ({ orderedMessages, scrollTop, thread }) => {
            const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
            return (
                thread === messaging.inbox.thread &&
                orderedMessages.length === 30 &&
                isScrolledToBottom(messageList)
            );
        },
    });

    await click('.o_ThreadViewTopbar_markAllReadButton');
    assert.containsNone(
        document.body,
        '.o_Message',
        "there should no message in Inbox anymore"
    );

    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebarMailbox[data-mailbox-local-id="${
                    messaging.history.localId
                }"]
            `).click();
        },
        message: "should wait until history scrolled to its last message after opening it from the discuss sidebar",
        predicate: ({ orderedMessages, scrollTop, thread }) => {
            const messageList = document.querySelector('.o_MessageList');
            return (
                thread &&
                thread.mailbox &&
                thread.mailbox === messaging.history &&
                orderedMessages.length === 30 &&
                isScrolledToBottom(messageList)
            );
        },
    });

    // simulate a scroll to top to load more messages
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => document.querySelector('.o_MessageList').scrollTop = 0,
        message: "should wait until mailbox history loaded more messages after scrolling to top",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.mailbox &&
                threadViewer.thread.mailbox === messaging.history
            );
        },
    });
    assert.containsN(
        document.body,
        '.o_Message',
        40,
        "there should be 40 messages in History"
    );
});

QUnit.test('receive new chat message: out of odoo focus (notification, channel)', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ channel_type: 'chat' });
    const { env, openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    await openDiscuss();
    env.bus.on('set_title_part', null, payload => {
        assert.step('set_title_part');
        assert.strictEqual(payload.part, '_chat');
        assert.strictEqual(payload.title, "1 Message");
    });

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId1]])[0];
    // simulate receiving a new message with odoo focused
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel/new_message', {
            'id': mailChannelId1,
            'message': {
                id: 126,
                model: 'mail.channel',
                res_id: mailChannelId1,
            },
        });
    });
    assert.verifySteps(['set_title_part']);
});

QUnit.test('receive new chat message: out of odoo focus (notification, chat)', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ channel_type: "chat" });
    const { env, openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    await openDiscuss();
    env.bus.on('set_title_part', null, payload => {
        assert.step('set_title_part');
        assert.strictEqual(payload.part, '_chat');
        assert.strictEqual(payload.title, "1 Message");
    });

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId1]])[0];
    // simulate receiving a new message with odoo focused
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel/new_message', {
            'id': mailChannelId1,
            'message': {
                id: 126,
                model: 'mail.channel',
                res_id: mailChannelId1,
            },
        });
    });
    assert.verifySteps(['set_title_part']);
});

QUnit.test('receive new chat messages: out of odoo focus (tab title)', async function (assert) {
    assert.expect(12);

    let step = 0;
    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        { channel_type: 'chat', public: 'private' },
        { channel_type: 'chat', public: 'private' },
    ]);
    const { env, openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    await openDiscuss();
    env.bus.on('set_title_part', null, payload => {
        step++;
        assert.step('set_title_part');
        assert.strictEqual(payload.part, '_chat');
        if (step === 1) {
            assert.strictEqual(payload.title, "1 Message");
        }
        if (step === 2) {
            assert.strictEqual(payload.title, "2 Messages");
        }
        if (step === 3) {
            assert.strictEqual(payload.title, "3 Messages");
        }
    });

    const mailChannel1 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId1]])[0];
    // simulate receiving a new message in chat 1 with odoo focused
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel1, 'mail.channel/new_message', {
            'id': mailChannelId1,
            'message': {
                id: 126,
                model: 'mail.channel',
                res_id: mailChannelId1,
            },
        });
    });
    assert.verifySteps(['set_title_part']);

    const mailChannel2 = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId2]])[0];
    // simulate receiving a new message in chat 2 with odoo focused
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel2, 'mail.channel/new_message', {
            'id': mailChannelId2,
            'message': {
                id: 127,
                model: 'mail.channel',
                res_id: mailChannelId2,
            },
        });
    });
    assert.verifySteps(['set_title_part']);

    // simulate receiving another new message in chat 2 with odoo focused
    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(mailChannel2, 'mail.channel/new_message', {
            'id': mailChannelId2,
            'message': {
                id: 128,
                model: 'mail.channel',
                res_id: mailChannelId2,
            },
        });
    });
    assert.verifySteps(['set_title_part']);
});

QUnit.test('auto-focus composer on opening thread', async function (assert) {
    assert.expect(14);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo User" });
    pyEnv['mail.channel'].create([
        { name: "General" },
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
            channel_type: 'chat',
            public: 'private',
        }
    ]);
    const { click, openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarMailbox[data-mailbox-name="Inbox"]
        `).length,
        1,
        "should have mailbox 'Inbox' in the sidebar"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarMailbox[data-mailbox-name="Inbox"]
        `).classList.contains('o-active'),
        "mailbox 'Inbox' should be active initially"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarCategoryItem[data-channel-name="General"]
        `).length,
        1,
        "should have channel 'General' in the sidebar"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebarCategoryItem[data-channel-name="General"]
        `).classList.contains('o-active'),
        "channel 'General' should not be active initially"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebarCategoryItem[data-channel-name="Demo User"]
        `).length,
        1,
        "should have chat 'Demo User' in the sidebar"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebarCategoryItem[data-channel-name="Demo User"]
        `).classList.contains('o-active'),
        "chat 'Demo User' should not be active initially"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer`).length,
        0,
        "there should be no composer when active thread of discuss is mailbox 'Inbox'"
    );

    await click(`.o_DiscussSidebarCategoryItem[data-channel-name="General"]`);
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarCategoryItem[data-channel-name="General"]
        `).classList.contains('o-active'),
        "channel 'General' should become active after selecting it from the sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer`).length,
        1,
        "there should be a composer when active thread of discuss is channel 'General'"
    );
    assert.strictEqual(
        document.activeElement,
        document.querySelector(`.o_ComposerTextInput_textarea`),
        "composer of channel 'General' should be automatically focused on opening"
    );

    document.querySelector(`.o_ComposerTextInput_textarea`).blur();
    assert.notOk(
        document.activeElement === document.querySelector(`.o_ComposerTextInput_textarea`),
        "composer of channel 'General' should no longer focused on click away"
    );

    await click(`.o_DiscussSidebarCategoryItem[data-channel-name="Demo User"]`);
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebarCategory_item[data-channel-name="Demo User"]
        `).classList.contains('o-active'),
        "chat 'Demo User' should become active after selecting it from the sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer`).length,
        1,
        "there should be a composer when active thread of discuss is chat 'Demo User'"
    );
    assert.strictEqual(
        document.activeElement,
        document.querySelector(`.o_ComposerTextInput_textarea`),
        "composer of chat 'Demo User' should be automatically focused on opening"
    );
});

QUnit.test('mark channel as seen if last message is visible when switching channels when the previous channel had a more recent last message than the current channel [REQUIRE FOCUS]', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        {
            channel_member_ids: [
                [0, 0, {
                    message_unread_counter: 1,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
            name: 'Bla',
        },
        {
            channel_member_ids: [
                [0, 0, {
                    message_unread_counter: 1,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
            name: 'Blu',
        },
    ]);
    const [mailMessageId1] = pyEnv['mail.message'].create([{
        body: 'oldest message',
        model: "mail.channel",
        res_id: mailChannelId1,
    }, {
        body: 'newest message',
        model: "mail.channel",
        res_id: mailChannelId2,
    }]);
    const { afterEvent, openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId2}`,
            },
        },
    });
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: openDiscuss,
        message: "should wait until channel 2 loaded its messages initially",
        predicate: ({ hint, threadViewer }) => {
            return (
                threadViewer.thread.channel &&
                threadViewer.thread.channel.id === mailChannelId2 &&
                hint.type === 'messages-loaded'
            );
        },
    });
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
            `).click();
        },
        message: "should wait until last seen by current partner message id changed",
        predicate: ({ thread }) => {
            return (
                thread.channel &&
                thread.channel.id === mailChannelId1 &&
                thread.lastSeenByCurrentPartnerMessageId === mailMessageId1
            );
        },
    }));
    assert.doesNotHaveClass(
        document.querySelector(`
            .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
        `),
        'o-unread',
        "sidebar item of channel 1 should no longer be unread"
    );
});

QUnit.test('warning on send with shortcut when attempting to post message with still-uploading attachments', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { messaging, openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId1}`,
            },
        },
        async mockRPC(route) {
            if (route === '/mail/attachment/upload') {
                // simulates attachment is never finished uploading
                await new Promise(() => {});
            }
        },
        services: {
            notification: makeFakeNotificationService((message, options) => {
                assert.strictEqual(
                    message,
                    "Please wait while the file is uploading.",
                    "notification content should be about the uploading file"
                );
                assert.strictEqual(
                    options.type,
                    'warning',
                    "notification should be a warning"
                );
                assert.step('notification');
            }),
        },
    });
    await openDiscuss();
    const file = await createFile({
        content: 'hello, world',
        contentType: 'text/plain',
        name: 'text.txt',
    });
    await afterNextRender(() =>
        inputFiles(
            messaging.discuss.threadView.composerView.fileUploader.fileInput,
            [file]
        )
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard',
        "should have only one attachment"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard.o-isUploading',
        "attachment displayed is being uploaded"
    );
    assert.containsOnce(
        document.body,
        '.o_Composer_buttonSend',
        "composer send button should be displayed"
    );

    // Try to send message
    document
        .querySelector(`.o_ComposerTextInput_textarea`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }));
    assert.verifySteps(
        ['notification'],
        "should have triggered a notification for inability to post message at the moment (some attachments are still being uploaded)"
    );
});

QUnit.test('send message only once when enter is pressed twice quickly', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { insertText, openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId1}`,
            },
        },
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('message_post');
            }
        },
    });
    await openDiscuss();
    // Type message
    await insertText('.o_ComposerTextInput_textarea', "test message");
    await afterNextRender(() => {
        const enterEvent = new window.KeyboardEvent('keydown', { key: 'Enter' });
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(enterEvent);
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(enterEvent);
    });
    assert.verifySteps(
        ['message_post'],
        "The message has been posted only once"
    );
});

QUnit.test('message being a replied to another message should show message being replied in the message view', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: "1st message",
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const mailMessageId2 = pyEnv['mail.message'].create({
        body: "2nd message",
        model: 'mail.channel',
        parent_id: mailMessageId1,
        res_id: mailChannelId1,
    });
    const { openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.querySelector(`.o_Message[data-message-id="${mailMessageId2}"]`),
        '.o_MessageInReplyToView',
        "message being a replied to another message should show message being replied in the message view",
    );
});

});
});
