odoo.define('mail.component.DiscussTests', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    getMailServices,
    inputFiles,
    pause,
    start: utilsStart,
} = require('mail.owl.testUtils');

const testUtils = require('web.test_utils');

async function scroll({ scrollableElement, scrollTop }) {
    const scrollProm = testUtils.makeTestPromise();
    scrollableElement.addEventListener(
        'scroll',
        () => scrollProm.resolve(),
        false,
        { once: true });
    scrollableElement.scrollTop = scrollTop;
    await scrollProm; // scroll time
    await testUtils.nextTick(); // re-render
}

QUnit.module('mail.owl', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('Discuss', {
    beforeEach() {
        utilsBeforeEach(this);
        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { discuss, store, widget } = await utilsStart({
                ...params,
                autoOpenDiscuss: true,
                data: this.data,
            });
            this.discuss = discuss;
            this.store = store;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.widget) {
            this.widget.destroy();
        }
    }
});

QUnit.test('basic rendering', async function (assert) {
    assert.expect(4);

    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll('.o_Discuss_sidebar')
            .length,
        1,
        "should have a sidebar section");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Discuss_content')
            .length,
        1,
        "should have content section");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Discuss_thread')
            .length,
        1,
        "should have thread section inside content");
    assert.ok(
        document
            .querySelector('.o_Discuss_thread')
            .classList
            .contains('o_Thread'),
        "thread section should use thread component");
});

QUnit.test('basic rendering: sidebar', async function (assert) {
    assert.expect(20);

    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll(`.o_DiscussSidebar_group`)
            .length,
        3,
        "should have 3 groups in sidebar");
    assert.strictEqual(
        document
            .querySelectorAll(`.o_DiscussSidebar_groupMailbox`)
            .length,
        1,
        "should have group 'Mailbox' in sidebar");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupMailbox
                .o_DiscussSidebar_groupHeader`)
            .length,
        0,
        "mailbox category should not have any header");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupMailbox
                .o_DiscussSidebar_item`)
            .length,
        3,
        "should have 3 mailbox items");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupMailbox
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]`)
            .length,
        1,
        "should have inbox mailbox item");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupMailbox
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]`)
            .length,
        1,
        "should have starred mailbox item");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupMailbox
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_history"]`)
            .length,
        1,
        "should have history mailbox item");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_sidebar
                .o_DiscussSidebar_separator`)
            .length,
        1,
        "should have separator (between mailboxes and channels, but that's not tested)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel`)
            .length,
        1,
        "should have group 'Channel' in sidebar");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_groupHeader`)
            .length,
        1,
        "channel category should have a header");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_groupHeader
                .o_DiscussSidebar_groupTitle`)
            .length,
        1,
        "should have title in channel header");
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_groupHeader
                .o_DiscussSidebar_groupTitle`)
            .textContent
            .trim(),
        "Channels");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_list`)
            .length,
        1,
        "channel category should list items");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item`)
            .length,
        0,
        "channel category should have no item by default");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChat`)
            .length,
        1,
        "should have group 'Chat' in sidebar");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_groupHeader`)
            .length,
        1,
        "channel category should have a header");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_groupHeader
                .o_DiscussSidebar_groupTitle`)
            .length,
        1,
        "should have title in chat header");
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_groupHeader
                .o_DiscussSidebar_groupTitle`)
            .textContent
            .trim(),
        "Direct Messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_list`)
            .length,
        1,
        "chat category should list items");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_item`)
            .length,
        0,
        "chat category should have no item by default");
});

QUnit.test('sidebar: basic mailbox rendering', async function (assert) {
    assert.expect(6);

    await this.start();
    const inbox = document.querySelector(`
        .o_DiscussSidebar_groupMailbox
        .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]`);
    assert.strictEqual(
        inbox
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_activeIndicator`)
            .length,
        1,
        "mailbox should have active indicator");
    assert.strictEqual(
        inbox
            .querySelectorAll(`
                :scope
                .o_ThreadIcon`)
            .length,
        1,
        "mailbox should have an icon");
    assert.strictEqual(
        inbox
            .querySelectorAll(`
                :scope
                .o_ThreadIcon_mailboxInbox`)
            .length,
        1,
        "inbox should have 'inbox' icon");
    assert.strictEqual(
        inbox
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_name`)
            .length,
        1,
        "mailbox should have a name");
    assert.strictEqual(
        inbox
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .textContent,
        "Inbox",
        "inbox should have name 'Inbox'");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`)
            .length,
        0,
        "should have no counter when equal to 0 (default value)");
});

QUnit.test('sidebar: default active inbox', async function (assert) {
    assert.expect(1);

    await this.start();
    const inbox = document
        .querySelector(`
            .o_DiscussSidebar_groupMailbox
            .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]`);
    assert.ok(
        inbox
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "inbox should be active by default");
});

QUnit.test('sidebar: change item', async function (assert) {
    assert.expect(4);

    await this.start();
    assert.ok(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "inbox should be active by default");
    assert.notOk(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "starred should be inactive by default");

    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]`));
    assert.notOk(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "inbox mailbox should become inactive");
    assert.ok(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "starred mailbox should become active");
});

QUnit.test('sidebar: inbox with counter', async function (assert) {
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        needaction_inbox_counter: 100,
    });
    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`)
            .length,
        1,
        "should have a counter when different from 0");
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`)
            .textContent,
        "100",
        "should have counter value");
});

QUnit.test('sidebar: add channel', async function (assert) {
    assert.expect(3);

    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_groupHeaderItemAdd`)
            .length,
        1,
        "should be able to add channel from header");
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_groupHeaderItemAdd`)
            .title,
        "Add or join a channel");

    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_groupHeaderItemAdd`));
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_itemNew`)
            .length,
        1,
        "should have item to add a new channel");
});

QUnit.test('sidebar: basic channel rendering', async function (assert) {
    assert.expect(14);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item`)
            .length,
        1,
        "should have one channel item");
    let channel = document.querySelector(`
        .o_DiscussSidebar_groupChannel
        .o_DiscussSidebar_item`);
    assert.strictEqual(
        channel
            .dataset
            .threadLocalId,
        "mail.channel_20",
        "should have channel with Id 20");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_activeIndicator`)
            .length,
        1,
        "should have active indicator");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_activeIndicator.o-item-active`)
            .length,
        0,
        "should not be active by default");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_ThreadIcon`)
            .length,
        1,
        "should have an icon");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_name`)
            .length,
        1,
        "should have a name");
    assert.strictEqual(
        channel
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .textContent,
        "General",
        "should have name value");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commands`)
            .length,
        1,
        "should have commands");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_command`)
            .length,
        2,
        "should have 2 commands");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commandSettings`)
            .length,
        1,
        "should have 'settings' command");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commandLeave`)
            .length,
        1,
        "should have 'leave' command");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_counter`)
            .length,
        0,
        "should have a counter when equals 0 (default value)");

    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item`));
    channel = document.querySelector(`
        .o_DiscussSidebar_groupChannel
        .o_DiscussSidebar_item`);
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_activeIndicator.o-item-active`)
            .length,
        1,
        "channel should become active");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_composer`)
            .length,
        1,
        "should have composer section inside thread content (can post message in channel)");
});

