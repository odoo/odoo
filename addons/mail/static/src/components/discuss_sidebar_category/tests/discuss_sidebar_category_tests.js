/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_sidebar_category', {}, function () {
QUnit.module('discuss_sidebar_category_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('channel - counter: should not have a counter if the category is unfolded and without needaction messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });

    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and without unread messages"
    );
});

QUnit.test('channel - counter: should not have a counter if the category is unfolded and with needaction messagens', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push(
        { id: 20 },
        { id: 30 },
    );
    this.data['mail.message'].records.push({
        body: "message 1",
        id: 100,
        model: "mail.channel",
        res_id: 20,
    }, {
        body: "message_2",
        id: 200,
        model: "mail.channel",
        res_id: 30,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 100,
        res_partner_id: this.data.currentPartnerId,
    }, {
        mail_message_id: 200,
        res_partner_id: this.data.currentPartnerId,
    });
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and with needaction messages",
    );
});

QUnit.test('channel - counter: should not have a counter if category is folded and without needaction messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });

    await this.start();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is folded and without unread messages"
    );
});

QUnit.test('channel - counter: should have correct value of needaction threads if category is folded and with needaction messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push(
        { id: 20 },
        { id: 30 },
    );
    this.data['mail.message'].records.push({
        body: "message 1",
        id: 100,
        model: "mail.channel",
        res_id: 20,
    }, {
        body: "message_2",
        id: 200,
        model: "mail.channel",
        res_id: 30,
    });
    this.data['mail.notification'].records.push({
        mail_message_id: 100,
        res_partner_id: this.data.currentPartnerId,
    }, {
        mail_message_id: 200,
        res_partner_id: this.data.currentPartnerId,
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await this.start();

    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).textContent,
        "2",
        "should have correct value of needaction threads if category is folded and with needaction messages"
    );
});

QUnit.test('channel - command: should have view command when category is unfolded', async function (assert) {
    assert.expect(1);

    await this.start();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandView`).length,
        1,
        "should have view command when channel category is open"
    );
});

QUnit.test('channel - command: should have view command when category is folded', async function (assert) {
    assert.expect(1);

    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await this.start();

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandView`).length,
        1,
        "should have view command when channel category is closed"
    );
});

QUnit.test('channel - command: should have add command when category is unfolded', async function (assert) {
    assert.expect(1);

    await this.start();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        1,
        "should have add command when channel category is open"
    );
});

QUnit.test('channel - command: should not have add command when category is folded', async function (assert) {
    assert.expect(1);

    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await this.start();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        0,
        "should not have add command when channel category is closed"
    );
});

QUnit.test('channel - states: close manually by clicking the title', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    await this.start();

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be closed and the content should be invisible"
    );
});

QUnit.test('channel - states: open manually by clicking the title', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await this.start();

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
});

QUnit.test('channel - states: close should update the value on the server', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    const currentUserId = this.data.currentUserId;
    await this.start();

    const initalSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_channel_open,
        true,
        "the vaule in server side should be true"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    const newSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_channel_open,
        false,
        "the vaule in server side should be false"
    );
});

QUnit.test('channel - states: open should update the value on the server', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const currentUserId = this.data.currentUserId;
    await this.start();

    const initalSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_channel_open,
        false,
        "the vaule in server side should be false"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    const newSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_channel_open,
        true,
        "the vaule in server side should be false"
    );
});

QUnit.test('channel - states: close from the bus', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    await this.start();

    await afterNextRender(() => {
        this.env.services.bus_service.trigger('notification', [{
            type: "res.users.settings/changed",
            payload: {
                is_discuss_sidebar_category_channel_open: false,
            },
        }]);
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be closed and the content should be invisible"
    );
});

