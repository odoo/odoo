odoo.define('mail/static/src/components/discuss/tests/discuss_tests.js', function (require) {
'use strict';

const BusService = require('bus.BusService');

const {
    afterEach,
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
    start,
} = require('mail/static/src/utils/test_utils.js');

const Bus = require('web.Bus');
const { makeTestPromise, file: { createFile, inputFiles } } = require('web.test_utils');

const {
    applyFilter,
    toggleAddCustomFilter,
    toggleFilterMenu,
} = require('web.test_utils_control_panel');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { afterEvent, env, widget } = await start(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.afterEvent = afterEvent;
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('messaging not initialized', async function (assert) {
    assert.expect(1);

    await this.start({
        async mockRPC(route) {
            const _super = this._super.bind(this, ...arguments); // limitation of class.js
            if (route === '/mail/init_messaging') {
                await makeTestPromise(); // simulate messaging never initialized
            }
            return _super();
        },
        waitUntilMessagingCondition: 'created',
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Discuss_messagingNotInitialized').length,
        1,
        "should display messaging not initialized"
    );
});

QUnit.test('messaging becomes initialized', async function (assert) {
    assert.expect(2);

    const messagingInitializedProm = makeTestPromise();

    await this.start({
        async mockRPC(route) {
            const _super = this._super.bind(this, ...arguments); // limitation of class.js
            if (route === '/mail/init_messaging') {
                await messagingInitializedProm;
            }
            return _super();
        },
        waitUntilMessagingCondition: 'created',
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Discuss_messagingNotInitialized').length,
        1,
        "should display messaging not initialized"
    );

    await afterNextRender(() => messagingInitializedProm.resolve());
    assert.strictEqual(
        document.querySelectorAll('.o_Discuss_messagingNotInitialized').length,
        0,
        "should no longer display messaging not initialized"
    );
});

QUnit.test('basic rendering', async function (assert) {
    assert.expect(4);

    await this.start();
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
    assert.expect(20);

    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_group`).length,
        3,
        "should have 3 groups in sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupMailbox`).length,
        1,
        "should have group 'Mailbox' in sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupMailbox .o_DiscussSidebar_groupHeader
        `).length,
        0,
        "mailbox category should not have any header"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupMailbox .o_DiscussSidebar_item
        `).length,
        3,
        "should have 3 mailbox items"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupMailbox
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
        `).length,
        1,
        "should have inbox mailbox item"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupMailbox
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
        `).length,
        1,
        "should have starred mailbox item"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupMailbox
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
            }"]
        `).length,
        1,
        "should have history mailbox item"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_sidebar .o_DiscussSidebar_separator`).length,
        1,
        "should have separator (between mailboxes and channels, but that's not tested)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel`).length,
        1,
        "should have group 'Channel' in sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupChannel .o_DiscussSidebar_groupHeader
        `).length,
        1,
        "channel category should have a header"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupChannel .o_DiscussSidebar_groupTitle
        `).length,
        1,
        "should have title in channel header"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel .o_DiscussSidebar_groupTitle
        `).textContent.trim(),
        "Channels"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_list`).length,
        1,
        "channel category should list items"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`).length,
        0,
        "channel category should have no item by default"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChat`).length,
        1,
        "should have group 'Chat' in sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_groupHeader`).length,
        1,
        "channel category should have a header"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_groupTitle`).length,
        1,
        "should have title in chat header"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_groupChat .o_DiscussSidebar_groupTitle
        `).textContent.trim(),
        "Direct Messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_list`).length,
        1,
        "chat category should list items"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_item`).length,
        0,
        "chat category should have no item by default"
    );
});

QUnit.test('sidebar: basic mailbox rendering', async function (assert) {
    assert.expect(6);

    await this.start();
    const inbox = document.querySelector(`
        .o_DiscussSidebar_groupMailbox
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.messaging.inbox.localId
        }"]
    `);
    assert.strictEqual(
        inbox.querySelectorAll(`:scope .o_DiscussSidebarItem_activeIndicator`).length,
        1,
        "mailbox should have active indicator"
    );
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
        inbox.querySelectorAll(`:scope .o_DiscussSidebarItem_name`).length,
        1,
        "mailbox should have a name"
    );
    assert.strictEqual(
        inbox.querySelector(`:scope .o_DiscussSidebarItem_name`).textContent,
        "Inbox",
        "inbox should have name 'Inbox'"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
        `).length,
        0,
        "should have no counter when equal to 0 (default value)"
    );
});

QUnit.test('sidebar: default active inbox', async function (assert) {
    assert.expect(1);

    await this.start();
    const inbox = document.querySelector(`
        .o_DiscussSidebar_groupMailbox
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.messaging.inbox.localId
        }"]
    `);
    assert.ok(
        inbox.querySelector(`
            :scope .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "inbox should be active by default"
    );
});

QUnit.test('sidebar: change item', async function (assert) {
    assert.expect(4);

    await this.start();
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "inbox should be active by default"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "starred should be inactive by default"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
        `).click()
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "inbox mailbox should become inactive"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "starred mailbox should become active");
});

QUnit.test('sidebar: inbox with counter', async function (assert) {
    assert.expect(2);

    // notification expected to be counted at init_messaging
    this.data['mail.notification'].records.push({ res_partner_id: this.data.currentPartnerId });
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
        `).length,
        1,
        "should display a counter (= have a counter when different from 0)"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
        `).textContent,
        "1",
        "should have counter value"
    );
});

QUnit.test('sidebar: add channel', async function (assert) {
    assert.expect(3);

    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_groupHeaderItemAdd
        `).length,
        1,
        "should be able to add channel from header"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_groupHeaderItemAdd
        `).title,
        "Add or join a channel");

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_groupChannel .o_DiscussSidebar_groupHeaderItemAdd
        `).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_itemNew`).length,
        1,
        "should have item to add a new channel"
    );
});

QUnit.test('sidebar: basic channel rendering', async function (assert) {
    assert.expect(14);

    // channel expected to be found in the sidebar,
    // with a random unique id and name that  will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20, name: "General" });
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`).length,
        1,
        "should have one channel item");
    let channel = document.querySelector(`
        .o_DiscussSidebar_groupChannel
        .o_DiscussSidebar_item
    `);
    assert.strictEqual(
        channel.dataset.threadLocalId,
        this.env.models['mail.thread'].find(thread =>
            thread.id === 20 &&
            thread.model === 'mail.channel'
        ).localId,
        "should have channel with Id 20"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_activeIndicator`).length,
        1,
        "should have active indicator"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_activeIndicator.o-item-active`).length,
        0,
        "should not be active by default"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_ThreadIcon`).length,
        1,
        "should have an icon"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_name`).length,
        1,
        "should have a name"
    );
    assert.strictEqual(
        channel.querySelector(`:scope .o_DiscussSidebarItem_name`).textContent,
        "General",
        "should have name value"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_commands`).length,
        1,
        "should have commands"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_command`).length,
        2,
        "should have 2 commands"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_commandSettings`).length,
        1,
        "should have 'settings' command"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_commandLeave`).length,
        1,
        "should have 'leave' command"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_counter`).length,
        0,
        "should have a counter when equals 0 (default value)"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`).click()
    );
    channel = document.querySelector(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`);
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_activeIndicator.o-item-active`).length,
        1,
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

    // channel expected to be found in the sidebar
    // with a random unique id that will be used to link message
    this.data['mail.channel'].records.push({ id: 20 });
    // expected needaction message
    this.data['mail.message'].records.push({
        body: "not empty",
        channel_ids: [20], // link message to channel
        id: 100, // random unique id, useful to link notification
    });
    // expected needaction notification
    this.data['mail.notification'].records.push({
        mail_message_id: 100, // id of related message
        res_partner_id: this.data.currentPartnerId, // must be for current partner
    });
    await this.start();
    const channel = document.querySelector(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`);
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_counter`).length,
        1,
        "should have a counter when different from 0"
    );
    assert.strictEqual(
        channel.querySelector(`:scope .o_DiscussSidebarItem_counter`).textContent,
        "1",
        "should have counter value"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_command`).length,
        1,
        "should have single command"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_commandSettings`).length,
        1,
        "should have 'settings' command"
    );
    assert.strictEqual(
        channel.querySelectorAll(`:scope .o_DiscussSidebarItem_commandLeave`).length,
        0,
        "should not have 'leave' command"
    );
});

QUnit.test('sidebar: mailing channel', async function (assert) {
    assert.expect(1);

    // channel that is expected to be in the sidebar, with proper mass_mailing value
    this.data['mail.channel'].records.push({ mass_mailing: true });
    await this.start();
    assert.containsOnce(
        document.querySelector(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`),
        '.fa.fa-envelope-o',
        "should have an icon to indicate that the channel is a mailing channel"
    );
});