QUnit.test('sidebar: channel rendering with needaction counter', async function (assert) {
    assert.expect(5);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
                message_needaction_counter: 10,
            }],
        },
    });
    await this.start();
    const channel = document.querySelector(`
        .o_DiscussSidebar_groupChannel
        .o_DiscussSidebar_item`);
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_counter`)
            .length,
        1,
        "should have a counter when different from 0");
    assert.strictEqual(
        channel
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_counter`)
            .textContent,
        "10",
        "should have counter value");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_command`)
            .length,
        1,
        "should have single command");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commandSettings`)
            .length,
        1,
        "should have 'settings' command");
    assert.strictEqual(
        channel
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commandLeave`)
            .length,
        0,
        "should not have 'leave' command");
});

QUnit.test('sidebar: public/private channel rendering', async function (assert) {
    assert.expect(5);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 100,
                name: "channel1",
                public: 'public',
            }],
            channel_private_group: [{
                channel_type: "channel",
                id: 101,
                name: "channel2",
                public: 'private',
            }],
        },
    });
    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item`)
            .length,
        2,
        "should have 2 channel items");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_100"]`)
            .length,
        1,
        "should have channel1 (Id 100)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_101"]`)
            .length,
        1,
        "should have channel2 (Id 101)");
    const channel1 = document.querySelector(`
        .o_DiscussSidebar_groupChannel
        .o_DiscussSidebar_item[data-thread-local-id="mail.channel_100"]`);
    const channel2 = document.querySelector(`
        .o_DiscussSidebar_groupChannel
        .o_DiscussSidebar_item[data-thread-local-id="mail.channel_101"]`);
    assert.strictEqual(
        channel1
            .querySelectorAll(`
                :scope
                .o_ThreadIcon_channelPublic`)
            .length,
        1,
        "channel1 (public) has hashtag icon");
    assert.strictEqual(
        channel2
            .querySelectorAll(`
                :scope
                .o_ThreadIcon_channelPrivate`)
            .length,
        1,
        "channel2 (private) has lock icon");
});

QUnit.test('sidebar: basic chat rendering', async function (assert) {
    assert.expect(11);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_direct_message: [{
                channel_type: "chat",
                direct_partner: [{
                    id: 7,
                    name: "Demo",
                }],
                id: 10,
            }],
        },
    });
    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_item`)
            .length,
        1,
        "should have one chat item");
    const chat = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item`);
    assert.strictEqual(
        chat
            .dataset
            .threadLocalId,
        "mail.channel_10",
        "should have chat with Id 20");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_activeIndicator`)
            .length,
        1,
        "should have active indicator");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_ThreadIcon`)
            .length,
        1,
        "should have an icon");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_name`)
            .length,
        1,
        "should have a name");
    assert.strictEqual(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .textContent,
        "Demo",
        "should have direct partner name as name");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commands`)
            .length,
        1,
        "should have commands");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_command`)
            .length,
        2,
        "should have 2 commands");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commandRename`)
            .length,
        1,
        "should have 'rename' command");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commandUnpin`)
            .length,
        1,
        "should have 'unpin' command");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_counter`)
            .length,
        0,
        "should have a counter when equals 0 (default value)");
});

QUnit.test('sidebar: chat rendering with unread counter', async function (assert) {
    assert.expect(5);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_direct_message: [{
                channel_type: "chat",
                direct_partner: [{
                    id: 7,
                    name: "Demo",
                }],
                id: 10,
                message_unread_counter: 100,
            }],
        },
    });
    await this.start();
    const chat = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item`);
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_counter`)
            .length,
        1,
        "should have a counter when different from 0");
    assert.strictEqual(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_counter`)
            .textContent,
        "100",
        "should have counter value");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_command`)
            .length,
        1,
        "should have single command");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commandRename`)
            .length,
        1,
        "should have 'rename' command");
    assert.strictEqual(
        chat
            .querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_commandUnpin`)
            .length,
        0,
        "should not have 'unpin' command");
});

QUnit.test('sidebar: chat im_status rendering', async function (assert) {
    assert.expect(7);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_direct_message: [{
                channel_type: "chat",
                direct_partner: [{
                    id: 1,
                    im_status: 'offline',
                    name: "Partner1",
                }],
                id: 11,
            }, {
                channel_type: "chat",
                direct_partner: [{
                    id: 2,
                    im_status: 'online',
                    name: "Partner2",
                }],
                id: 12,
            }, {
                channel_type: "chat",
                direct_partner: [{
                    id: 3,
                    im_status: 'away',
                    name: "Partner3",
                }],
                id: 13,
            }],
        },
    });
    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_item`)
            .length,
        3,
        "should have 3 chat items");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_sidebar
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_11"]`)
            .length,
        1,
        "should have Partner1 (Id 11)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_sidebar
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_12"]`)
            .length,
        1,
        "should have Partner2 (Id 12)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_sidebar
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_13"]`)
            .length,
        1,
        "should have Partner3 (Id 13)");
    const chat1 = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item[data-thread-local-id="mail.channel_11"]`);
    const chat2 = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item[data-thread-local-id="mail.channel_12"]`);
    const chat3 = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item[data-thread-local-id="mail.channel_13"]`);
    assert.strictEqual(
        chat1
            .querySelectorAll(`
                :scope
                .o_ThreadIcon_offline`)
            .length,
        1,
        "chat1 should have offline icon");
    assert.strictEqual(
        chat2
            .querySelectorAll(`
                :scope
                .o_ThreadIcon_online`)
            .length,
        1,
        "chat2 should have online icon");
    assert.strictEqual(
        chat3
            .querySelectorAll(`
                :scope
                .o_ThreadIcon_away`)
            .length,
        1,
        "chat3 should have away icon");
});

QUnit.test('sidebar: chat custom name', async function (assert) {
    assert.expect(1);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_direct_message: [{
                channel_type: "chat",
                custom_channel_name: "Marc",
                direct_partner: [{
                    id: 7,
                    name: "Marc Demo",
                }],
                id: 10,
            }],
        },
    });
    await this.start();
    const chat = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item`);
    assert.strictEqual(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .textContent,
        "Marc",
        "chat should have custom name as name");
});

QUnit.test('sidebar: rename chat', async function (assert) {
    assert.expect(8);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_direct_message: [{
                custom_channel_name: "Marc",
                channel_type: "chat",
                direct_partner: [{
                    id: 7,
                    name: "Marc Demo",
                }],
                id: 10,
            }],
        },
    });
    await this.start({
        mockRPC(route, args) {
            if (args.method === 'channel_set_custom_name') {
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        },
    });
    const chat = document.querySelector(`
        .o_DiscussSidebar_groupChat
        .o_DiscussSidebar_item`);
    assert.strictEqual(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .textContent,
        "Marc",
        "chat should have custom name as name");
    assert.notOk(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .classList
            .contains('o-editable'),
        "chat name should not be editable");

    await testUtils.dom.click(
        chat.querySelector(`
            :scope
            .o_DiscussSidebarItem_commandRename`),
        { allowInvisible: true });
    assert.ok(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .classList
            .contains('o-editable'),
        "chat should have editable name");
    assert.strictEqual(
        chat.
            querySelectorAll(`
                :scope
                .o_DiscussSidebarItem_nameInput`)
            .length,
        1,
        "chat should have editable name input");
    assert.strictEqual(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_nameInput`)
            .value,
        "Marc",
        "editable name input should have custom chat name as value by default");
    assert.strictEqual(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_nameInput`)
            .placeholder,
        "Marc Demo",
        "editable name input should have partner name as placeholder");

    chat
        .querySelector(`
            :scope
            .o_DiscussSidebarItem_nameInput`)
        .value = "Demo";
    const kevt = new window.KeyboardEvent('keydown', { key: "Enter" });
    chat
        .querySelector(`
            :scope
            .o_DiscussSidebarItem_nameInput`)
        .dispatchEvent(kevt);
    await testUtils.nextTick(); // re-render
    assert.notOk(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .classList
            .contains('o-editable'),
        "chat should no longer show editable name");
    assert.strictEqual(
        chat
            .querySelector(`
                :scope
                .o_DiscussSidebarItem_name`)
            .textContent,
        "Demo",
        "chat should have renamed name as name");
});

QUnit.test('default thread rendering', async function (assert) {
    assert.expect(16);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll('.o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]')
            .length,
        1,
        "should have inbox mailbox in the sidebar");
    assert.strictEqual(
        document
            .querySelectorAll('.o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]')
            .length,
        1,
        "should have starred mailbox in the sidebar");
    assert.strictEqual(
        document
            .querySelectorAll('.o_DiscussSidebar_item[data-thread-local-id="mail.box_history"]')
            .length,
        1,
        "should have history mailbox in the sidebar");
    assert.strictEqual(
        document
            .querySelectorAll('.o_DiscussSidebar_item[data-thread-local-id="mail.channel_20"]')
            .length,
        1,
        "should have 'general' channel in the sidebar");
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]')
            .classList
            .contains('o-active'),
        "inbox mailbox should be active thread");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .length,
        1,
        "should have empty thread in inbox");
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .textContent
            .trim(),
        "Congratulations, your inbox is empty  New messages appear here.");

    await testUtils.dom.click(
        document.querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]'));
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]')
            .classList
            .contains('o-active'),
        "starred mailbox should be active thread");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .length,
        1,
        "should have empty thread in starred");
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .textContent
            .trim(),
        "No starred messages  You can mark any message as 'starred', and it shows up in this mailbox.");

    await testUtils.dom.click(
        document.querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_history"]'));
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_history"]')
            .classList
            .contains('o-active'),
        "history mailbox should be active thread");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .length,
        1,
        "should have empty thread in starred");
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .textContent
            .trim(),
        "No history messages  Messages marked as read will appear in the history.");

    await testUtils.dom.click(
        document.querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.channel_20"]'));
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.channel_20"]')
            .classList
            .contains('o-active'),
        "channel 'general' should be active thread");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .length,
        1,
        "should have empty thread in starred");
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .textContent
            .trim(),
        "There are no messages in this conversation.");
});

QUnit.test('initially load messages from inbox', async function (assert) {
    assert.expect(5);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                assert.step('message_fetch');
                assert.strictEqual(
                    args.kwargs.limit,
                    30,
                    "should fetch up to 30 messages");
                assert.strictEqual(
                    args.args.length,
                    1,
                    "should have a single item in args");
                assert.deepEqual(
                    args.args[0],
                    [["needaction", "=", true]],
                    "should fetch needaction messages");
            }
            return this._super(...arguments);
        },
    });
    assert.verifySteps(['message_fetch']);
});

QUnit.test('default select thread in discuss params', async function (assert) {
    assert.expect(1);

    await this.start({
        params: {
            default_active_id: 'mail.box_starred',
        },
    });
    assert.ok(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "starred mailbox should become active");
});

QUnit.test('auto-select thread in discuss context', async function (assert) {
    assert.expect(1);

    await this.start({
        context: {
            active_id: 'mail.box_starred',
        },
    });
    assert.ok(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "starred mailbox should become active");
});

QUnit.test('load single message from channel initially', async function (assert) {
    assert.expect(8);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                assert.strictEqual(
                    args.kwargs.limit,
                    30,
                    "should fetch up to 30 messages");
                assert.strictEqual(
                    args.args.length,
                    1,
                    "should have a single item in args");
                assert.deepEqual(
                    args.args[0],
                    [["channel_ids", "in", [20]]],
                    "should fetch messages from channel");
                return [{
                    author_id: [11, "Demo"],
                    body: "<p>body</p>",
                    channel_ids: [20],
                    date: "2019-04-20 10:00:00",
                    id: 100,
                    message_type: 'comment',
                    model: 'mail.channel',
                    record_name: 'General',
                    res_id: 20,
                }];
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList`)
            .length,
        1,
        "should have list of messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorDate`)
            .length,
        1,
        "should have a single date separator"); // to check: may be client timezone dependent
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorLabelDate`)
            .textContent,
        "April 20, 2019",
        "should display date day of messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        1,
        "should have a single message");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_100"]`)
            .length,
        1,
        "should have message with Id 100");
});