QUnit.test('channel - states: open from the bus', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    await this.start();

    await afterNextRender(() => {
        this.env.services.bus_service.trigger('notification', [{
            type: "res.users.settings/changed",
            payload: {
                is_discuss_sidebar_category_channel_open: true,
            },
            }]);
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
});

QUnit.test('channel - states: the active category item should be visble even if the category is closed', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    const channel = document.querySelector(`.o_DiscussSidebarCategoryItem[data-thread-local-id="${
        this.messaging.models['mail.thread'].findFromIdentifyingData({
            id: 20,
            model: 'mail.channel',
        }).localId
    }"]`);
    await afterNextRender(() => {
        channel.click();
    });
    assert.ok(channel.classList.contains('o-active'));

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        'the active channel item should remain even if the category is folded'
    );

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebarMailbox[data-thread-local-id="${
            this.messaging.inbox.localId
        }"]`).click();
    });

    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "inactive item should be invisible if the category is folded"
    );
});

QUnit.test('chat - counter: should not have a counter if the category is unfolded and without unread messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 0,
        public: 'private',
    });

    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and without unread messages",
    );
});

QUnit.test('chat - counter: should not have a counter if the category is unfolded and with unread messagens', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 10,
        public: 'private',
    });
    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and with unread messages",
    );
});

QUnit.test('chat - counter: should not have a counter if category is folded and without unread messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 0,
        public: 'private',
    });

    await this.start();

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is folded and without unread messages"
    );
});

QUnit.test('chat - counter: should have correct value of unread threads if category is folded and with unread messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 10,
        public: 'private',
    }, {
        channel_type: 'chat',
        id: 20,
        message_unread_counter: 20,
        public: 'private',
    });
    await this.start();

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_counter`).textContent,
        "2",
        "should have correct value of unread threads if category is folded and with unread messages"
    );
});

QUnit.test('chat - command: should have add command when category is unfolded', async function (assert) {
    assert.expect(1);

    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        1,
        "should have add command when chat category is open"
    );
});

QUnit.test('chat - command: should not have add command when category is folded', async function (assert) {
    assert.expect(1);

    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    await this.start();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        0,
        "should not have add command when chat category is closed"
    );
});

QUnit.test('chat - states: close manually by clicking the title', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 0,
        public: 'private',
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    await this.start();

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );
});

QUnit.test('chat - states: open manually by clicking the title', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 0,
        public: 'private',
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    await this.start();

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );
});

QUnit.test('chat - states: close should call update server data', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    const currentUserId = this.data.currentUserId;
    await this.start();

    const initalSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_chat_open,
        true,
        "the value in server side should be true"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    const newSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_chat_open,
        false,
        "the value in server side should be false"
    );
});

QUnit.test('chat - states: open should call update server data', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const currentUserId = this.data.currentUserId;
    await this.start();

    const initalSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_chat_open,
        false,
        "the value in server side should be false"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    const newSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_chat_open,
        true,
        "the value in server side should be true"
    );
});

QUnit.test('chat - states: close from the bus', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 0,
        public: 'private',
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    await this.start();

    await afterNextRender(() => {
        this.env.services.bus_service.trigger('notification', [{
            type: "res.users.settings/changed",
            payload: {
                is_discuss_sidebar_category_chat_open: false,
            },
        }]);
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be open and the content should be visible"
    );
});

QUnit.test('chat - states: open from the bus', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 0,
        public: 'private',
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    await this.start();

    await afterNextRender(() => {
        this.env.services.bus_service.trigger('notification', [{
            type: "res.users.settings/changed",
            payload: {
                is_discuss_sidebar_category_chat_open: true,
            },
        }]);
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );
});

QUnit.test('chat - states: the active category item should be visble even if the category is closed', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 0,
        public: 'private',
    });
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    const chat = document.querySelector(`.o_DiscussSidebarCategoryItem[data-thread-local-id="${
        this.messaging.models['mail.thread'].findFromIdentifyingData({
            id: 10,
            model: 'mail.channel',
        }).localId
    }"]`);
    await afterNextRender(() => {
        chat.click();
    });
    assert.ok(chat.classList.contains('o-active'));

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        'the active chat item should remain even if the category is folded'
    );

    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebarMailbox[data-thread-local-id="${
            this.messaging.inbox.localId
        }"]`).click();
    });

    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "inactive item should be invisible if the category is folded"
    );
});

});
});
});