QUnit.test('sidebar: public/private channel rendering', async function (assert) {
    assert.expect(5);

    // channels that are expected to be found in the sidebar (one public, one private)
    // with random unique id and name that will be referenced in the test
    this.data['mail.channel'].records.push(
        { id: 100, name: "channel1", public: 'public', },
        { id: 101, name: "channel2", public: 'private' }
    );
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`).length,
        2,
        "should have 2 channel items"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 100 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have channel1 (Id 100)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 101 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have channel2 (Id 101)"
    );
    const channel1 = document.querySelector(`
        .o_DiscussSidebar_groupChannel
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 100 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    const channel2 = document.querySelector(`
        .o_DiscussSidebar_groupChannel
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 101 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    assert.strictEqual(
        channel1.querySelectorAll(`:scope .o_ThreadIcon_channelPublic`).length,
        1,
        "channel1 (public) has hashtag icon"
    );
    assert.strictEqual(
        channel2.querySelectorAll(`:scope .o_ThreadIcon_channelPrivate`).length,
        1,
        "channel2 (private) has lock icon"
    );
});

QUnit.test('sidebar: basic chat rendering', async function (assert) {
    assert.expect(11);

    // expected correspondent, with a random unique id that will be used to link
    // partner to chat and a random name that will be asserted in the test
    this.data['res.partner'].records.push({ id: 17, name: "Demo" });
    // chat expected to be found in the sidebar
    this.data['mail.channel'].records.push({
        channel_type: 'chat', // testing a chat is the goal of the test
        id: 10, // random unique id, will be referenced in the test
        members: [this.data.currentPartnerId, 17], // expected partners
        public: 'private', // expected value for testing a chat
    });
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_item`).length,
        1,
        "should have one chat item"
    );
    const chat = document.querySelector(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_item`);
    assert.strictEqual(
        chat.dataset.threadLocalId,
        this.env.models['mail.thread'].find(thread =>
            thread.id === 10 &&
            thread.model === 'mail.channel'
        ).localId,
        "should have chat with Id 10"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_activeIndicator`).length,
        1,
        "should have active indicator"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_ThreadIcon`).length,
        1,
        "should have an icon"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_name`).length,
        1,
        "should have a name"
    );
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarItem_name`).textContent,
        "Demo",
        "should have correspondent name as name"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_commands`).length,
        1,
        "should have commands"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_command`).length,
        2,
        "should have 2 commands"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_commandRename`).length,
        1,
        "should have 'rename' command"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_commandUnpin`).length,
        1,
        "should have 'unpin' command"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_counter`).length,
        0,
        "should have a counter when equals 0 (default value)"
    );
});

QUnit.test('sidebar: chat rendering with unread counter', async function (assert) {
    assert.expect(5);

    // chat expected to be found in the sidebar
    this.data['mail.channel'].records.push({
        channel_type: 'chat', // testing a chat is the goal of the test
        id: 10, // random unique id, will be referenced in the test
        message_unread_counter: 100,
        public: 'private', // expected value for testing a chat
    });
    await this.start();
    const chat = document.querySelector(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_item`);
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_counter`).length,
        1,
        "should have a counter when different from 0"
    );
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarItem_counter`).textContent,
        "100",
        "should have counter value"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_command`).length,
        1,
        "should have single command"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_commandRename`).length,
        1,
        "should have 'rename' command"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_commandUnpin`).length,
        0,
        "should not have 'unpin' command"
    );
});

QUnit.test('sidebar: chat im_status rendering', async function (assert) {
    assert.expect(7);

    // expected correspondent, with a random unique id that will be used to link
    // partner to chat, and various im_status values to assert
    this.data['res.partner'].records.push(
        { id: 101, im_status: 'offline', name: "Partner1" },
        { id: 102, im_status: 'online', name: "Partner2" },
        { id: 103, im_status: 'away', name: "Partner3" }
    );
    // chats expected to be found in the sidebar
    this.data['mail.channel'].records.push(
        {
            channel_type: 'chat', // testing a chat is the goal of the test
            id: 11, // random unique id, will be referenced in the test
            members: [this.data.currentPartnerId, 101], // expected partners
            public: 'private', // expected value for testing a chat
        },
        {
            channel_type: 'chat', // testing a chat is the goal of the test
            id: 12, // random unique id, will be referenced in the test
            members: [this.data.currentPartnerId, 102], // expected partners
            public: 'private', // expected value for testing a chat
        },
        {
            channel_type: 'chat', // testing a chat is the goal of the test
            id: 13, // random unique id, will be referenced in the test
            members: [this.data.currentPartnerId, 103], // expected partners
            public: 'private', // expected value for testing a chat
        }
    );
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_item`).length,
        3,
        "should have 3 chat items"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupChat
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 11 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have Partner1 (Id 11)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupChat
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 12 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have Partner2 (Id 12)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_groupChat
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 13 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have Partner3 (Id 13)"
    );
    const chat1 = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 11 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    const chat2 = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 12 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    const chat3 = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 13 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
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

    // expected correspondent, with a random unique id that will be used to link
    // partner to chat, and a random name not used in the scope of this test but set for consistency
    this.data['res.partner'].records.push({ id: 101, name: "Marc Demo" });
    // chat expected to be found in the sidebar
    this.data['mail.channel'].records.push({
        channel_type: 'chat', // testing a chat is the goal of the test
        custom_channel_name: "Marc", // testing a custom name is the goal of the test
        members: [this.data.currentPartnerId, 101], // expected partners
        public: 'private', // expected value for testing a chat
    });
    await this.start();
    const chat = document.querySelector(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_item`);
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarItem_name`).textContent,
        "Marc",
        "chat should have custom name as name"
    );
});

QUnit.test('sidebar: rename chat', async function (assert) {
    assert.expect(8);

    // expected correspondent, with a random unique id that will be used to link
    // partner to chat, and a random name not used in the scope of this test but set for consistency
    this.data['res.partner'].records.push({ id: 101, name: "Marc Demo" });
    // chat expected to be found in the sidebar
    this.data['mail.channel'].records.push({
        channel_type: 'chat', // testing a chat is the goal of the test
        custom_channel_name: "Marc", // testing a custom name is the goal of the test
        members: [this.data.currentPartnerId, 101], // expected partners
        public: 'private', // expected value for testing a chat
    });
    await this.start();
    const chat = document.querySelector(`.o_DiscussSidebar_groupChat .o_DiscussSidebar_item`);
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarItem_name`).textContent,
        "Marc",
        "chat should have custom name as name"
    );
    assert.notOk(
        chat.querySelector(`:scope .o_DiscussSidebarItem_name`).classList.contains('o-editable'),
        "chat name should not be editable"
    );

    await afterNextRender(() =>
        chat.querySelector(`:scope .o_DiscussSidebarItem_commandRename`).click()
    );
    assert.ok(
        chat.querySelector(`:scope .o_DiscussSidebarItem_name`).classList.contains('o-editable'),
        "chat should have editable name"
    );
    assert.strictEqual(
        chat.querySelectorAll(`:scope .o_DiscussSidebarItem_nameInput`).length,
        1,
        "chat should have editable name input"
    );
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarItem_nameInput`).value,
        "Marc",
        "editable name input should have custom chat name as value by default"
    );
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarItem_nameInput`).placeholder,
        "Marc Demo",
        "editable name input should have partner name as placeholder"
    );

    await afterNextRender(() => {
        chat.querySelector(`:scope .o_DiscussSidebarItem_nameInput`).value = "Demo";
        const kevt = new window.KeyboardEvent('keydown', { key: "Enter" });
        chat.querySelector(`:scope .o_DiscussSidebarItem_nameInput`).dispatchEvent(kevt);
    });
    assert.notOk(
        chat.querySelector(`:scope .o_DiscussSidebarItem_name`).classList.contains('o-editable'),
        "chat should no longer show editable name"
    );
    assert.strictEqual(
        chat.querySelector(`:scope .o_DiscussSidebarItem_name`).textContent,
        "Demo",
        "chat should have renamed name as name"
    );
});