QUnit.test('basic rendering of message', async function (assert) {
    assert.expect(13);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [{
                    author_id: [11, "Demo"],
                    body: "<p>body</p>",
                    channel_ids: [20],
                    date: "2019-04-20 10:00:00",
                    id: 100,
                    message_type: 'comment',
                    model: 'mail.channel',
                    record_name: 'General',
                    res_id: 20,
                }];
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    const message = document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList
        .o_MessageList_message[data-message-local-id="mail.message_100"]`);
    assert.strictEqual(
            message
                .querySelectorAll(`
                    :scope
                    .o_Message_sidebar`)
                .length,
            1,
            "should have message sidebar of message");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_authorAvatar`)
            .length,
        1,
        "should have author avatar in sidebar of message");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_authorAvatar`)
            .dataset
            .src,
        "/web/image/res.partner/11/image_128",
        "should have url of message in author avatar sidebar");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_core`)
            .length,
        1,
        "should have core part of message");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_header`)
            .length,
        1,
        "should have header in core part of message");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_authorName`)
            .length,
        1,
        "should have author name in header of message");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_authorName`)
            .textContent,
        "Demo",
        "should have textually author name in header of message");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_header
                .o_Message_date`)
            .length,
        1,
        "should have date in header of message");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_header
                .o_Message_commands`)
            .length,
        1,
        "should have commands in header of message");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_header
                .o_Message_command`)
            .length,
        1,
        "should have a single command in header of message");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_commandStar`)
            .length,
        1,
        "should have command to star message");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_content`)
            .length,
        1,
        "should have content in core part of message");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_content`)
            .textContent
            .trim(),
        "body",
        "should have body of message in content part of message");
});

QUnit.test('basic rendering of squashed message', async function (assert) {
    // messages are squashed when "close", e.g. less than 1 minute has elapsed
    // from messages of same author and same thread. Note that this should
    // be working in non-mailboxes
    assert.expect(12);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [{
                    author_id: [11, "Demo"],
                    body: "<p>body1</p>",
                    channel_ids: [20],
                    date: "2019-04-20 10:00:00",
                    id: 100,
                    message_type: 'comment',
                    model: 'mail.channel',
                    record_name: 'General',
                    res_id: 20,
                }, {
                    author_id: [11, "Demo"],
                    body: "<p>body2</p>",
                    channel_ids: [20],
                    date: "2019-04-20 10:00:30",
                    id: 101,
                    message_type: 'comment',
                    model: 'mail.channel',
                    record_name: 'General',
                    res_id: 20,
                }];
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "should have 2 messages");
    const message1 = document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList
        .o_MessageList_message[data-message-local-id="mail.message_100"]`);
    const message2 = document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList
        .o_MessageList_message[data-message-local-id="mail.message_101"]`);
    assert.notOk(
        message1
            .classList
            .contains('o-squashed'),
        "message 1 should not be squashed");
    assert.notOk(
        message1
            .querySelector(`
                :scope
                .o_Message_sidebar`)
            .classList
            .contains('o-message-squashed'),
        "message 1 should not have squashed sidebar");
    assert.ok(
        message2
            .classList
            .contains('o-squashed'),
        "message 2 should be squashed");
    assert.ok(
        message2
            .querySelector(`
                :scope
                .o_Message_sidebar`)
            .classList
            .contains('o-message-squashed'),
        "message 2 should have squashed sidebar");
    assert.strictEqual(
        message2
            .querySelectorAll(`
                :scope
                .o_Message_sidebar
                .o_Message_date`)
            .length,
        1,
        "message 2 should have date in sidebar");
    assert.strictEqual(
        message2
            .querySelectorAll(`
                :scope
                .o_Message_sidebar
                .o_Message_commands`)
            .length,
        1,
        "message 2 should have some commands in sidebar");
    assert.strictEqual(
        message2
            .querySelectorAll(`
                :scope
                .o_Message_sidebar
                .o_Message_commandStar`)
            .length,
        1,
        "message 2 should have star command in sidebar");
    assert.strictEqual(
        message2
            .querySelectorAll(`
                :scope
                .o_Message_core`)
            .length,
        1,
        "message 2 should have core part");
    assert.strictEqual(
        message2
            .querySelectorAll(`
                :scope
                .o_Message_header`)
            .length,
        0,
        "message 2 should have a header in core part");
    assert.strictEqual(
        message2
            .querySelectorAll(`
                :scope
                .o_Message_content`)
            .length,
        1,
        "message 2 should have some content in core part");
    assert.strictEqual(
        message2
            .querySelector(`
                :scope
                .o_Message_content`)
            .textContent
            .trim(),
        "body2",
        "message 2 should have body in content part");
});

QUnit.test('inbox messages are never squashed', async function (assert) {
    assert.expect(3);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                // fetching messages from inbox
                return [{
                    author_id: [11, "Demo"],
                    body: "<p>body1</p>",
                    channel_ids: [20],
                    date: "2019-04-20 10:00:00",
                    id: 100,
                    message_type: 'comment',
                    model: 'mail.channel',
                    needaction: true,
                    needaction_partner_ids: [3],
                    record_name: 'General',
                    res_id: 20,
                }, {
                    author_id: [11, "Demo"],
                    body: "<p>body2</p>",
                    channel_ids: [20],
                    date: "2019-04-20 10:00:30",
                    id: 101,
                    message_type: 'comment',
                    model: 'mail.channel',
                    needaction: true,
                    needaction_partner_ids: [3],
                    record_name: 'General',
                    res_id: 20,
                }];
            }
            return this._super(...arguments);
        },
        session: {
            partner_id: 3,
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "should have 2 messages");
    const message1 = document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList
        .o_MessageList_message[data-message-local-id="mail.message_100"]`);
    const message2 = document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList
        .o_MessageList_message[data-message-local-id="mail.message_101"]`);
    assert.notOk(
        message1
            .classList
            .contains('o-squashed'),
        "message 1 should not be squashed");
    assert.notOk(
        message2
            .classList
            .contains('o-squashed'),
        "message 2 should not be squashed");
});

QUnit.test('load all messages from channel initially, less than fetch limit (29 < 30)', async function (assert) {
    assert.expect(5);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                assert.strictEqual(args.kwargs.limit, 30, "should fetch up to 30 messages");
                let messagesData = [];
                // 29 messages
                for (let i = 28; i >= 0; i--) {
                    messagesData.push({
                        author_id: [10+i, `User${i}`],
                        body: `<p>body${i}</p>`,
                        channel_ids: [20],
                        date: "2019-04-20 10:00:00",
                        id: 100+i,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: 'General',
                        res_id: 20,
                    });
                }
                return messagesData;
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorDate`)
            .length,
        1,
        "should have a single date separator"); // to check: may be client timezone dependent
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorLabelDate`)
            .textContent,
        "April 20, 2019",
        "should display date day of messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        29,
        "should have 29 messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_loadMore`)
            .length,
        0,
        "should not have load more link");
});

QUnit.test('load more messages from channel', async function (assert) {
    assert.expect(8);

    let step = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                step++;
                if (step === 1) {
                    // fetching messages from channel (initial load)
                    assert.strictEqual(
                        args.kwargs.limit,
                        30,
                        "should fetch up to 30 messages");
                    let messagesData = [];
                    // 30 messages
                    for (let i = 39; i >= 10; i--) {
                        messagesData.push({
                            author_id: [10+i, `User${i}`],
                            body: `<p>body${i}</p>`,
                            channel_ids: [20],
                            date: "2019-04-20 10:00:00",
                            id: 100+i,
                            message_type: 'comment',
                            model: 'mail.channel',
                            record_name: 'General',
                            res_id: 20,
                        });
                    }
                    return messagesData;
                }
                if (step === 2) {
                    // fetching more messages from channel (load more)
                    assert.strictEqual(
                        args.kwargs.limit,
                        30,
                        "should fetch up to 30 messages");
                    let messagesData = [];
                    // 10 messages
                    for (let i = 9; i >= 0; i--) {
                        messagesData.push({
                            author_id: [10+i, `User${i}`],
                            body: `<p>body${i}</p>`,
                            channel_ids: [20],
                            date: "2019-04-20 10:00:00",
                            id: 100+i,
                            message_type: 'comment',
                            model: 'mail.channel',
                            record_name: 'General',
                            res_id: 20,
                        });
                    }
                    return messagesData;
                }
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorDate`)
            .length,
        1,
        "should have a single date separator"); // to check: may be client timezone dependent
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorLabelDate`)
            .textContent,
        "April 20, 2019",
        "should display date day of messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        30,
        "should have 30 messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_loadMore`)
            .length,
        1,
        "should have load more link");

    document
        .querySelector(`
            .o_Discuss_thread
            .o_Thread_messageList
            .o_MessageList_loadMore`)
        .click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        40,
        "should have 40 messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_loadMore`)
            .length,
        0,
        "should not longer have load more link (all messages loaded)");
});

QUnit.test('auto-scroll to bottom of thread', async function (assert) {
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                let messagesData = [];
                // 25 messages
                for (let i = 1; i <= 25; i++) {
                    messagesData.push({
                        author_id: [10+i, `User${i}`],
                        body: `<p>body${i}</p>`,
                        channel_ids: [20],
                        date: "2019-04-20 10:00:00",
                        id: 100+i,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: 'General',
                        res_id: 20,
                    });
                }
                return messagesData;
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        25,
        "should have 25 messages");
    const messageList= document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList`);
    assert.strictEqual(
        messageList.scrollTop + messageList.clientHeight,
        messageList.scrollHeight,
        "should have scrolled to bottom of thread");
});

QUnit.test('load more messages from channel (auto-load on scroll)', async function (assert) {
    assert.expect(3);

    let step = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                step++;
                if (step === 1) {
                    // fetching messages from channel (initial load)
                    let messagesData = [];
                    // 30 messages
                    for (let i = 39; i >= 10; i--) {
                        messagesData.push({
                            author_id: [10+i, `User${i}`],
                            body: `<p>body${i}</p>`,
                            channel_ids: [20],
                            date: "2019-04-20 10:00:00",
                            id: 100+i,
                            message_type: 'comment',
                            model: 'mail.channel',
                            record_name: 'General',
                            res_id: 20,
                        });
                    }
                    return messagesData;
                }
                if (step === 2) {
                    // fetching more messages from channel (load more)
                    let messagesData = [];
                    // 10 messages
                    for (let i = 9; i >= 0; i--) {
                        messagesData.push({
                            author_id: [10+i, `User${i}`],
                            body: `<p>body${i}</p>`,
                            channel_ids: [20],
                            date: "2019-04-20 10:00:00",
                            id: 100+i,
                            message_type: 'comment',
                            model: 'mail.channel',
                            record_name: 'General',
                            res_id: 20,
                        });
                    }
                    return messagesData;
                }
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        30,
        "should have 30 messages");

    await scroll({
        scrollableElement: document.querySelector(`
            .o_Discuss_thread
            .o_Thread_messageList`),
        scrollTop: 0,
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        40,
        "should have 40 messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Dsiscuss_thread
                .o_Thread_messageList
                .o_MessageList_loadMore`)
            .length,
        0,
        "should not longer have load more link (all messages loaded)");
});

