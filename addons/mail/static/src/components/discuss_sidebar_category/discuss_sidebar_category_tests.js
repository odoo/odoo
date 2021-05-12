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

    // Create a channel without needaction messages
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

    // Create 2 channels with needaction message,
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

    // Create a channel without needaction messages
    this.data['mail.channel'].records.push({ id: 20 });

    await this.start();

    // fold the channel category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is folded and without unread messages"
    );
});

QUnit.test('channel - counter: should have correct value of needaction threads if category is folded and with needaction messages', async function (assert) {
    assert.expect(1);

    // prepare 2 channels with needaction messages
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

    // fold the channel category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).textContent,
        "2",
        "should have correct value of needaction threads if category is folded and with needaction messages"
    );
});

QUnit.test('channel - command: should have view command when category is unfolded', async function (assert) {
    assert.expect(1);

    await this.start();
    // channel category is open by default
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandView`).length,
        1,
        "should have view command when channel category is open"
    );
});

QUnit.test('channel - command: should have view command when category is folded', async function (assert) {
    assert.expect(1);

    await this.start();
    // close channel category
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
    // channel category is open by default
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        1,
        "should have add command when channel category is open"
    );
});

QUnit.test('channel - command: should not have add command when category is folded', async function (assert) {
    assert.expect(1);

    await this.start();
    // close channel category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        0,
        "should not have add command when channel category is closed"
    );
});

QUnit.test('channel - states: open and close manually by clicking the title', async function (assert) {
    assert.expect(3);

    // create a channel thread
    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // fold the channel category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be closed and the content should be invisible"
    );

    // unfold the channel category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
});

QUnit.test('channel - states: open and close should call rpc', async function (assert) {
    assert.expect(8);

    // prepare a random channel to show channel category
    // create a channel thread
    this.data['mail.channel'].records.push({ id: 20 });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'set_mail_user_settings') {
                const mailUserSettingsId = this._getRecords('mail.user.settings',
                    [['user_id', '=', this.currentUserId]],
                )[0].id;
                assert.step('set_mail_user_settings');
                assert.deepEqual(
                    args.args[0],
                    [mailUserSettingsId],
                    "Correct mail user settings id should be sent to the server side"
                );
                assert.deepEqual(
                    args.kwargs.new_settings,
                    { is_discuss_sidebar_category_channel_open: args.kwargs.new_settings.is_discuss_sidebar_category_channel_open },
                    "Correct category states should be sent to the server side."
                );
            }
            return this._super(...arguments);
        },
    });

    // fold the channel category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.verifySteps(
        ['set_mail_user_settings'],
        "set_mail_user_settings should be called when folding the channel category"
    );

    // unfold the channel category
    // fold the channel category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });
    assert.verifySteps(
        ['set_mail_user_settings'],
        "set_mail_user_settings should be called when unfolding the channel category"
    );
});

QUnit.test('channel - states: open and close from the bus', async function (assert) {
    assert.expect(3);

    // create a channel thread
    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    await afterNextRender(() => {
        const notif = [
            ["dbName", "res.partner", this.env.messaging.currentPartner.id],
            {
                type: "mail_user_settings",
                payload: {
                    is_discuss_sidebar_category_channel_open: false,
                },
            },
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be closed and the content should be invisible"
    );

    await afterNextRender(() => {
        const notif = [
            ["dbName", "res.partner", this.env.messaging.currentPartner.id],
            {
                type: "mail_user_settings",
                payload: {
                    is_discuss_sidebar_category_channel_open: true,
                },
            },
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
});

QUnit.test('channel - states: the active category item should be visble even if the category is closed', async function (assert) {
    assert.expect(4);

    // prepare a random channel for channel category
    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // click the channel thread to activate it
    const channel = document.querySelector(`.o_DiscussSidebarCategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 20,
            model: 'mail.channel',
        }).localId
    }"]`);
    await afterNextRender(() => {
        channel.click();
    });
    assert.ok(channel.classList.contains('o-active'));

    // close the category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`).click();
    });

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        'the active channel item should remain even if the category is folded'
    );

    // activate another item so the channel thread is deactivated
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebarMailBox[data-thread-local-id="${
            this.env.messaging.inbox.localId
        }"]`).click();
    });

    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "inactive item should be invisible if the category is folded"
    );
});