QUnit.test('default thread rendering', async function (assert) {
    assert.expect(16);

    // channel expected to be found in the sidebar,
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
        `).length,
        1,
        "should have inbox mailbox in the sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
        `).length,
        1,
        "should have starred mailbox in the sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
            }"]
        `).length,
        1,
        "should have history mailbox in the sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have channel 20 in the sidebar"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
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

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
        `).click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
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

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
            }"]
        `).click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
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

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
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
    assert.expect(4);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                assert.step('message_fetch');
                assert.strictEqual(
                    args.kwargs.limit,
                    30,
                    "should fetch up to 30 messages"
                );
                assert.deepEqual(
                    args.kwargs.domain,
                    [["needaction", "=", true]],
                    "should fetch needaction messages"
                );
            }
            return this._super(...arguments);
        },
    });
    assert.verifySteps(['message_fetch']);
});

QUnit.test('default select thread in discuss params', async function (assert) {
    assert.expect(1);

    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.box_starred',
            },
        }
    });
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "starred mailbox should become active"
    );
});

QUnit.test('auto-select thread in discuss context', async function (assert) {
    assert.expect(1);

    await this.start({
        discuss: {
            context: {
                active_id: 'mail.box_starred',
            },
        },
    });
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "starred mailbox should become active"
    );
});

QUnit.test('load single message from channel initially', async function (assert) {
    assert.expect(7);

    // channel expected to be rendered, with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    this.data['mail.message'].records.push({
        body: "not empty",
        channel_ids: [20],
        date: "2019-04-20 10:00:00",
        id: 100,
        model: 'mail.channel',
        res_id: 20,
    });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                assert.strictEqual(
                    args.kwargs.limit,
                    30,
                    "should fetch up to 30 messages"
                );
                assert.deepEqual(
                    args.kwargs.domain,
                    [["channel_ids", "in", [20]]],
                    "should fetch messages from channel"
                );
            }
            return this._super(...arguments);
        },
    });
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
            .o_MessageList_message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
        `).length,
        1,
        "should have message with Id 100"
    );
});

QUnit.test('open channel from active_id as channel id', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start({
        discuss: {
            context: {
                active_id: 20,
            },
        }
    });
    assert.containsOnce(
        document.body,
        `
            .o_Discuss_thread[data-thread-local-id="${
                this.env.models['mail.thread'].findFromIdentifyingData({ id: 20, model: 'mail.channel' }).localId
            }"]
        `,
        "should have channel with ID 20 open in Discuss when providing active_id 20"
    );
});

QUnit.test('basic rendering of message', async function (assert) {
    // AKU TODO: should be in message-only tests
    assert.expect(13);

    // channel expected to be rendered, with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    // partner to be set as author, with a random unique id that will be used to
    // link message and a random name that will be asserted in the test
    this.data['res.partner'].records.push({ id: 11, name: "Demo" });
    this.data['mail.message'].records.push({
        author_id: 11,
        body: "<p>body</p>",
        channel_ids: [20],
        date: "2019-04-20 10:00:00",
        id: 100,
        model: 'mail.channel',
        res_id: 20,
    });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    const message = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
        .o_MessageList_message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
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
        "/web/image/res.partner/11/image_128",
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
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_header .o_Message_commands`).length,
        1,
        "should have commands in header of message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_header .o_Message_command`).length,
        1,
        "should have a single command in header of message"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_commandStar`).length,
        1,
        "should have command to star message"
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

QUnit.test('basic rendering of squashed message', async function (assert) {
    // messages are squashed when "close", e.g. less than 1 minute has elapsed
    // from messages of same author and same thread. Note that this should
    // be working in non-mailboxes
    // AKU TODO: should be message and/or message list-only tests
    assert.expect(12);

    // channel expected to be rendered, with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    // partner to be set as author, with a random unique id that will be used to link message
    this.data['res.partner'].records.push({ id: 11 });
    this.data['mail.message'].records.push(
        {
            author_id: 11, // must be same author as other message
            body: "<p>body1</p>", // random body, set for consistency
            channel_ids: [20], // to link message to channel
            date: "2019-04-20 10:00:00", // date must be within 1 min from other message
            id: 100, // random unique id, will be referenced in the test
            message_type: 'comment', // must be a squash-able type-
            model: 'mail.channel', // to link message to channel
            res_id: 20, // id of related channel
        },
        {
            author_id: 11, // must be same author as other message
            body: "<p>body2</p>", // random body, will be asserted in the test
            channel_ids: [20], // to link message to channel
            date: "2019-04-20 10:00:30", // date must be within 1 min from other message
            id: 101, // random unique id, will be referenced in the test
            message_type: 'comment', // must be a squash-able type
            model: 'mail.channel', // to link message to channel
            res_id: 20, // id of related channel
        }
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
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
        .o_MessageList_message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
    `);
    const message2 = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
        .o_MessageList_message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 101).localId
        }"]
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
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_Message_sidebar .o_Message_date`).length,
        1,
        "message 2 should have date in sidebar"
    );
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_Message_sidebar .o_Message_commands`).length,
        1,
        "message 2 should have some commands in sidebar"
    );
    assert.strictEqual(
        message2.querySelectorAll(`:scope .o_Message_sidebar .o_Message_commandStar`).length,
        1,
        "message 2 should have star command in sidebar"
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

    // partner to be set as author, with a random unique id that will be used to link message
    this.data['res.partner'].records.push({ id: 11 });
    this.data['mail.message'].records.push(
        {
            author_id: 11, // must be same author as other message
            body: "<p>body1</p>", // random body, set for consistency
            channel_ids: [20], // to link message to channel
            date: "2019-04-20 10:00:00", // date must be within 1 min from other message
            id: 100, // random unique id, will be referenced in the test
            message_type: 'comment', // must be a squash-able type-
            model: 'mail.channel', // to link message to channel
            needaction: true, // necessary for message_fetch domain
            needaction_partner_ids: [this.data.currentPartnerId], // for consistency
            res_id: 20, // id of related channel
        },
        {
            author_id: 11, // must be same author as other message
            body: "<p>body2</p>", // random body, will be asserted in the test
            channel_ids: [20], // to link message to channel
            date: "2019-04-20 10:00:30", // date must be within 1 min from other message
            id: 101, // random unique id, will be referenced in the test
            message_type: 'comment', // must be a squash-able type
            model: 'mail.channel', // to link message to channel
            needaction: true, // necessary for message_fetch domain
            needaction_partner_ids: [this.data.currentPartnerId], // for consistency
            res_id: 20, // id of related channel
        }
    );
    await this.start();
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
        .o_MessageList_message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
    `);
    const message2 = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
        .o_MessageList_message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 101).localId
        }"]
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

    // channel expected to be rendered, with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    // partner to be set as author, with a random unique id that will be used to link message
    this.data['res.partner'].records.push({ id: 11 });
    for (let i = 28; i >= 0; i--) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
            date: "2019-04-20 10:00:00",
            model: 'mail.channel',
            res_id: 20,
        });
    }
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                assert.strictEqual(args.kwargs.limit, 30, "should fetch up to 30 messages");
            }
            return this._super(...arguments);
        },
    });
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

    // channel expected to be rendered, with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    // partner to be set as author, with a random unique id that will be used to link message
    this.data['res.partner'].records.push({ id: 11 });
    for (let i = 0; i < 40; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
            date: "2019-04-20 10:00:00",
            model: 'mail.channel',
            res_id: 20,
        });
    }
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
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

    await afterNextRender(() =>
        document.querySelector(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_loadMore
        `).click()
    );
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

    // channel expected to be rendered, with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    for (let i = 1; i <= 25; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
            model: 'mail.channel',
            res_id: 20,
        });
    }
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
        waitUntilEvent: {
            eventName: 'o-component-message-list-scrolled',
            message: "should wait until channel 20 scrolled to its last message initially",
            predicate: ({ scrollTop, threadViewer }) => {
                const messageList = document.querySelector('.o_ThreadView_messageList');
                return (
                    threadViewer.thread.model === 'mail.channel' &&
                    threadViewer.thread.id === 20 &&
                    scrollTop === messageList.scrollHeight - messageList.clientHeight
                );
            },
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
    assert.strictEqual(
        messageList.scrollTop,
        messageList.scrollHeight - messageList.clientHeight,
        "should have scrolled to bottom of thread"
    );
});