QUnit.test('new messages separator', async function (assert) {
    // this test requires several messages so that the last message is not
    // visible. This is necessary in order to display 'new messages' and not
    // remove from DOM right away from seeing last message.
    assert.expect(5);

    let step = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                message_unread_counter: 0,
                name: "General",
                seen_message_id: 125,
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                step++;
                if (step === 1) {
                    // fetching messages from channel (initial load)
                    let messagesData = [];
                    // 25 messages
                    for (let i = 1; i <= 25; i++) {
                        messagesData.push({
                            author_id: [10+i, `User${i}`],
                            body: `<p>body${i}</p>`,
                            channel_ids: [20],
                            date: "2019-04-20 10:00:00",
                            id: 100+i,
                            message_type: 'comment',
                            model: 'mail.channel',
                            record_name: 'General',
                            res_id: 20,
                        });
                    }
                    return messagesData;
                }
                if (step === 2) {
                    throw new Error("should not fetch more messages");
                }
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        25,
        "should have 25 messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorNewMessages`)
            .length,
        0,
        "should not display 'new messages' separator");

    await scroll({
        scrollableElement: document.querySelector(`
            .o_Discuss_thread
            .o_Thread_messageList`),
        scrollTop: 0,
    });
    // simulate receiving a new message
    const data = {
        author_id: [36, "User26"],
        body: "<p>boddy26</p>",
        channel_ids: [20],
        date: "2019-04-20 10:00:00",
        id: 126,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'General',
        res_id: 20,
    };
    const notifications = [ [['my-db', 'mail.channel', 20], data] ];
    this.widget.call('bus_service', 'trigger', 'notification', notifications);
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        26,
        "should have 26 messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorNewMessages`)
            .length,
        1,
        "should display 'new messages' separator");

    // scroll to bottom
    await scroll({
        scrollableElement: document.querySelector(`
            .o_Discuss_thread
            .o_Thread_messageList`),
        scrollTop: document.querySelector(`
            .o_Discuss_thread
            .o_Thread_messageList`).scrollHeight,
    });
    await testUtils.nextTick(); // re-render (t-transition, even with CSS disabled)
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_separatorNewMessages`)
            .length,
        0,
        "should no longer display 'new messages' separator (message seen)");
});

QUnit.test('restore thread scroll position', async function (assert) {
    assert.expect(4);

    let step = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 1,
                name: "channel1",
            }, {
                channel_type: "channel",
                id: 2,
                name: "channel2",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                step++;
                if (step === 1) {
                    // fetching messages from channel1 (initial load)
                    let messagesData = [];
                    // 25 messages
                    for (let i = 1; i <= 25; i++) {
                        messagesData.push({
                            author_id: [10+i, `User${i}`],
                            body: `<p>body${i}</p>`,
                            channel_ids: [1],
                            date: "2019-04-20 10:00:00",
                            id: 100+i,
                            message_type: 'comment',
                            model: 'mail.channel',
                            record_name: 'channel1',
                            res_id: 1,
                        });
                    }
                    return messagesData;
                }
                if (step === 2) {
                    // fetching messages from channel2 (initial load)
                    let messagesData = [];
                    // 25 messages
                    for (let i = 1; i <= 25; i++) {
                        messagesData.push({
                            author_id: [10+i, `User${i}`],
                            body: `<p>body${i}</p>`,
                            channel_ids: [2],
                            date: "2019-04-20 10:00:00",
                            id: 200+i,
                            message_type: 'comment',
                            model: 'mail.channel',
                            record_name: 'channel2',
                            res_id: 2,
                        });
                    }
                    return messagesData;
                }
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_1',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        25,
        "should have 25 messages");

    // scroll to top of channel1
    await scroll({
        scrollableElement: document.querySelector(`
            .o_Discuss_thread
            .o_Thread_messageList`),
        scrollTop: 0,
    });
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList`)
            .scrollTop,
        0,
        "should have scrolled to top of thread");

    // select channel2
    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item[data-thread-local-id="mail.channel_2"]`));
    await testUtils.nextTick(); // re-render
    // select channel1
    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item[data-thread-local-id="mail.channel_1"]`));
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList`)
            .scrollTop,
        0,
        "should have recovered scroll position of channel1 (scroll to top)");

    // select channel2
    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_groupChannel
            .o_DiscussSidebar_item[data-thread-local-id="mail.channel_2"]`));
    await testUtils.nextTick(); // re-render
    const messageList = document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList`);
    assert.strictEqual(
        messageList.scrollTop + messageList.clientHeight,
        messageList.scrollHeight,
        "should have recovered scroll position of channel2 (scroll to bottom)");
});

QUnit.test('message origin redirect to channel', async function (assert) {
    assert.expect(15);

    let step = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 1,
                name: "channel1",
            }, {
                channel_type: 'channel',
                id: 2,
                name: "channel2",
            }],
        },
    });
    let messagesData = [{
        author_id: [10, "User1"],
        body: `<p>message1</p>`,
        channel_ids: [1, 2],
        date: "2019-04-20 10:00:00",
        id: 100,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: "channel1",
        res_id: 1,
    }, {
        author_id: [11, "User2"],
        body: `<p>message2</p>`,
        channel_ids: [1, 2],
        date: "2019-04-20 10:00:00",
        id: 101,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: "channel2",
        res_id: 2,
    }];
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                step++;
                if (step === 1) {
                    // fetching messages from channel1 (initial load)
                    return messagesData;
                }
                if (step === 2) {
                    // fetching messages from channel2 (initial load)
                    return messagesData;
                }
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_1',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "should have 2 messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_100"]`)
            .length,
        1,
        "should have message1 (Id 100)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_101"]`)
            .length,
        1,
        "should have message2 (Id 101)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_100"]
                .o_Message_header
                .o_Message_originThread`)
            .length,
        0,
        "message1 should not have origin part in channel1 (same origin as channel)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_101"]
                .o_Message_header
                .o_Message_originThread`)
            .length,
        1,
        "message2 should have origin part (origin is channel2 !== channel1)");
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_101"]
                .o_Message_header
                .o_Message_originThread`)
            .textContent
            .trim(),
        "(from #channel2)",
        "message2 should display name of origin channel");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_101"]
                .o_Message_header
                .o_Message_originThreadLink`)
            .length,
        1,
        "message2 should have link to redirect to origin");

    // click on origin link of message2 (= channel2)
    document
        .querySelector(`
            .o_Discuss_thread
            .o_Thread_messageList
            .o_MessageList_message[data-message-local-id="mail.message_101"]
            .o_Message_header
            .o_Message_originThreadLink`)
        .click();
    await testUtils.nextTick(); // re-render
    assert.ok(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_2"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "channel2 should be active channel on redirect from discuss app");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "should have 2 messages");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_100"]`)
            .length,
        1,
        "should have message1 (Id 100)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_101"]`)
            .length,
        1,
        "should have message2 (Id 101)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_100"]
                .o_Message_header
                .o_Message_originThread`)
            .length,
        1,
        "message1 should have origin thread part (= channel1 !== channel2)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_101"]
                .o_Message_header
                .o_Message_originThread`)
            .length,
        0,
        "message2 should not have origin thread part in channel2 (same as current channel)");
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_100"]
                .o_Message_header
                .o_Message_originThread`)
            .textContent
            .trim(),
        "(from #channel1)",
        "message1 should display name of origin channel");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message[data-message-local-id="mail.message_100"]
                .o_Message_header
                .o_Message_originThreadLink`)
            .length,
        1,
        "message1 should have link to redirect to origin channel");
});

QUnit.test('redirect to author (open chat)', async function (assert) {
    assert.expect(9);

    let step = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 1,
                name: "General",
            }],
            channel_direct_message: [{
                channel_type: "chat",
                direct_partner: [{
                    id: 7,
                    name: "Demo",
                }],
                id: 10,
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                step++;
                if (step === 1) {
                    // fetching messages from General (initial load)
                    return [{
                        author_id: [7, "Demo"],
                        body: `<p>message1</p>`,
                        channel_ids: [1],
                        date: "2019-04-20 10:00:00",
                        id: 100,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: "General",
                        res_id: 1,
                    }, {
                        author_id: [3, "Me"],
                        body: `<p>message2</p>`,
                        channel_ids: [1],
                        date: "2019-04-20 10:00:00",
                        id: 101,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: "General",
                        res_id: 1,
                    }];
                }
                if (step === 2) {
                    // fetching messages from DM (initial load)
                    return [];
                }
            }
            if (args.model === 'res.users' && args.method === 'search') {
                return [2];
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_1',
        },
        session: {
            partner_id: 3,
        },
    });
    assert.ok(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_1"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "channel 'General' should be active");
    assert.notOk(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_10"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "DM 'Demo' should not be active");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "should have 2 messages");
    const msg1 = document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList
        .o_MessageList_message[data-message-local-id="mail.message_100"]`);
    const msg2 = document.querySelector(`
        .o_Discuss_thread
        .o_Thread_messageList
        .o_MessageList_message[data-message-local-id="mail.message_101"]`);
    assert.strictEqual(
        msg1
            .querySelectorAll(`
                :scope
                .o_Message_authorAvatar`)
            .length,
        1,
        "message1 should have author image");
    assert.ok(
        msg1
            .querySelector(`
                :scope
                .o_Message_authorAvatar`)
            .classList
            .contains('o_redirect'),
        "message1 should have redirect to author");
    assert.strictEqual(
        msg2
            .querySelectorAll(`
                :scope
                .o_Message_authorAvatar`)
            .length,
        1,
        "message2 should have author image");
    assert.notOk(
        msg2
            .querySelector(`
                :scope
                .o_Message_authorAvatar`)
            .classList
            .contains('o_redirect'),
        "message2 should not have redirect to author (self-author)");

    await testUtils.dom.click(
        msg1.querySelector(`
            :scope
            .o_Message_authorAvatar`));
    await testUtils.nextTick(); // re-render
    assert.notOk(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_1"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "channel 'General' should become inactive after author redirection");
    assert.ok(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChat
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_10"]
                .o_DiscussSidebarItem_activeIndicator`)
            .classList
            .contains('o-item-active'),
        "chat 'Demo' should become active after author redirection");
});

QUnit.test('sidebar quick search', async function (assert) {
    // feature enables at 20 or more channels
    assert.expect(6);

    let channelsData = [];
    for (let id = 1; id <= 20; id++) {
        channelsData.push({
            channel_type: 'channel',
            id,
            name: `channel${id}`,
        });
    }
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: channelsData,
        },
    });
    await this.start();
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item`)
            .length,
        20,
        "should have 20 channel items");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_sidebar
                input.o_DiscussSidebar_quickSearch`)
            .length,
        1,
        "should have quick search in sidebar");

    const quickSearch = document.querySelector(`
        .o_Discuss_sidebar
        input.o_DiscussSidebar_quickSearch`);
    quickSearch.value = "1";
    const kevt1 = new window.KeyboardEvent('input');
    quickSearch.dispatchEvent(kevt1);
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item`)
            .length,
        11,
        "should have filtered to 11 channel items");

    quickSearch.value = "12";
    const kevt2 = new window.KeyboardEvent('input');
    quickSearch.dispatchEvent(kevt2);
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item`)
            .length,
        1,
        "should have filtered to a single channel item");
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item`)
            .dataset
            .threadLocalId,
        'mail.channel_12',
        "should have filtered to a single channel item with Id 12");

    quickSearch.value = "123";
    const kevt3 = new window.KeyboardEvent('input');
    quickSearch.dispatchEvent(kevt3);
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_groupChannel
                .o_DiscussSidebar_item`)
            .length,
        0,
        "should have filtered to no channel item");
});

QUnit.test('basic control panel rendering', async function (assert) {
    assert.expect(8);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start();
    assert.strictEqual(
        document
            .querySelector(`
                .o_widget_Discuss
                > .o_cp_controller
                > .o_control_panel
                .breadcrumb`)
            .textContent,
        "Inbox",
        "display inbox in the breadcrumb");
    const markAllReadButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonMarkAllRead`);
    assert.isVisible(
        markAllReadButton,
        "should have visible button 'Mark all read' in the control panel of inbox");
    assert.ok(
        markAllReadButton.disabled,
        "should have disabled button 'Mark all read' in the control panel of inbox (no messages)");

    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]`));
    assert.strictEqual(
        document
            .querySelector(`
                .o_widget_Discuss
                > .o_cp_controller
                > .o_control_panel
                .breadcrumb`)
            .textContent,
        "Starred",
        "display starred in the breadcrumb");
    const unstarAllButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonUnstarAll`);
    assert.isVisible(
        unstarAllButton,
        "should have visible button 'Unstar all' in the control panel of starred");
    assert.ok(
        unstarAllButton.disabled,
        "should have disabled button 'Unstar all' in the control panel of starred (no messages)");

    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="mail.channel_20"]`));
    assert.strictEqual(
        document
            .querySelector(`
                .o_widget_Discuss
                > .o_cp_controller
                > .o_control_panel
                .breadcrumb`)
            .textContent,
        "#General",
        "display general in the breadcrumb");
    const inviteButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonInvite`);
    assert.isVisible(
        inviteButton,
        "should have visible button 'Invite' in the control panel of channel");
});