QUnit.test('chat - counter: should not have a counter if the category is unfolded and without unread messages', async function (assert) {
    assert.expect(1);

    // Create a chat without unread messages
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

    // Create a chat with unread message,
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

    // Create a chat without unread messages
    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        message_unread_counter: 0,
        public: 'private',
    });

    await this.start();

    // fold the chat category
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

    // prepare 2 chats with unread messages
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

    // fold the chat category
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
    // chat category is open by default
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        1,
        "should have add command when chat category is open"
    );
});

QUnit.test('chat - command: should not have add command when category is folded', async function (assert) {
    assert.expect(1);

    await this.start();
    // close chat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        0,
        "should not have add command when chat category is closed"
    );
});

QUnit.test('chat - states: open and close manually by clicking the title', async function (assert) {
    assert.expect(3);

    // Create a chat
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
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // fold the chat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );

    // unfold the chat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be open and the content should be visible"
    );
});

QUnit.test('chat - states: open and close should call rpc', async function (assert) {
    assert.expect(8);

    // prepare a random chat to show chat category
    // create a chat thread
    this.data['mail.channel'].records.push({ id: 20 });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'set_mail_user_settings') {
                const mailUserSettingsId = this._getRecords('mail.user.settings',
                    [['user_id', '=', this.currentUserId]],
                )[0].id;
                assert.step('set_mail_user_settings');
                assert.deepEqual(
                    args.args[0],
                    [mailUserSettingsId],
                    "Correct mail user settings id should be sent to the server side"
                );
                assert.deepEqual(
                    args.kwargs.new_settings,
                    { is_discuss_sidebar_category_chat_open: args.kwargs.new_settings.is_discuss_sidebar_category_chat_open },
                    "Correct catergory states should be sent to the server side."
                );
            }
            return this._super(...arguments);
        },
    });

    // fold the chat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.verifySteps(
        ['set_mail_user_settings'],
        "set_mail_user_settings should be called when folding the chat category"
    );

    // unfold the chat category
    // fold the chat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });
    assert.verifySteps(
        ['set_mail_user_settings'],
        "set_mail_user_settings should be called when unfolding the chat category"
    );
});

QUnit.test('chat - states: open and close from the bus', async function (assert) {
    assert.expect(3);

    // create a chat thread
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
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    await afterNextRender(() => {
        const notif = [
            ["dbName", "res.partner", this.env.messaging.currentPartner.id],
            {
                type: "mail_user_settings",
                payload: {
                    is_discuss_sidebar_category_chat_open: false,
                },
            },
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );

    await afterNextRender(() => {
        const notif = [
            ["dbName", "res.partner", this.env.messaging.currentPartner.id],
            {
                type: "mail_user_settings",
                payload: {
                    is_discuss_sidebar_category_chat_open: true,
                },
            },
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be open and the content should be visible"
    );
});

QUnit.test('chat - states: the active category item should be visble even if the category is closed', async function (assert) {
    assert.expect(4);

    // Create a chat
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
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // click the chat thread to activate it
    const chat = document.querySelector(`.o_DiscussSidebarCategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 10,
            model: 'mail.channel',
        }).localId
    }"]`);
    await afterNextRender(() => {
        chat.click();
    });
    assert.ok(chat.classList.contains('o-active'));

    // close the category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`).click();
    });

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        'the active chat item should remain even if the category is folded'
    );

    // activate another item so the chat thread is deactivated
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebarMailBox[data-thread-local-id="${
            this.env.messaging.inbox.localId
        }"]`).click();
    });

    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
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