QUnit.test('load more messages from channel (auto-load on scroll)', async function (assert) {
    // AKU TODO: thread specific test
    assert.expect(3);

    this.data['mail.channel'].records.push({ id: 20 });
    for (let i = 0; i < 40; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
            model: 'mail.channel',
            res_id: 20,
        });
    }
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
        waitUntilEvent: {
            eventName: 'o-component-message-list-scrolled',
            message: "should wait until channel 20 scrolled to its last message initially",
            predicate: ({ scrollTop, threadViewer }) => {
                const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
                return (
                    threadViewer.thread.model === 'mail.channel' &&
                    threadViewer.thread.id === 20 &&
                    scrollTop === messageList.scrollHeight - messageList.clientHeight
                );
            },
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        30,
        "should have 30 messages"
    );

    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => document.querySelector('.o_ThreadView_messageList').scrollTop = 0,
        message: "should wait until channel 20 loaded more messages after scrolling to top",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20
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

    // Needed partner & user to allow simulation of message reception
    this.data['res.partner'].records.push({
        id: 11,
        name: "Foreigner partner",
    });
    this.data['res.users'].records.push({
        id: 42,
        name: "Foreigner user",
        partner_id: 11,
    });
    // channel expected to be rendered, with a random unique id that will be
    // referenced in the test and the seen_message_id value set to last message
    this.data['mail.channel'].records.push({
        id: 20,
        seen_message_id: 125,
        uuid: 'randomuuid',
    });
    for (let i = 1; i <= 25; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
            id: 100 + i, // for setting proper value for seen_message_id
            model: 'mail.channel',
            res_id: 20,
        });
    }
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
        waitUntilEvent: {
            eventName: 'o-component-message-list-scrolled',
            message: "should wait until channel 20 scrolled to its last message initially",
            predicate: ({ scrollTop, threadViewer }) => {
                const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
                return (
                    threadViewer.thread.model === 'mail.channel' &&
                    threadViewer.thread.id === 20 &&
                    scrollTop === messageList.scrollHeight - messageList.clientHeight
                );
            },
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
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`).scrollTop = 0;
        },
        message: "should wait until channel scrolled to top",
        predicate: ({ scrollTop, threadViewer }) => {
            return (
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20 &&
                scrollTop === 0
            );
        },
    });
    // composer is focused by default, we remove that focus
    document.querySelector('.o_ComposerTextInput_textarea').blur();
    // simulate receiving a message
    await afterNextRender(async () => this.env.services.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: 42,
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
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
            messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
        },
        message: "should wait until channel scrolled to bottom",
        predicate: ({ scrollTop, threadViewer }) => {
            const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
            return (
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20 &&
                scrollTop === messageList.scrollHeight - messageList.clientHeight
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
    // channels expected to be rendered, with random unique id that will be referenced in the test
    this.data['mail.channel'].records.push(
        {
            id: 11,
        },
        {
            id: 12,
        },
    );
    for (let i = 1; i <= 25; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [11],
            model: 'mail.channel',
            res_id: 11,
        });
    }
    for (let i = 1; i <= 24; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [12],
            model: 'mail.channel',
            res_id: 12,
        });
    }
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_11',
            },
        },
        waitUntilEvent: {
            eventName: 'o-component-message-list-scrolled',
            message: "should wait until channel 11 scrolled to its last message",
            predicate: ({ threadViewer }) => {
                return threadViewer.thread.model === 'mail.channel' && threadViewer.thread.id === 11;
            },
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        25,
        "should have 25 messages in channel 11"
    );
    const initialMessageList = document.querySelector(`
        .o_Discuss_thread
        .o_ThreadView_messageList
    `);
    assert.strictEqual(
        initialMessageList.scrollTop,
        initialMessageList.scrollHeight - initialMessageList.clientHeight,
        "should have scrolled to bottom of channel 11 initially"
    );

    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`).scrollTop = 0,
        message: "should wait until channel 11 changed its scroll position to top",
        predicate: ({ threadViewer }) => {
            return threadViewer.thread.model === 'mail.channel' && threadViewer.thread.id === 11;
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`).scrollTop,
        0,
        "should have scrolled to top of channel 11",
    );

    // Ensure scrollIntoView of channel 12 has enough time to complete before
    // going back to channel 11. Await is needed to prevent the scrollIntoView
    // initially planned for channel 12 to actually apply on channel 11.
    // task-2333535
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            // select channel 12
            document.querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item[data-thread-local-id="${
                    this.env.models['mail.thread'].find(thread =>
                        thread.id === 12 &&
                        thread.model === 'mail.channel'
                    ).localId
                }"]
            `).click();
        },
        message: "should wait until channel 12 scrolled to its last message",
        predicate: ({ scrollTop, threadViewer }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 12 &&
                scrollTop === messageList.scrollHeight - messageList.clientHeight
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread .o_ThreadView_messageList .o_MessageList_message
        `).length,
        24,
        "should have 24 messages in channel 12"
    );

    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            // select channel 11
            document.querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item[data-thread-local-id="${
                    this.env.models['mail.thread'].find(thread =>
                        thread.id === 11 &&
                        thread.model === 'mail.channel'
                    ).localId
                }"]
            `).click();
        },
        message: "should wait until channel 11 restored its scroll position",
        predicate: ({ scrollTop, threadViewer }) => {
            return (
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 11 &&
                scrollTop === 0
            );
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`).scrollTop,
        0,
        "should have recovered scroll position of channel 11 (scroll to top)"
    );

    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            // select channel 12
            document.querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item[data-thread-local-id="${
                    this.env.models['mail.thread'].find(thread =>
                        thread.id === 12 &&
                        thread.model === 'mail.channel'
                    ).localId
                }"]
            `).click();
        },
        message: "should wait until channel 12 recovered its scroll position (to bottom)",
        predicate: ({ scrollTop, threadViewer }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 12 &&
                scrollTop === messageList.scrollHeight - messageList.clientHeight
            );
        },
    });
    const messageList = document.querySelector('.o_ThreadView_messageList');
    assert.strictEqual(
        messageList.scrollTop,
        messageList.scrollHeight - messageList.clientHeight,
        "should have recovered scroll position of channel 12 (scroll to bottom)"
    );
});

QUnit.test('message origin redirect to channel', async function (assert) {
    assert.expect(15);

    // channels expected to be rendered, with random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 11 }, { id: 12 });
    this.data['mail.message'].records.push(
        {
            body: "not empty",
            channel_ids: [11, 12],
            id: 100,
            model: 'mail.channel',
            record_name: "channel11",
            res_id: 11,
        },
        {
            body: "not empty",
            channel_ids: [11, 12],
            id: 101,
            model: 'mail.channel',
            record_name: "channel12",
            res_id: 12,
        }
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_11',
            },
        },
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Discuss_thread .o_Message').length,
        2,
        "should have 2 messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
        `).length,
        1,
        "should have message1 (Id 100)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 101).localId
            }"]
        `).length,
        1,
        "should have message2 (Id 101)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
            .o_Message_originThread
        `).length,
        0,
        "message1 should not have origin part in channel11 (same origin as channel)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 101).localId
            }"]
            .o_Message_originThread
        `).length,
        1,
        "message2 should have origin part (origin is channel12 !== channel11)"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 101).localId
            }"]
            .o_Message_originThread
        `).textContent.trim(),
        "(from #channel12)",
        "message2 should display name of origin channel"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 101).localId
            }"]
            .o_Message_originThreadLink
        `).length,
        1,
        "message2 should have link to redirect to origin"
    );

    // click on origin link of message2 (= channel12)
    await afterNextRender(() =>
        document.querySelector(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 101).localId
            }"]
            .o_Message_originThreadLink
        `).click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 12 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "channel12 should be active channel on redirect from discuss app"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_Message`).length,
        2,
        "should have 2 messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
        `).length,
        1,
        "should have message1 (Id 100)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 101).localId
            }"]
        `).length,
        1,
        "should have message2 (Id 101)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
            .o_Message_originThread
        `).length,
        1,
        "message1 should have origin thread part (= channel11 !== channel12)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 101).localId
            }"]
            .o_Message_originThread
        `).length,
        0,
        "message2 should not have origin thread part in channel12 (same as current channel)"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
            .o_Message_originThread
        `).textContent.trim(),
        "(from #channel11)",
        "message1 should display name of origin channel"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
            .o_Message_originThreadLink
        `).length,
        1,
        "message1 should have link to redirect to origin channel"
    );
});