QUnit.test('inbox: mark all messages as read', async function (assert) {
    assert.expect(8);

    const self = this;
    Object.assign(this.data.initMessaging, {
        needaction_inbox_counter: 2,
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                message_needaction_counter: 2,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [{
                    author_id: [7, "Demo"],
                    body: `<p>message1</p>`,
                    channel_ids: [20],
                    date: "2019-04-20 10:00:00",
                    id: 100,
                    message_type: 'comment',
                    model: 'mail.channel',
                    needaction: true,
                    needaction_partner_ids: [3],
                    record_name: "General",
                    res_id: 20,
                }, {
                    author_id: [8, "Other"],
                    body: `<p>message2</p>`,
                    channel_ids: [20],
                    date: "2019-04-20 10:00:00",
                    id: 101,
                    message_type: 'comment',
                    model: 'mail.channel',
                    needaction: true,
                    needaction_partner_ids: [3],
                    record_name: "General",
                    res_id: 20,
                }];
            }
            if (args.method === 'mark_all_as_read') {
                // simulate mark as read notification
                const data = {
                    message_ids: [100, 101],
                    type: 'mark_as_read',
                };
                const notifications = [ [['my-db', 'res.partner'], data] ];
                self.widget.call('bus_service', 'trigger', 'notification', notifications);
                return;

            }
            return this._super(...arguments);
        },
        session: {
            partner_id: 3,
        },
    });
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`)
            .textContent,
        "2",
        "inbox should have counter of 2");
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_20"]
                .o_DiscussSidebarItem_counter`)
            .textContent,
        "2",
        "channel should have counter of 2");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "should have 2 messages in inbox");
    let markAllReadButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonMarkAllRead`);
    assert.notOk(
        markAllReadButton.disabled,
        "should have enabled button 'Mark all read' in the control panel of inbox (has messages)");

    markAllReadButton.click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`)
            .length,
        0,
        "inbox should display no counter (= 0)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.channel_20"]
                .o_DiscussSidebarItem_counter`)
            .length,
        0,
        "channel should display no counter (= 0)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        0,
        "should have no message in inbox");
    markAllReadButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonMarkAllRead`);
    assert.ok(
        markAllReadButton.disabled,
        "should have disabled button 'Mark all read' in the control panel of inbox (no messages)");
});

QUnit.test('starred: unstar all', async function (assert) {
    assert.expect(6);

    const self = this;
    Object.assign(this.data.initMessaging, { starred_counter: 2 });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [{
                    author_id: [7, "Demo"],
                    body: `<p>message1</p>`,
                    channel_ids: [20],
                    date: "2019-04-20 10:00:00",
                    id: 100,
                    message_type: 'comment',
                    model: 'mail.channel',
                    record_name: "General",
                    res_id: 20,
                    starred: true,
                    starred_partner_ids: [3],
                }, {
                    author_id: [8, "Other"],
                    body: `<p>message2</p>`,
                    channel_ids: [20],
                    date: "2019-04-20 10:00:00",
                    id: 101,
                    message_type: 'comment',
                    model: 'mail.channel',
                    record_name: "General",
                    res_id: 20,
                    starred: true,
                    starred_partner_ids: [3],
                }];
            }
            if (args.method === 'unstar_all') {
                // simulate toggle_star notification
                const data = {
                    message_ids: [100, 101],
                    starred: false,
                    type: 'toggle_star',
                };
                const notifications = [ [['my-db', 'res.partner'], data] ];
                self.widget.call('bus_service', 'trigger', 'notification', notifications);
                return;

            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.box_starred',
        },
        session: {
            partner_id: 3,
        },
    });
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_counter`)
            .textContent,
        "2",
        "starred should have counter of 2");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "should have 2 messages in starred");
    let unstarAllButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonUnstarAll`);
    assert.notOk(
        unstarAllButton.disabled,
        "should have enabled button 'Unstar all' in the control panel of starred (has messages)");

    unstarAllButton.click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_counter`)
            .length,
        0,
        "starred should display no counter (= 0)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        0,
        "should have no message in starred");
    unstarAllButton = document.querySelector(`.o_widget_Discuss_controlPanelButtonUnstarAll`);
    assert.ok(
        unstarAllButton.disabled,
        "should have disabled button 'Unstar all' in the control panel of starred (no messages)");
});

QUnit.test('toggle_star message', async function (assert) {
    assert.expect(16);

    const self = this;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    let messageData = {
        author_id: [11, "Demo"],
        body: "<p>body</p>",
        channel_ids: [20],
        date: "2019-04-20 10:00:00",
        id: 100,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'General',
        res_id: 20,
        starred: false,
        starred_partner_ids: [],
    };

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [messageData];
            }
            if (args.method === 'toggle_message_starred') {
                assert.step('rpc:toggle_message_starred');
                assert.strictEqual(
                    args.args[0][0],
                    100,
                    "should have message Id in args");
                // simulate toggle_star notification
                messageData.starred = !messageData.starred;
                const data = {
                    message_ids: [100],
                    starred: messageData.starred,
                    type: 'toggle_star',
                };
                const notifications = [ [['my-db', 'res.partner'], data] ];
                self.widget.call('bus_service', 'trigger', 'notification', notifications);
                return;
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_counter`)
            .length,
        0,
        "starred should display no counter (= 0)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        1,
        "should have 1 message in channel");
    let message = document.querySelector(`
        .o_Discuss
        .o_Thread_messageList
        .o_MessageList_message`);
    assert.notOk(
        message
            .classList
            .contains('o-starred'),
        "message should not be starred");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_commandStar`)
            .length,
        1,
        "message should have star command");

    message
        .querySelector(`
            :scope
            .o_Message_commandStar`)
        .click();
    await testUtils.nextTick(); // re-render
    assert.verifySteps(['rpc:toggle_message_starred']);
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_counter`)
            .textContent,
        "1",
        "starred should display a counter of 1");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        1,
        "should have kept 1 message in channel");
    message = document.querySelector(`
        .o_Discuss
        .o_Thread_messageList
        .o_MessageList_message`);
    assert.ok(
        message
            .classList
            .contains('o-starred'),
        "message should be starred");

    message
        .querySelector(`
            :scope
            .o_Message_commandStar`)
        .click();
    await testUtils.nextTick(); // re-render
    assert.verifySteps(['rpc:toggle_message_starred']);
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_starred"]
                .o_DiscussSidebarItem_counter`)
            .length,
        0,
        "starred should no longer display a counter (= 0)");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        1,
        "should still have 1 message in channel");
    message = document.querySelector(`
        .o_Discuss
        .o_Thread_messageList
        .o_MessageList_message`);
    assert.notOk(
        message
            .classList
            .contains('o-starred'),
        "message should no longer be starred");
});

QUnit.test('composer state: text save and restore', async function (assert) {
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                name: "General",
            }, {
                channel_type: 'channel',
                id: 21,
                name: "Special",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [];
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    // Write text in composer for #general
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "XDU for the win");
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('input'));
    await testUtils.nextTick();
    document
        .querySelector(`.o_DiscussSidebarItem[data-thread-name="Special"]`)
        .click();
    await testUtils.nextTick(); // re-render
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "They see me rollin'");
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('input'));
    await testUtils.nextTick();
    // Switch back to #general
    document
        .querySelector(`.o_DiscussSidebarItem[data-thread-name="General"]`)
        .click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "XDU for the win",
        "should restore the input text");

    document
        .querySelector(`.o_DiscussSidebarItem[data-thread-name="Special"]`)
        .click();
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "They see me rollin'",
        "should restore the input text");
});

QUnit.test('composer state: attachments save and restore', async function (assert) {
    assert.expect(6);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                name: "General",
            }, {
                channel_type: 'channel',
                id: 21,
                name: "Special",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [];
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
    });
    const channels = document.querySelectorAll(`
        .o_DiscussSidebar
        > .o_DiscussSidebar_groupChannel
        > .o_DiscussSidebar_list
        > .o_DiscussSidebarItem
    `);
    // Add attachment in a message for #general
    await inputFiles(
        document.querySelector('.o_Composer_fileInput'),
        [
            await testUtils.file.createFile({
                content: 'hello, world',
                contentType: 'text/plain',
                name: 'text.txt',
            }),
        ]);
    // Switch to #special
    await testUtils.dom.click(channels[1]);
    // Add attachments in a message for #special
    await inputFiles(
        document.querySelector('.o_Composer_fileInput'),
        [
            await testUtils.file.createFile({
                content: 'hello2, world',
                contentType: 'text/plain',
                name: 'text2.txt',
            }),
            await testUtils.file.createFile({
                content: 'hello3, world',
                contentType: 'text/plain',
                name: 'text3.txt',
            }),
            await testUtils.file.createFile({
                content: 'hello4, world',
                contentType: 'text/plain',
                name: 'text4.txt',
            }),
        ]
    );
    // Switch back to #general
    await testUtils.dom.click(channels[0]);
    // Check attachment is reloaded
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)
            .length,
        1,
        "should have 1 attachment in the composer");
    assert.strictEqual(
        document
            .querySelector(`
                .o_Composer
                .o_Attachment`)
            .dataset
            .attachmentLocalId,
        'ir.attachment_1',
        "should have correct 1st attachment in the composer");

    // Switch back to #special
    await testUtils.dom.click(channels[1]);
    // Check attachments are reloaded
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)
            .length,
        3,
        "should have 3 attachments in the composer");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)[0]
            .dataset
            .attachmentLocalId,
        'ir.attachment_2',
        "should have ir.attachment_2 as 1st attachment");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)[1]
            .dataset
            .attachmentLocalId,
        'ir.attachment_3',
        "should have ir.attachment_3 as 2nd attachment");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Composer
                .o_Attachment`)[2]
            .dataset
            .attachmentLocalId,
        'ir.attachment_4',
        "should have ir.attachment_4 as 3rd attachment");
});

QUnit.test('post a simple message', async function (assert) {
    assert.expect(15);

    const self = this;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    let messagesData = [];
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return messagesData;
            }
            if (args.method === 'message_post') {
                assert.step('message_post');
                assert.strictEqual(
                    args.args[0],
                    20,
                    "should post message to channel Id 20");
                assert.strictEqual(
                    args.kwargs.body,
                    "Test<p></p>", // AKU: summernote adds extra <p> for some reasons
                    "should post with provided content in composer input");
                assert.strictEqual(
                    args.kwargs.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
                assert.strictEqual(
                    args.kwargs.subtype,
                    "mail.mt_comment",
                    "should set subtype as 'comment'"
                );
                // simulate receiving a new message
                const data = {
                    author_id: [3, "Admin"],
                    body: args.kwargs.body,
                    channel_ids: [20],
                    date: "2019-04-20 11:00:00",
                    id: 101,
                    message_type: args.kwargs.message_type,
                    model: 'mail.channel',
                    subtype: args.kwargs.subtype,
                    record_name: 'General',
                    res_id: 20,
                };
                const notifications = [
                    [['my-db', 'mail.channel', 20], data]
                ];
                messagesData.push(data);
                self.widget.call('bus_service', 'trigger', 'notification', notifications);
                return;
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
        session: {
            partner_id: 3,
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`.o_MessageList_empty`)
            .length,
        1,
        "should display thread with no message initially");
    assert.strictEqual(
        document
            .querySelectorAll(`.o_Message`)
            .length,
        0,
        "should display no message initially");
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "",
        "should have empty content initially");

    // insert some HTML in editable
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "Test");
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "Test",
        "should have inserted text in editable");

    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }));
    await testUtils.nextTick(); // re-render
    assert.verifySteps(['message_post']);
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "",
        "should have no content in composer input after posting message");
    assert.strictEqual(
        document
            .querySelectorAll(`.o_Message`)
            .length,
        1,
        "should display a message after posting message");
    const message = document.querySelector(`.o_Message`);
    assert.strictEqual(
        message.dataset.messageLocalId,
        'mail.message_101',
        "new message in thread should be linked to newly created message from message post");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_authorName`)
            .textContent,
        "Admin",
        "new message in thread should be from Admin");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_content`)
            .textContent,
        "Test",
        "new message in thread should have content typed from composer text input");
});

QUnit.test('input cleared only after message_post rpc is resolved', async function (assert) {
    assert.expect(7);

    const messagePostPromise = testUtils.makeTestPromise();
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_post') {
                assert.step('message_post:in-progress');
                await messagePostPromise;
                assert.step('message_post:done');
                return;
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
        session: {
            partner_id: 3,
        },
    });
    // Type message
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "test message");
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "test message",
        "should have inserted text content in editable");

    // Send message
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }));
    await testUtils.nextTick(); // re-render
    assert.verifySteps(['message_post:in-progress']);
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "test message",
        "should still have inserted HTML in editable when message_post is in progress");

    // Simulate server response
    messagePostPromise.resolve();
    await testUtils.nextTick();
    assert.verifySteps(['message_post:done']);
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "",
        "should have no content in composer input after posting message");
});

QUnit.test('input not cleared if message_post rpc is not resolved', async function (assert) {
    assert.expect(4);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_post') {
                assert.step('message_post');
                throw new Error();
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.channel_20',
        },
        session: {
            partner_id: 3,
        },
    });
    // Type message
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .focus();
    document.execCommand('insertText', false, "test message");
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "test message",
        "should have inserted text content in editable");

    // Send message
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }));
    await testUtils.nextTick(); // re-render
    assert.verifySteps(['message_post']);
    // Check input is not cleared as message_post is rejected
    assert.strictEqual(
        document
            .querySelector(`.o_ComposerTextInput_editable`)
            .textContent,
        "test message",
        "should still have content in composer input");
});

QUnit.test('rendering of inbox message', async function (assert) {
    assert.expect(7);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [{
                    author_id: [11, "Demo"],
                    body: "<p>body</p>",
                    date: "2019-04-20 10:00:00",
                    id: 100,
                    message_type: 'comment',
                    model: 'project.task',
                    needaction_partner_ids: [44],
                    record_name: 'Refactoring',
                    res_id: 20,
                }];
            }
            return this._super(...arguments);
        },
        session: {
            partner_id: 44,
        },
    });
    assert.strictEqual(
        document.querySelectorAll('.o_Message').length,
        1,
        "should display a message");
    const message = document.querySelector('.o_Message');
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_originThread`)
            .length,
        1,
        "should display origin thread of message");
    assert.strictEqual(
        message
            .querySelector(`
                :scope
                .o_Message_originThread`)
            .textContent,
        " on Refactoring",
        "should display origin thread name");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_command`)
            .length,
        3,
        "should display 3 commands");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_commandStar`)
            .length,
        1,
        "should display star command");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_commandReply`)
            .length,
        1,
        "should display reply command");
    assert.strictEqual(
        message
            .querySelectorAll(`
                :scope
                .o_Message_commandMarkAsRead`)
            .length,
        1,
        "should display mark as read command");
});