QUnit.test('redirect to author (open chat)', async function (assert) {
    assert.expect(7);

    // expected correspondent, with a random unique id that will be used to link
    // partner to chat and a random name that will be asserted in the test
    this.data['res.partner'].records.push({ id: 7, name: "Demo" });
    this.data['res.users'].records.push({ partner_id: 7 });
    this.data['mail.channel'].records.push(
        // channel expected to be found in the sidebar
        {
            id: 1, // random unique id, will be referenced in the test
            name: "General", // random name, will be asserted in the test
        },
        // chat expected to be found in the sidebar
        {
            channel_type: 'chat', // testing a chat is the goal of the test
            id: 10, // random unique id, will be referenced in the test
            members: [this.data.currentPartnerId, 7], // expected partners
            public: 'private', // expected value for testing a chat
        }
    );
    this.data['mail.message'].records.push(
        {
            author_id: 7,
            body: "not empty",
            channel_ids: [1],
            id: 100,
            model: 'mail.channel',
            res_id: 1,
        }
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_1',
            },
        },
    });
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 1 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "channel 'General' should be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebar_groupChat
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "Chat 'Demo' should not be active"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_Message`).length,
        1,
        "should have 1 message"
    );
    const msg1 = document.querySelector(`
        .o_Discuss_thread
        .o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 100).localId
        }"]
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
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 1 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "channel 'General' should become inactive after author redirection"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_groupChat
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
            .o_DiscussSidebarItem_activeIndicator
        `).classList.contains('o-item-active'),
        "chat 'Demo' should become active after author redirection"
    );
});

QUnit.test('sidebar quick search', async function (assert) {
    // feature enables at 20 or more channels
    assert.expect(6);

    for (let id = 1; id <= 20; id++) {
        this.data['mail.channel'].records.push({ id, name: `channel${id}` });
    }
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`).length,
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
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`).length,
        11,
        "should have filtered to 11 channel items"
    );

    await afterNextRender(() => {
        quickSearch.value = "12";
        const kevt2 = new window.KeyboardEvent('input');
        quickSearch.dispatchEvent(kevt2);
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`).length,
        1,
        "should have filtered to a single channel item"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel .o_DiscussSidebar_item
        `).dataset.threadLocalId,
        this.env.models['mail.thread'].find(thread =>
            thread.id === 12 &&
            thread.model === 'mail.channel'
        ).localId,
        "should have filtered to a single channel item with Id 12"
    );

    await afterNextRender(() => {
        quickSearch.value = "123";
        const kevt3 = new window.KeyboardEvent('input');
        quickSearch.dispatchEvent(kevt3);
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupChannel .o_DiscussSidebar_item`).length,
        0,
        "should have filtered to no channel item"
    );
});

QUnit.test('basic control panel rendering', async function (assert) {
    assert.expect(8);

    // channel expected to be found in the sidebar
    // with a random unique id and name that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20, name: "General" });
    await this.start();
    assert.strictEqual(
        document.querySelector(`
            .o_widget_Discuss .o_control_panel .breadcrumb
        `).textContent,
        "Inbox",
        "display inbox in the breadcrumb"
    );
    const markAllReadButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonMarkAllRead`);
    assert.isVisible(
        markAllReadButton,
        "should have visible button 'Mark all read' in the control panel of inbox"
    );
    assert.ok(
        markAllReadButton.disabled,
        "should have disabled button 'Mark all read' in the control panel of inbox (no messages)"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
        `).click()
    );
    assert.strictEqual(
        document.querySelector(`
            .o_widget_Discuss .o_control_panel .breadcrumb
        `).textContent,
        "Starred",
        "display starred in the breadcrumb"
    );
    const unstarAllButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonUnstarAll`);
    assert.isVisible(
        unstarAllButton,
        "should have visible button 'Unstar all' in the control panel of starred"
    );
    assert.ok(
        unstarAllButton.disabled,
        "should have disabled button 'Unstar all' in the control panel of starred (no messages)"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).click()
    );
    assert.strictEqual(
        document.querySelector(`
            .o_widget_Discuss .o_control_panel .breadcrumb
        `).textContent,
        "#General",
        "display general in the breadcrumb"
    );
    const inviteButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonInvite`);
    assert.isVisible(
        inviteButton,
        "should have visible button 'Invite' in the control panel of channel"
    );
});

QUnit.test('inbox: mark all messages as read', async function (assert) {
    assert.expect(8);

    // channel expected to be found in the sidebar,
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    this.data['mail.message'].records.push(
        // first expected message
        {
            body: "not empty",
            channel_ids: [20], // link message to channel
            id: 100, // random unique id, useful to link notification
            // needaction needs to be set here for message_fetch domain, because
            // mocked models don't have computed fields
            needaction: true,
        },
        // second expected message
        {
            body: "not empty",
            channel_ids: [20], // link message to channel
            id: 101, // random unique id, useful to link notification
            // needaction needs to be set here for message_fetch domain, because
            // mocked models don't have computed fields
            needaction: true,
        }
    );
    this.data['mail.notification'].records.push(
        // notification to have first message in inbox
        {
            mail_message_id: 100, // id of related message
            res_partner_id: this.data.currentPartnerId, // must be for current partner
        },
        // notification to have second message in inbox
        {
            mail_message_id: 101, // id of related message
            res_partner_id: this.data.currentPartnerId, // must be for current partner
        }
    );
    await this.start();
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
        `).textContent,
        "2",
        "inbox should have counter of 2"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
            .o_DiscussSidebarItem_counter
        `).textContent,
        "2",
        "channel should have counter of 2"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        2,
        "should have 2 messages in inbox"
    );
    let markAllReadButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonMarkAllRead`);
    assert.notOk(
        markAllReadButton.disabled,
        "should have enabled button 'Mark all read' in the control panel of inbox (has messages)"
    );

    await afterNextRender(() => markAllReadButton.click());
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
        `).length,
        0,
        "inbox should display no counter (= 0)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
            .o_DiscussSidebarItem_counter
        `).length,
        0,
        "channel should display no counter (= 0)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        0,
        "should have no message in inbox"
    );
    markAllReadButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonMarkAllRead`);
    assert.ok(
        markAllReadButton.disabled,
        "should have disabled button 'Mark all read' in the control panel of inbox (no messages)"
    );
});

QUnit.test('starred: unstar all', async function (assert) {
    assert.expect(6);

    // messages expected to be starred
    this.data['mail.message'].records.push(
        { body: "not empty", starred_partner_ids: [this.data.currentPartnerId] },
        { body: "not empty", starred_partner_ids: [this.data.currentPartnerId] }
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.box_starred',
            },
        },
    });
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_counter
        `).textContent,
        "2",
        "starred should have counter of 2"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        2,
        "should have 2 messages in starred"
    );
    let unstarAllButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonUnstarAll`);
    assert.notOk(
        unstarAllButton.disabled,
        "should have enabled button 'Unstar all' in the control panel of starred (has messages)"
    );

    await afterNextRender(() => unstarAllButton.click());
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_counter
        `).length,
        0,
        "starred should display no counter (= 0)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss .o_Message`).length,
        0,
        "should have no message in starred"
    );
    unstarAllButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonUnstarAll`);
    assert.ok(
        unstarAllButton.disabled,
        "should have disabled button 'Unstar all' in the control panel of starred (no messages)"
    );
});

QUnit.test('toggle_star message', async function (assert) {
    assert.expect(16);

    // channel expected to be initially rendered
    // with a random unique id, will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    this.data['mail.message'].records.push({
        body: "not empty",
        channel_ids: [20],
        id: 100,
        model: 'mail.channel',
        res_id: 20,
    });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
        async mockRPC(route, args) {
            if (args.method === 'toggle_message_starred') {
                assert.step('rpc:toggle_message_starred');
                assert.strictEqual(
                    args.args[0][0],
                    100,
                    "should have message Id in args"
                );
            }
            return this._super(...arguments);
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_counter
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
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_commandStar`).length,
        1,
        "message should have star command"
    );

    await afterNextRender(() => message.querySelector(`:scope .o_Message_commandStar`).click());
    assert.verifySteps(['rpc:toggle_message_starred']);
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_counter
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

    await afterNextRender(() => message.querySelector(`:scope .o_Message_commandStar`).click());
    assert.verifySteps(['rpc:toggle_message_starred']);
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.starred.localId
            }"]
            .o_DiscussSidebarItem_counter
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

    // channels expected to be found in the sidebar,
    // with random unique id and name that will be referenced in the test
    this.data['mail.channel'].records.push(
        { id: 20, name: "General" },
        { id: 21, name: "Special" }
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    // Write text in composer for #general
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "A message");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('input'));
    });
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarItem[data-thread-name="Special"]`).click()
    );
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "An other message");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('input'));
    });
    // Switch back to #general
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarItem[data-thread-name="General"]`).click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "A message",
        "should restore the input text"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarItem[data-thread-name="Special"]`).click()
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "An other message",
        "should restore the input text"
    );
});

QUnit.test('composer state: attachments save and restore', async function (assert) {
    assert.expect(6);

    // channels expected to be found in the sidebar
    // with random unique id and name that will be referenced in the test
    this.data['mail.channel'].records.push(
        { id: 20, name: "General" },
        { id: 21, name: "Special" }
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    const channels = document.querySelectorAll(`
        .o_DiscussSidebar_groupChannel .o_DiscussSidebar_item
    `);
    // Add attachment in a message for #general
    await afterNextRender(async () => {
        const file = await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        });
        inputFiles(
            document.querySelector('.o_FileUploader_input'),
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
            document.querySelector('.o_FileUploader_input'),
            files
        )
    );
    // Switch back to #general
    await afterNextRender(() => channels[0].click());
    // Check attachment is reloaded
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        1,
        "should have 1 attachment in the composer"
    );
    assert.strictEqual(
        document.querySelector(`.o_Composer .o_Attachment`).dataset.attachmentLocalId,
        this.env.models['mail.attachment'].find(attachment => attachment.id === 1).localId,
        "should have correct 1st attachment in the composer"
    );

    // Switch back to #special
    await afterNextRender(() => channels[1].click());
    // Check attachments are reloaded
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        3,
        "should have 3 attachments in the composer"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`)[0].dataset.attachmentLocalId,
        this.env.models['mail.attachment'].find(attachment => attachment.id === 2).localId,
        "should have attachment with id 2 as 1st attachment"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`)[1].dataset.attachmentLocalId,
        this.env.models['mail.attachment'].find(attachment => attachment.id === 3).localId,
        "should have attachment with id 3 as 2nd attachment"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`)[2].dataset.attachmentLocalId,
        this.env.models['mail.attachment'].find(attachment => attachment.id === 4).localId,
        "should have attachment with id 4 as 3rd attachment"
    );
});

QUnit.test('post a simple message', async function (assert) {
    assert.expect(15);

    // channel expected to be found in the sidebar
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    let postedMessageId;
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
        async mockRPC(route, args) {
            const res = await this._super(...arguments);
            if (args.method === 'message_post') {
                assert.step('message_post');
                assert.strictEqual(
                    args.args[0],
                    20,
                    "should post message to channel Id 20"
                );
                assert.strictEqual(
                    args.kwargs.body,
                    "Test",
                    "should post with provided content in composer input"
                );
                assert.strictEqual(
                    args.kwargs.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
                assert.strictEqual(
                    args.kwargs.subtype_xmlid,
                    "mail.mt_comment",
                    "should set subtype_xmlid as 'comment'"
                );
                postedMessageId = res;
            }
            return res;
        },
    });
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
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "Test",
        "should have inserted text in editable"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
    );
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
    const message = document.querySelector(`.o_Message`);
    assert.strictEqual(
        message.dataset.messageLocalId,
        this.env.models['mail.message'].find(message => message.id === postedMessageId).localId,
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

QUnit.test('post message on non-mailing channel with "Enter" keyboard shortcut', async function (assert) {
    assert.expect(2);

    // channel expected to be found in the sidebar
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20, mass_mailing: false });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in channel"
    );

    // insert some HTML in editable
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
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

QUnit.test('do not post message on non-mailing channel with "SHIFT-Enter" keyboard shortcut', async function (assert) {
    // Note that test doesn't assert SHIFT-Enter makes a newline, because this
    // default browser cannot be simulated with just dispatching
    // programmatically crafted events...
    assert.expect(2);

    // channel expected to be found in the sidebar
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20, mass_mailing: true });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in channel"
    );

    // insert some HTML in editable
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    const kevt = new window.KeyboardEvent('keydown', { key: "Enter", shiftKey: true });
    document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_Message',
        "should still not have any message in channel after pressing 'Shift-Enter' in text input of composer"
    );
});

QUnit.test('post message on mailing channel with "CTRL-Enter" keyboard shortcut', async function (assert) {
    assert.expect(2);

    // channel expected to be found in the sidebar
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20, mass_mailing: true });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in channel"
    );

    // insert some HTML in editable
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { ctrlKey: true, key: "Enter" });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have single message in channel after posting message from pressing 'CTRL-Enter' in text input of composer"
    );
});

QUnit.test('post message on mailing channel with "META-Enter" keyboard shortcut', async function (assert) {
    assert.expect(2);

    // channel expected to be found in the sidebar
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20, mass_mailing: true });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in channel"
    );

    // insert some HTML in editable
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { key: "Enter", metaKey: true });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have single message in channel after posting message from pressing 'META-Enter' in text input of composer"
    );
});

QUnit.test('do not post message on mailing channel with "Enter" keyboard shortcut', async function (assert) {
    // Note that test doesn't assert Enter makes a newline, because this
    // default browser cannot be simulated with just dispatching
    // programmatically crafted events...
    assert.expect(2);

    // channel expected to be found in the sidebar
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20, mass_mailing: true });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should not have any message initially in mailing channel"
    );

    // insert some HTML in editable
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    const kevt = new window.KeyboardEvent('keydown', { key: "Enter" });
    document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_Message',
        "should still not have any message in mailing channel after pressing 'Enter' in text input of composer"
    );
});

QUnit.test('rendering of inbox message', async function (assert) {
    // AKU TODO: kinda message specific test
    assert.expect(7);

    this.data['mail.message'].records.push({
        body: "not empty",
        model: 'res.partner', // random existing model
        needaction: true, // for message_fetch domain
        needaction_partner_ids: [this.data.currentPartnerId], // for consistency
        record_name: 'Refactoring', // random name, will be asserted in the test
        res_id: 20, // random related id
    });
    await this.start();
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
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_command`).length,
        3,
        "should display 3 commands"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_commandStar`).length,
        1,
        "should display star command"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_commandReply`).length,
        1,
        "should display reply command"
    );
    assert.strictEqual(
        message.querySelectorAll(`:scope .o_Message_commandMarkAsRead`).length,
        1,
        "should display mark as read command"
    );
});

QUnit.test('mark channel as seen on last message visible [REQUIRE FOCUS]', async function (assert) {
    assert.expect(3);

    // channel expected to be found in the sidebar, with the expected message_unread_counter
    // and a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 10, message_unread_counter: 1 });
    this.data['mail.message'].records.push({
        id: 12,
        body: "not empty",
        channel_ids: [10],
        model: 'mail.channel',
        res_id: 10,
    });
    await this.start();
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebar_item[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "should have discuss sidebar item with the channel"
    );
    assert.hasClass(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 10,
                    model: 'mail.channel',
                }).localId
            }"]
        `),
        'o-unread',
        "sidebar item of channel ID 10 should be unread"
    );

    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="${
                    this.env.models['mail.thread'].findFromIdentifyingData({
                        id: 10,
                        model: 'mail.channel',
                    }).localId
                }"]
            `).click();
        },
        message: "should wait until last seen by current partner message id changed",
        predicate: ({ thread }) => {
            return (
                thread.id === 10 &&
                thread.model === 'mail.channel' &&
                thread.lastSeenByCurrentPartnerMessageId === 12
            );
        },
    }));
    assert.doesNotHaveClass(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 10,
                    model: 'mail.channel',
                }).localId
            }"]
        `),
        'o-unread',
        "sidebar item of channel ID 10 should not longer be unread"
    );
});

QUnit.test('receive new needaction messages', async function (assert) {
    assert.expect(12);

    await this.start();
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
        `),
        "should have inbox in sidebar"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
        `).classList.contains('o-active'),
        "inbox should be current discuss thread"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
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
        const data = {
            body: "not empty",
            id: 100,
            needaction_partner_ids: [3],
            model: 'res.partner',
            res_id: 20,
        };
        const notifications = [[['my-db', 'ir.needaction', 3], data]];
        this.widget.call('bus_service', 'trigger', 'notification', notifications);
    });
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
        `),
        "inbox item in sidebar should now have counter"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
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
        document.querySelector(`.o_Discuss_thread .o_Message`).dataset.messageLocalId,
        this.env.models['mail.message'].find(message => message.id === 100).localId,
        "should display newly received needaction message"
    );

    // simulate receiving another new needaction message
    await afterNextRender(() => {
        const data2 = {
            body: "not empty",
            id: 101,
            needaction_partner_ids: [3],
            model: 'res.partner',
            res_id: 20,
        };
        const notifications2 = [[['my-db', 'ir.needaction', 3], data2]];
        this.widget.call('bus_service', 'trigger', 'notification', notifications2);
    });
    assert.strictEqual(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
            .o_DiscussSidebarItem_counter
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
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
        `),
        "should still display 1st needaction message"
    );
    assert.ok(
        document.querySelector(`
            .o_Discuss_thread
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 101).localId
            }"]
        `),
        "should display 2nd needaction message"
    );
});