QUnit.test('mark channel as seen on last message visible', async function (assert) {
    assert.expect(3);

    let step = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 10,
                message_unread_counter: 1,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                step++;
                if (step === 1) {
                    return [];
                }
                if (step === 2) {
                    return [{
                        author_id: [11, "Demo"],
                        body: "<p>body</p>",
                        date: "2019-04-20 10:00:00",
                        id: 100,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: "General",
                        res_id: 10,
                    }];
                }
                throw new Error("should not call 'message_fetch' more than twice");
            }
            return this._super(...arguments);
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll(`.o_DiscussSidebar_item[data-thread-local-id="mail.channel_10"]`)
            .length,
        1,
        "should have discuss sidebar item with the channel");
    assert.ok(
        document
            .querySelector(`.o_DiscussSidebar_item[data-thread-local-id="mail.channel_10"]`)
            .classList
            .contains('o-unread'),
        "sidebar item of channel ID 10 should be unread");

    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="mail.channel_10"]`));
    assert.notOk(
        document
            .querySelector(`.o_DiscussSidebar_item[data-thread-local-id="mail.channel_10"]`)
            .classList
            .contains('o-unread'),
        "sidebar item of channel ID 10 should not longer be unread");
});

QUnit.test('receive new needaction messages', async function (assert) {
    assert.expect(12);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [];
            }
            return this._super(...arguments);
        },
        session: {
            partner_id: 3,
        },
    });
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]'),
        "should have inbox in sidebar");
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]')
            .classList
            .contains('o-active'),
        "inbox should be current discuss thread");
    assert.notOk(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`),
        "inbox item in sidebar should not have any counter");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Message`)
            .length,
        0,
        "should have no messages in inbox initially");

    // simulate receiving a new needaction message
    const data = {
        author_id: [7, "Demo"],
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        id: 100,
        message_type: 'comment',
        needaction_partner_ids: [3],
        model: 'project.task',
        record_name: 'Refactoring',
        res_id: 20,
    };
    const notifications = [
        [['my-db', 'ir.needaction', 3], data]
    ];
    this.widget.call('bus_service', 'trigger', 'notification', notifications);
    await testUtils.nextTick(); // re-render
    assert.ok(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`),
        "inbox item in sidebar should now have counter");
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`)
            .textContent,
        '1',
        "inbox item in sidebar should have counter of '1'");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Message`)
            .length,
        1,
        "should have one message in inbox");
    assert.strictEqual(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Message`)
            .dataset
            .messageLocalId,
        'mail.message_100',
        "should display newly received needaction message");

    // simulate receiving another new needaction message
    const data2 = {
        author_id: [7, "Demo"],
        body: "<p>Test2</p>",
        date: "2019-04-20 11:00:00",
        id: 101,
        message_type: 'comment',
        needaction_partner_ids: [3],
        model: 'project.task',
        record_name: 'Refactoring',
        res_id: 20,
    };
    const notifications2 = [
        [['my-db', 'ir.needaction', 3], data2]
    ];
    this.widget.call('bus_service', 'trigger', 'notification', notifications2);
    await testUtils.nextTick(); // re-render
    assert.strictEqual(
        document
            .querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]
                .o_DiscussSidebarItem_counter`)
            .textContent,
        '2',
        "inbox item in sidebar should have counter of '2'");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Message`)
            .length,
        2,
        "should have 2 messages in inbox");
    assert.ok(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Message[data-message-local-id="mail.message_100"]`),
        "should still display 1st needaction message");
    assert.ok(
        document
            .querySelector(`
                .o_Discuss_thread
                .o_Message[data-message-local-id="mail.message_101"]`),
        "should display 2nd needaction message");
});

QUnit.test('reply to message from inbox (message linked to document)', async function (assert) {
    assert.expect(20);

    Object.assign(this.data.initMessaging, {
        needaction_inbox_counter: 1,
    });

    let messagesData = [];
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                return [{
                    author_id: [7, "Demo"],
                    body: "<p>Test</p>",
                    date: "2019-04-20 11:00:00",
                    id: 100,
                    message_type: 'comment',
                    needaction_partner_ids: [3],
                    model: 'project.task',
                    record_name: 'Refactoring',
                    res_id: 20,
                }];
            }
            if (args.method === 'message_post') {
                assert.step('message_post');
                assert.strictEqual(
                    args.model,
                    'project.task',
                    "should post message to record with model 'project.task'");
                assert.strictEqual(
                    args.args[0],
                    20,
                    "should post message to record with Id 20");
                assert.strictEqual(
                    args.kwargs.body,
                    "Test<p></p>", // AKU: summernote adds extra <p> for some reasons
                    "should post with provided content in composer input");
                assert.strictEqual(
                    args.kwargs.message_type,
                    "comment",
                    "should set message type as 'comment'"
                );
                assert.strictEqual(
                    args.kwargs.subtype,
                    "mail.mt_comment",
                    "should set subtype as 'comment'"
                );
                messagesData.push({
                    author_id: [3, "Admin"],
                    body: args.kwargs.body,
                    date: "2019-04-20 11:00:00",
                    id: 101,
                    message_type: args.kwargs.message_type,
                    model: args.model,
                    subtype: args.kwargs.subtype,
                    record_name: 'Refactoring',
                    res_id: 20,
                });
                return;
            }
            if (args.method === 'message_format') {
                return messagesData;
            }
            return this._super(...arguments);
        },
        session: {
            partner_id: 3,
        },
    });
    assert.strictEqual(
        document
            .querySelectorAll('.o_Message')
            .length,
        1,
        "should display a single message");
    assert.strictEqual(
        document
            .querySelector('.o_Message')
            .dataset
            .messageLocalId,
        'mail.message_100',
        "should display message with ID 100");
    assert.strictEqual(
        document
            .querySelector('.o_Message_originThread')
            .textContent,
        " on Refactoring",
        "should display message originates from record 'Refactoring'");

    await testUtils.dom.click(
        document.querySelector('.o_Message_commandReply'));
    assert.ok(
        document
            .querySelector('.o_Message')
            .classList
            .contains('o-selected'),
        "message should be selected after clicking on reply icon");
    assert.ok(
        document.querySelector('.o_Composer'),
        "should have composer after clicking on reply to message");
    assert.strictEqual(
        document
            .querySelector(`.o_Composer_threadName`)
            .textContent,
        " on: Refactoring",
        "composer should display origin thread name of message");
    assert.strictEqual(
        document.activeElement,
        document.querySelector(`.o_ComposerTextInput_editable`),
        "composer text input should be auto-focus");

    document.execCommand('insertText', false, "Test");
    document
        .querySelector(`.o_ComposerTextInput_editable`)
        .dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }));
    assert.verifySteps(['message_post']);
    await testUtils.nextTick(); // re-render
    assert.notOk(
        document.querySelector('.o_Composer'),
        "should no longer have composer after posting reply to message");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Message')
            .length,
        1,
        "should still display a single message after posting reply");
    assert.strictEqual(
        document
            .querySelector('.o_Message')
            .dataset
            .messageLocalId,
        'mail.message_100',
        "should still display message with ID 100 after posting reply");
    assert.notOk(
        document
            .querySelector('.o_Message')
            .classList
            .contains('o-selected'),
        "message should not longer be selected after posting reply");
    assert.ok(
        document.querySelector('.o_notification'),
        "should display a notification after posting reply");
    assert.strictEqual(
        document
            .querySelector('.o_notification_title')
            .textContent,
        "Message posted on \"Refactoring\"",
        "notification should tell that message has been posted to the record 'Refactoring'");
});

QUnit.test('load recent messages from thread (already loaded some old messages)', async function (assert) {
    // Load old message that has been needaction, when opening this thread for
    // the first time, it should load messages that are more recent.
    assert.expect(17);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                name: "General",
            }],
        },
        needaction_inbox_counter: 1,
    });
    let step = 0;
    let mailMessages = {};
    for (let i = 0; i < 50; i++) {
        mailMessages[100 + i] = {
            author_id: [7, "Demo"],
            body: `<p>Test${i}</p>`,
            date: `2019-04-20 11:00:${i < 10 ? '0' + i : i}`,
            id: 100 + i,
            message_type: 'comment',
            needaction_partner_ids: i === 0 ? [3] : [],
            model: 'mail.channel',
            record_name: "General",
            res_id: 20,
        };
    }
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                step++;
                if (step === 1) {
                    assert.step('message_fetch:load_inbox');
                    assert.deepEqual(
                        args.args[0],
                        [['needaction', '=', true]],
                        "should fetch needaction messages from inbox");
                    const needactionMessages = Object
                        .values(mailMessages)
                        .filter(mailMessage =>
                            mailMessage.needaction_partner_ids.length > 0);
                    return needactionMessages;
                }
                if (step === 2) {
                    assert.step('message_fetch:load_channel_20');
                    assert.deepEqual(
                        args.args[0],
                        [['channel_ids', 'in', [20]]],
                        "should fetch messages from channel ID 20");
                    assert.strictEqual(
                        args.kwargs.limit,
                        30,
                        "should limit fetch to 30 messages (load)");
                    const moreRecentMessages = Object
                        .values(mailMessages)
                        .sort((mailMsg1, mailMsg2) => mailMsg1.id > mailMsg2.id ? -1 : 1)
                        .splice(0, 30);
                    return moreRecentMessages;
                }
                if (step === 3) {
                    assert.step('message_fetch:load_more_channel_20');
                    assert.deepEqual(
                        args.args[0],
                        // loaded 30 messages, so 150 - 30 = 120 = ID of last message fetched
                        // => load more messages starting from this ID
                        [['id', '<', 120], ['channel_ids', 'in', [20]]],
                        "should fetch more messages from 30 more recent messages");
                    assert.strictEqual(
                        args.kwargs.limit,
                        30,
                        "should limit fetch to 30 messages (load more)");
                    const loadMoreMessages = Object
                        .values(mailMessages)
                        .filter(mailMessage => mailMessage.id < 120)
                        .sort((mailMsg1, mailMsg2) => mailMsg1.id > mailMsg2.id ? -1 : 1)
                        .splice(0, 30);
                    return loadMoreMessages;
                }
                throw new Error("should not fetch more than twice");
            }
            return this._super(...arguments);
        },
        session: {
            partner_id: 3,
        },
    });
    assert.verifySteps(
        ['message_fetch:load_inbox'],
        "should initially have fetched messages from inbox");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Message')
            .length,
        1,
        "should fetch a single message from inbox");
    assert.strictEqual(
        document
            .querySelector('.o_Message')
            .dataset
            .messageLocalId,
        'mail.message_100',
        "should have fetched 1st message of channel 'General' as needaction from inbox");

    await testUtils.dom.click(
        document.querySelector(`
            .o_DiscussSidebar_item[data-thread-local-id="mail.channel_20"]`));
    assert.verifySteps(
        ['message_fetch:load_channel_20'],
        "should initially have fetched messages from channel 'General' (channel 20)");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Message')
            .length,
        30,
        "should display 30 messages from channel 'General' (only fetched ones)");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Message[data-message-local-id="mail.message_100"]')
            .length,
        0,
        "should not display 1st message of 'General' as needaction from inbox");

    await scroll({
        scrollableElement: document.querySelector(`
            .o_Discuss_thread
            .o_Thread_messageList`),
        scrollTop: 0,
    });
    assert.verifySteps(
        ['message_fetch:load_more_channel_20'],
        "should have fetched more messages from channel 'General' (channel 20)");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Message')
            .length,
        50,
        "should display 50 messages from channel 'General' (all fetched)");
    assert.strictEqual(
        document
            .querySelectorAll('.o_Message[data-message-local-id="mail.message_100"]')
            .length,
        1,
        "should include 1st message of 'General' as needaction from inbox in the fetched more messages");
});