QUnit.test('reply to message from inbox (message linked to document)', async function (assert) {
    assert.expect(19);

    // message that is expected to be found in Inbox
    this.data['mail.message'].records.push({
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100, // random unique id, will be used to link notification to message
        message_type: 'comment',
        // needaction needs to be set here for message_fetch domain, because
        // mocked models don't have computed fields
        needaction: true,
        model: 'res.partner',
        record_name: 'Refactoring',
        res_id: 20,
    });
    // notification to have message in Inbox
    this.data['mail.notification'].records.push({
        mail_message_id: 100, // id of related message
        res_partner_id: this.data.currentPartnerId, // must be for current partner
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_post') {
                assert.step('message_post');
                assert.strictEqual(
                    args.model,
                    'res.partner',
                    "should post message to record with model 'res.partner'"
                );
                assert.strictEqual(
                    args.args[0],
                    20,
                    "should post message to record with Id 20"
                );
                assert.strictEqual(
                    args.kwargs.body,
                    "Test",
                    "should post with provided content in composer input"
                );
                assert.strictEqual(
                    args.kwargs.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
            }
            return this._super(...arguments);
        },
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should display a single message"
    );
    assert.strictEqual(
        document.querySelector('.o_Message').dataset.messageLocalId,
        this.env.models['mail.message'].find(message => message.id === 100).localId,
        "should display message with ID 100"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_originThread').textContent,
        " on Refactoring",
        "should display message originates from record 'Refactoring'"
    );

    await afterNextRender(() =>
        document.querySelector('.o_Message_commandReply').click()
    );
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

    await afterNextRender(() =>
        document.execCommand('insertText', false, "Test")
    );
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
    );
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
        document.querySelector('.o_Message').dataset.messageLocalId,
        this.env.models['mail.message'].find(message => message.id === 100).localId,
        "should still display message with ID 100 after posting reply"
    );
    assert.notOk(
        document.querySelector('.o_Message').classList.contains('o-selected'),
        "message should not longer be selected after posting reply"
    );
    assert.ok(
        document.querySelector('.o_notification'),
        "should display a notification after posting reply"
    );
    assert.strictEqual(
        document.querySelector('.o_notification_content').textContent,
        "Message posted on \"Refactoring\"",
        "notification should tell that message has been posted to the record 'Refactoring'"
    );
});

QUnit.test('load recent messages from thread (already loaded some old messages)', async function (assert) {
    assert.expect(6);

    // channel expected to be found in the sidebar,
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    for (let i = 0; i < 50; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20], // id of related channel
            id: 100 + i, // random unique id, will be referenced in the test
            model: 'mail.channel', // expected value to link message to channel
            // needaction needs to be set here for message_fetch domain, because
            // mocked models don't have computed fields
            needaction: i === 0,
            // the goal is to have only the first (oldest) message in Inbox
            needaction_partner_ids: i === 0 ? [this.data.currentPartnerId] : [],
            res_id: 20, // id of related channel
        });
    }
    await this.start();
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "Inbox should have a single message initially"
    );
    assert.strictEqual(
        document.querySelector('.o_Message').dataset.messageLocalId,
        this.env.models['mail.message'].find(message => message.id === 100).localId,
        "the only message initially should be the one marked as 'needaction'"
    );

    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="${
                    this.env.models['mail.thread'].find(thread =>
                        thread.id === 20 &&
                        thread.model === 'mail.channel'
                    ).localId
                }"]
            `).click();
        },
        message: "should wait until channel scrolled to bottom after opening it from the discuss sidebar",
        predicate: ({ scrollTop, threadViewer }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20 &&
                scrollTop === messageList.scrollHeight - messageList.clientHeight
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        31,
        `should display 31 messages inside the channel after clicking on it (the previously known
        message from Inbox and the 30 most recent messages that have been fetched)`
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
        `).length,
        1,
        "should display the message from Inbox inside the channel too"
    );

    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => document.querySelector('.o_Discuss_thread .o_ThreadView_messageList').scrollTop = 0,
        message: "should wait until channel 20 loaded more messages after scrolling to top",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        50,
        "should display 50 messages inside the channel after scrolling to load more (all messages fetched)"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 100).localId
            }"]
        `).length,
        1,
        "should still display the message from Inbox inside the channel too"
    );
});

QUnit.test('messages marked as read move to "History" mailbox', async function (assert) {
    assert.expect(10);

    // channel expected to be found in the sidebar
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    // expected messages
    this.data['mail.message'].records.push(
        {
            body: "not empty",
            id: 100, // random unique id, useful to link notification
            model: 'mail.channel', // value to link message to channel
            // needaction needs to be set here for message_fetch domain, because
            // mocked models don't have computed fields
            needaction: true,
            res_id: 20, // id of related channel
        },
        {
            body: "not empty",
            id: 101, // random unique id, useful to link notification
            model: 'mail.channel', // value to link message to channel
            // needaction needs to be set here for message_fetch domain, because
            // mocked models don't have computed fields
            needaction: true,
            res_id: 20, // id of related channel
        }
    );
    this.data['mail.notification'].records.push(
        // notification to have first message in inbox
        {
            mail_message_id: 100, // id of related message
            res_partner_id: this.data.currentPartnerId, // must be for current partner
        },
        // notification to have second message in inbox
        {
            mail_message_id: 101, // id of related message
            res_partner_id: this.data.currentPartnerId, // must be for current partner
        }
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.box_history',
            },
        },
    });
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
            }"]
        `).classList.contains('o-active'),
        "history mailbox should be active thread"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_empty`).length,
        1,
        "should have empty thread in history"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
        `).click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
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

    await afterNextRender(() =>
        document.querySelector('.o_widget_Discuss_controlPanelButtonMarkAllRead').click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
        `).classList.contains('o-active'),
        "inbox mailbox should still be active after mark as read"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Discuss_thread .o_MessageList_empty`).length,
        1,
        "inbox mailbox should now be empty after mark as read"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
            }"]
        `).click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
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

    this.data['mail.message'].records.push(
        {
            body: "not empty",
            id: 1,
            needaction: true,
            needaction_partner_ids: [this.data.currentPartnerId],
        },
        {
            body: "not empty",
            id: 2,
            needaction: true,
            needaction_partner_ids: [this.data.currentPartnerId],
        }
    );
    this.data['mail.notification'].records.push(
        {
            mail_message_id: 1,
            res_partner_id: this.data.currentPartnerId,
        },
        {
            mail_message_id: 2,
            res_partner_id: this.data.currentPartnerId,
        }
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.box_history',
            },
        },
    });
    assert.hasClass(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
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

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
            }"]
        `).click()
    );
    assert.hasClass(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.inbox.localId
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

    await afterNextRender(() =>
        document.querySelector(`
            .o_Message[data-message-local-id="${
                this.env.models['mail.message'].find(message => message.id === 1).localId
            }"] .o_Message_commandMarkAsRead
        `).click()
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "inbox mailbox should have one less message after clicking mark as read"
    );
    assert.containsOnce(
        document.body,
        `.o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 2).localId
        }"]`,
        "message still in inbox should be the one not marked as read"
    );

    await afterNextRender(() =>
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
            }"]
        `).click()
    );
    assert.hasClass(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.messaging.history.localId
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
        `.o_Message[data-message-local-id="${
            this.env.models['mail.message'].find(message => message.id === 1).localId
        }"]`,
        "message moved in history should be the one marked as read"
    );
});

QUnit.test('all messages in "Inbox" in "History" after marked all as read', async function (assert) {
    assert.expect(4);

    const messageOffset = 200;
    for (let id = messageOffset; id < messageOffset + 40; id++) {
        // message expected to be found in Inbox
        this.data['mail.message'].records.push({
            body: "not empty",
            id, // will be used to link notification to message
            // needaction needs to be set here for message_fetch domain, because
            // mocked models don't have computed fields
            needaction: true,
        });
        // notification to have message in Inbox
        this.data['mail.notification'].records.push({
            mail_message_id: id, // id of related message
            res_partner_id: this.data.currentPartnerId, // must be for current partner
        });

    }
    await this.start({
        waitUntilEvent: {
            eventName: 'o-component-message-list-scrolled',
            message: "should wait until inbox scrolled to its last message initially",
            predicate: ({ scrollTop, threadViewer }) => {
                const messageList = document.querySelector(`.o_Discuss_thread .o_ThreadView_messageList`);
                return (
                    threadViewer.thread.model === 'mail.box' &&
                    threadViewer.thread.id === 'inbox' &&
                    scrollTop === messageList.scrollHeight - messageList.clientHeight
                );
            },
        },
    });
    assert.containsN(
        document.body,
        '.o_Message',
        30,
        "there should be 30 messages that are loaded in Inbox"
    );

    await afterNextRender(async () => {
        const markAllReadButton = document.querySelector('.o_widget_Discuss_controlPanelButtonMarkAllRead');
        markAllReadButton.click();
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "there should no message in Inbox anymore"
    );

    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebarItem[data-thread-local-id="${
                    this.env.messaging.history.localId
                }"]
            `).click();
        },
        message: "should wait until history scrolled to its last message after opening it from the discuss sidebar",
        predicate: ({ scrollTop, threadViewer }) => {
            const messageList = document.querySelector('.o_MessageList');
            return (
                threadViewer.thread.model === 'mail.box' &&
                threadViewer.thread.id === 'history' &&
                scrollTop === messageList.scrollHeight - messageList.clientHeight
            );
        },
    });
    assert.containsN(
        document.body,
        '.o_Message',
        30,
        "there should be 30 messages in History"
    );

    // simulate a scroll to top to load more messages
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => document.querySelector('.o_MessageList').scrollTop = 0,
        message: "should wait until mailbox history loaded more messages after scrolling to top",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'mail.box' &&
                threadViewer.thread.id === 'history'
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

QUnit.test('receive new channel message: out of odoo focus (notification, channel)', async function (assert) {
    assert.expect(4);

    // channel expected to be found in the sidebar
    // with a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 20 });
    const bus = new Bus();
    bus.on('set_title_part', null, payload => {
        assert.step('set_title_part');
        assert.strictEqual(payload.part, '_chat');
        assert.strictEqual(payload.title, "1 Message");
    });
    await this.start({
        env: { bus },
        services: {
            bus_service: BusService.extend({
                _beep() {}, // Do nothing
                _poll() {}, // Do nothing
                _registerWindowUnload() {}, // Do nothing
                isOdooFocused: () => false,
                updateOption() {},
            }),
        },
    });

    // simulate receiving a new message with odoo focused
    await afterNextRender(() => {
        const messageData = {
            channel_ids: [20],
            id: 126,
            model: 'mail.channel',
            res_id: 20,
        };
        const notifications = [[['my-db', 'mail.channel', 20], messageData]];
        this.widget.call('bus_service', 'trigger', 'notification', notifications);
    });
    assert.verifySteps(['set_title_part']);
});

QUnit.test('receive new channel message: out of odoo focus (notification, chat)', async function (assert) {
    assert.expect(4);

    // chat expected to be found in the sidebar with the proper channel_type
    // and a random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ channel_type: "chat", id: 10 });
    const bus = new Bus();
    bus.on('set_title_part', null, payload => {
        assert.step('set_title_part');
        assert.strictEqual(payload.part, '_chat');
        assert.strictEqual(payload.title, "1 Message");
    });
    await this.start({
        env: { bus },
        services: {
            bus_service: BusService.extend({
                _beep() {}, // Do nothing
                _poll() {}, // Do nothing
                _registerWindowUnload() {}, // Do nothing
                isOdooFocused: () => false,
                updateOption() {},
            }),
        },
    });

    // simulate receiving a new message with odoo focused
    await afterNextRender(() => {
        const messageData = {
            channel_ids: [10],
            id: 126,
            model: 'mail.channel',
            res_id: 10,
        };
        const notifications = [[['my-db', 'mail.channel', 10], messageData]];
        this.widget.call('bus_service', 'trigger', 'notification', notifications);
    });
    assert.verifySteps(['set_title_part']);
});

QUnit.test('receive new channel messages: out of odoo focus (tab title)', async function (assert) {
    assert.expect(12);

    let step = 0;
    // channel and chat expected to be found in the sidebar
    // with random unique id and name that will be referenced in the test
    this.data['mail.channel'].records.push(
        { id: 20, name: "General" },
        { channel_type: 'chat', id: 10, public: 'private' }
    );
    const bus = new Bus();
    bus.on('set_title_part', null, payload => {
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
    await this.start({
        env: { bus },
        services: {
            bus_service: BusService.extend({
                _beep() {}, // Do nothing
                _poll() {}, // Do nothing
                _registerWindowUnload() {}, // Do nothing
                isOdooFocused: () => false,
                updateOption() {},
            }),
        },
    });

    // simulate receiving a new message in general with odoo focused
    await afterNextRender(() => {
        const messageData1 = {
            channel_ids: [20],
            id: 126,
            model: 'mail.channel',
            res_id: 20,
        };
        const notifications1 = [[['my-db', 'mail.channel', 20], messageData1]];
        this.widget.call('bus_service', 'trigger', 'notification', notifications1);
    });
    assert.verifySteps(['set_title_part']);

    // simulate receiving a new message in chat with odoo focused
    await afterNextRender(() => {
        const messageData2 = {
            channel_ids: [10],
            id: 127,
            model: 'mail.channel',
            res_id: 10,
        };
        const notifications2 = [[['my-db', 'mail.channel', 10], messageData2]];
        this.widget.call('bus_service', 'trigger', 'notification', notifications2);
    });
    assert.verifySteps(['set_title_part']);

    // simulate receiving another new message in chat with odoo focused
    await afterNextRender(() => {
        const messageData3 = {
            channel_ids: [10],
            id: 128,
            model: 'mail.channel',
            res_id: 10,
        };
        const notifications3 = [[['my-db', 'mail.channel', 20], messageData3]];
        this.widget.call('bus_service', 'trigger', 'notification', notifications3);
    });
    assert.verifySteps(['set_title_part']);
});

QUnit.test('auto-focus composer on opening thread', async function (assert) {
    assert.expect(14);

    // expected correspondent, with a random unique id that will be used to link
    // partner to chat and a random name that will be asserted in the test
    this.data['res.partner'].records.push({ id: 7, name: "Demo User" });
    this.data['mail.channel'].records.push(
        // channel expected to be found in the sidebar
        {
            id: 20, // random unique id, will be referenced in the test
            name: "General", // random name, will be asserted in the test
        },
        // chat expected to be found in the sidebar
        {
            channel_type: 'chat', // testing a chat is the goal of the test
            id: 10, // random unique id, will be referenced in the test
            members: [this.data.currentPartnerId, 7], // expected partners
            public: 'private', // expected value for testing a chat
        }
    );
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-name="Inbox"]
        `).length,
        1,
        "should have mailbox 'Inbox' in the sidebar"
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-name="Inbox"]
        `).classList.contains('o-active'),
        "mailbox 'Inbox' should be active initially"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-name="General"]
        `).length,
        1,
        "should have channel 'General' in the sidebar"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-name="General"]
        `).classList.contains('o-active'),
        "channel 'General' should not be active initially"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_DiscussSidebar_item[data-thread-name="Demo User"]
        `).length,
        1,
        "should have chat 'Demo User' in the sidebar"
    );
    assert.notOk(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-name="Demo User"]
        `).classList.contains('o-active'),
        "chat 'Demo User' should not be active initially"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer`).length,
        0,
        "there should be no composer when active thread of discuss is mailbox 'Inbox'"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebar_item[data-thread-name="General"]`).click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-name="General"]
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

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebar_item[data-thread-name="Demo User"]`).click()
    );
    assert.ok(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-name="Demo User"]
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

QUnit.test('mark channel as seen if last message is visible when switching channels when the previous channel had a more recent last message than the current channel', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push(
        { id: 10, message_unread_counter: 1, name: 'Bla' },
        { id: 11, message_unread_counter: 1, name: 'Blu' },
    );
    this.data['mail.message'].records.push({
        body: 'oldest message',
        channel_ids: [10],
        id: 10,
    }, {
        body: 'newest message',
        channel_ids: [11],
        id: 11,
    });
    await this.start({
        discuss: {
            context: {
                active_id: 'mail.channel_11',
            },
        },
        waitUntilEvent: {
            eventName: 'o-thread-view-hint-processed',
            message: "should wait until channel 11 loaded its messages initially",
            predicate: ({ hint, threadViewer }) => {
                return (
                    threadViewer.thread.model === 'mail.channel' &&
                    threadViewer.thread.id === 11 &&
                    hint.type === 'messages-loaded'
                );
            },
        },
    });
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="${
                    this.env.models['mail.thread'].findFromIdentifyingData({
                        id: 10,
                        model: 'mail.channel',
                    }).localId
                }"]
            `).click();
        },
        message: "should wait until last seen by current partner message id changed",
        predicate: ({ thread }) => {
            return (
                thread.id === 10 &&
                thread.model === 'mail.channel' &&
                thread.lastSeenByCurrentPartnerMessageId === 10
            );
        },
    }));
    assert.doesNotHaveClass(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="${
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 10,
                    model: 'mail.channel',
                }).localId
            }"]
        `),
        'o-unread',
        "sidebar item of channel ID 10 should no longer be unread"
    );
});

QUnit.test('add custom filter should filter messages accordingly to selected filter', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({
        id: 20,
        name: "General"
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                const domainsAsStr = args.kwargs.domain.map(domain => domain.join(''));
                assert.step(`message_fetch:${domainsAsStr.join(',')}`);
            }
            return this._super(...arguments);
        },
    });
    assert.verifySteps(['message_fetch:needaction=true'], "A message_fetch request should have been done for needaction messages as inbox is selected by default");

    // Open filter menu of control panel and select a custom filter (id = 0, the only one available)
    await toggleFilterMenu(document.body);
    await toggleAddCustomFilter(document.body);
    await applyFilter(document.body);
    assert.verifySteps(['message_fetch:id=0,needaction=true'], "A message_fetch request should have been done for selected filter & domain of current thread (inbox)");
});

});
});
});

});