QUnit.test('messages marked as read move to "History" mailbox', async function (assert) {
    assert.expect(10);

    const self = this;
    this.data['mail.message'].records = [{
        author_id: [5, 'Demo User'],
        body: '<p>test 1</p>',
        id: 1,
        needaction: true,
        needaction_partner_ids: [3],
    }, {
        author_id: [6, 'Test User'],
        body: '<p>test 2</p>',
        id: 2,
        needaction: true,
        needaction_partner_ids: [3],
    }];
    this.data['mail.notification'].records = [{
        id: 50,
        is_read: false,
        mail_message_id: 1,
        res_partner_id: 3,
    }, {
        id: 51,
        is_read: false,
        mail_message_id: 1,
        res_partner_id: 3,
    }];
    this.data.initMessaging = {
        needaction_inbox_counter: 2,
    };
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'mark_all_as_read') {
                for (const message of this.data['mail.message'].records) {
                    message.history_partner_ids = [3];
                    message.needaction_partner_ids = [];
                }
                const notificationData = {
                    type: 'mark_as_read',
                    message_ids: [1, 2],
                };
                const notification = [[false, 'res.partner', 3], notificationData];
                self.widget.call('bus_service', 'trigger', 'notification', [notification]);
                return 3;
            }
            return this._super(...arguments);
        },
        params: {
            default_active_id: 'mail.box_history',
        },
        session: {
            partner_id: 3,
        },
    });
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_history"]')
            .classList
            .contains('o-active'),
        "History mailbox should be active thread");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .length,
        1,
        "should have empty thread in history");

    await testUtils.dom.click($('.o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]'));
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]')
            .classList
            .contains('o-active'),
        "Inbox mailbox should be active thread");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .length,
        0,
        "Inbox mailbox should not be empty");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "Inbox mailbox should have 2 messages");

    await testUtils.dom.click($('.o_widget_Discuss_controlPanelButtonMarkAllRead'));
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_inbox"]')
            .classList
            .contains('o-active'),
        "Inbox mailbox should still be active after mark as read");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .length,
        1,
        "Inbox mailbox should now be empty after mark as read");

    await testUtils.dom.click($('.o_DiscussSidebar_item[data-thread-local-id="mail.box_history"]'));
    assert.ok(
        document
            .querySelector('.o_DiscussSidebar_item[data-thread-local-id="mail.box_history"]')
            .classList
            .contains('o-active'),
        "History mailbox should be active");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_empty`)
            .length,
        0,
        "History mailbox should not be empty after mark as read");
    assert.strictEqual(
        document
            .querySelectorAll(`
                .o_Discuss_thread
                .o_Thread_messageList
                .o_MessageList_message`)
            .length,
        2,
        "History mailbox should have 2 messages");
});

QUnit.test('receive new channel message: out of odoo focus (notification, channel)', async function (assert) {
    assert.expect(7);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                message_unread_counter: 0,
                name: "General",
            }],
        },
    });
    const services = getMailServices();
    services.bus_service = services.bus_service.extend({
        isOdooFocused: () => false,
    });
    await this.start({
        intercepts: {
            /**
             * @param {OdooEvent} ev
             * @param {Object} ev.data
             * @param {string} ev.data.part
             * @param {string} ev.data.title
             */
            set_title_part(ev) {
                assert.step('set_title_part');
                assert.strictEqual(ev.data.part, '_chat');
                assert.strictEqual(ev.data.title, "1 Message");
            },
        },
        services,
    });

    // simulate receiving a new message with odoo focused
    const messageData = {
        author_id: [7, "Demo User"],
        body: "<p>Test</p>",
        channel_ids: [20],
        date: "2019-04-20 10:00:00",
        id: 126,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'General',
        res_id: 20,
    };
    const notifications = [ [['my-db', 'mail.channel', 20], messageData] ];
    this.widget.call('bus_service', 'trigger', 'notification', notifications);
    await testUtils.nextTick(); // re-render & store action fully handled
    assert.verifySteps(['set_title_part']);
    assert.strictEqual(
        document
            .querySelectorAll('.o_notification')
            .length,
        1,
        "should display notification when out of focus");
    assert.strictEqual(
        document
            .querySelector(`
                .o_notification
                .o_notification_title`)
            .textContent,
        "Demo User from General",
        "should display author name and origin channel name as notification title");
    assert.strictEqual(
        document
            .querySelector(`
                .o_notification
                .o_notification_content`)
            .textContent,
        "Test",
        "should display message body as notification content");
});

QUnit.test('receive new channel message: out of odoo focus (notification, chat)', async function (assert) {
    assert.expect(7);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_direct_message: [{
                channel_type: "chat",
                direct_partner: [{
                    id: 7,
                    name: "Demo User",
                }],
                id: 10,
                message_unread_counter: 0,
            }],
        },
    });
    const services = getMailServices();
    services.bus_service = services.bus_service.extend({
        isOdooFocused: () => false,
    });
    await this.start({
        intercepts: {
            /**
             * @param {OdooEvent} ev
             * @param {Object} ev.data
             * @param {string} ev.data.part
             * @param {string} ev.data.title
             */
            set_title_part(ev) {
                assert.step('set_title_part');
                assert.strictEqual(ev.data.part, '_chat');
                assert.strictEqual(ev.data.title, "1 Message");
            },
        },
        services,
    });

    // simulate receiving a new message with odoo focused
    const messageData = {
        author_id: [7, "Demo User"],
        body: "<p>Test</p>",
        channel_ids: [10],
        date: "2019-04-20 10:00:00",
        id: 126,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'General',
        res_id: 10,
    };
    const notifications = [ [['my-db', 'mail.channel', 10], messageData] ];
    this.widget.call('bus_service', 'trigger', 'notification', notifications);
    await testUtils.nextTick(); // re-render & store action fully handled
    assert.verifySteps(['set_title_part']);
    assert.strictEqual(
        document
            .querySelectorAll('.o_notification')
            .length,
        1,
        "should display notification when out of focus");
    assert.strictEqual(
        document
            .querySelector(`
                .o_notification
                .o_notification_title`)
            .textContent,
        "Demo User",
        "should display author name as notification title");
    assert.strictEqual(
        document
            .querySelector(`
                .o_notification
                .o_notification_content`)
            .textContent,
        "Test",
        "should display message body as notification content");
});

QUnit.test('receive new channel messages: out of odoo focus (tab title)', async function (assert) {
    assert.expect(12);

    let step = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                message_unread_counter: 0,
                name: "General",
            }],
            channel_direct_message: [{
                channel_type: "chat",
                direct_partner: [{
                    id: 7,
                    name: "Demo User",
                }],
                id: 10,
                message_unread_counter: 0,
            }],
        },
    });
    const services = getMailServices();
    services.bus_service = services.bus_service.extend({
        isOdooFocused: () => false,
    });
    await this.start({
        intercepts: {
            /**
             * @param {OdooEvent} ev
             * @param {Object} ev.data
             * @param {string} ev.data.part
             * @param {string} ev.data.title
             */
            set_title_part(ev) {
                step++;
                assert.step('set_title_part');
                assert.strictEqual(ev.data.part, '_chat');
                if (step === 1) {
                    assert.strictEqual(ev.data.title, "1 Message");
                }
                if (step === 2) {
                    assert.strictEqual(ev.data.title, "2 Messages");
                }
                if (step === 3) {
                    assert.strictEqual(ev.data.title, "3 Messages");
                }
            },
        },
        services,
    });

    // simulate receiving a new message in general with odoo focused
    const messageData1 = {
        author_id: [7, "Demo User"],
        body: "<p>Test1</p>",
        channel_ids: [20],
        date: "2019-04-20 10:00:00",
        id: 126,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'General',
        res_id: 20,
    };
    const notifications1 = [ [['my-db', 'mail.channel', 20], messageData1] ];
    this.widget.call('bus_service', 'trigger', 'notification', notifications1);
    await testUtils.nextTick(); // re-render & store action fully handled
    assert.verifySteps(['set_title_part']);

    // simulate receiving a new message in chat with odoo focused
    const messageData2 = {
        author_id: [7, "Demo User"],
        body: "<p>Test2</p>",
        channel_ids: [10],
        date: "2019-04-20 10:00:00",
        id: 127,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'General',
        res_id: 10,
    };
    const notifications2 = [ [['my-db', 'mail.channel', 10], messageData2] ];
    this.widget.call('bus_service', 'trigger', 'notification', notifications2);
    await testUtils.nextTick(); // re-render & store action fully handled
    assert.verifySteps(['set_title_part']);

    // simulate receiving another new message in chat with odoo focused
    const messageData3 = {
        author_id: [7, "Demo User"],
        body: "<p>Test3</p>",
        channel_ids: [10],
        date: "2019-04-20 10:00:00",
        id: 128,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'General',
        res_id: 10,
    };
    const notifications3 = [ [['my-db', 'mail.channel', 20], messageData3] ];
    this.widget.call('bus_service', 'trigger', 'notification', notifications3);
    await testUtils.nextTick(); // re-render & store action fully handled
    assert.verifySteps(['set_title_part']);
});

});
});
});
