odoo.define('im_support.systray_tests', function (require) {
"use strict";

var imSupportTestUtils = require('im_support.test_utils');

var mailTestUtils = require('mail.testUtils');
var MessagingMenu = require('mail.systray.MessagingMenu');

var testUtils = require('web.test_utils');

var addMockSupportEnvironment = imSupportTestUtils.addMockSupportEnvironment;

QUnit.module('im_support', {}, function () {

QUnit.module('systray', {
    beforeEach: function () {
        this.data = {
            'mail.message': {
                fields: {},
            },
        };
        this.services = mailTestUtils.getMailServices();

        this.supportParams = {
            db_uuid: 'some_uuid',
            support_token: 'ABCDEFGHIJ',
            support_origin: 'something.com',
        };
    },
});

QUnit.test('messaging menu displays the Support channel', async function (assert) {
    assert.expect(1);

    var messagingMenu = new MessagingMenu();
    addMockSupportEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
        session: this.supportParams,
    });
    await testUtils.nextTick();
    await messagingMenu.appendTo($('#qunit-fixture'));

    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_systray_dropdown_bottom .o_mail_preview[data-preview-id=SupportChannel]', "should display the Support channel");

    messagingMenu.destroy();
});

QUnit.test('clicking on Support channel: channel not available', async function (assert) {
    assert.expect(9);

    var messagingMenu = new MessagingMenu();
    addMockSupportEnvironment(messagingMenu, {
        data: this.data,
        mockRPC: function (route, args) {
            if (!_.string.endsWith(route, '.png')) { // ignore images
                assert.step(args.method || route);
            }
            return this._super.apply(this, arguments);
        },
        mockSupportRPC: function (route) {
            assert.step('cors: ' + route);
            if (route === '/odoo_im_support/get_support_channel') {
                return this._super.apply(this, arguments).then(function (supportChannel) {
                    supportChannel.available = false;
                    return supportChannel;
                });
            }
            return this._super.apply(this, arguments);
        },
        services: this.services,
        session: this.supportParams,
    });
    await testUtils.nextTick();
    await messagingMenu.appendTo($('#qunit-fixture'));

    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_systray_dropdown_bottom .o_mail_preview[data-preview-id=SupportChannel]');

    await testUtils.dom.click(messagingMenu.$('.o_mail_preview[data-preview-id=SupportChannel]'));
    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open a chat window");
    assert.strictEqual($('.o_thread_window .o_thread_window_title').text().trim(), 'Support (offline)',
        "should display the offline status in the header");
    assert.strictEqual($('.o_thread_window .o_composer_input').length, 0,
        "should have no composer");

    assert.verifySteps([
        '/mail/init_messaging',
        'message_fetch',
        'cors: /odoo_im_support/get_support_channel',
        'cors: /odoo_im_support/fetch_messages',
    ]);

    messagingMenu.destroy();
});

QUnit.test('clicking on Support channel: channel available', async function (assert) {
    assert.expect(9);

    var messagingMenu = new MessagingMenu();
    addMockSupportEnvironment(messagingMenu, {
        data: this.data,
        mockRPC: function (route, args) {
            if (!_.string.endsWith(route, '.png')) { // ignore images
                assert.step(args.method || route);
            }
            return this._super.apply(this, arguments);
        },
        mockSupportRPC: function (route) {
            if (route.split('/')[1] === 'odoo_im_support') {
                assert.step('cors: ' + route);
            }
            return this._super.apply(this, arguments);
        },
        services: this.services,
        session: this.supportParams,
    });
    await testUtils.nextTick();
    await messagingMenu.appendTo($('#qunit-fixture'));

    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_systray_dropdown_bottom .o_mail_preview[data-preview-id=SupportChannel]');

    await testUtils.dom.click(messagingMenu.$('.o_mail_preview[data-preview-id=SupportChannel]'));
    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open a chat window");
    assert.strictEqual($('.o_thread_window .o_thread_window_title').text().trim(), 'Support',
        "should display the correct thread title");
    assert.strictEqual($('.o_thread_window .o_composer_input').length, 1,
        "should have a composer");

    assert.verifySteps([
        '/mail/init_messaging',
        'message_fetch',
        'cors: /odoo_im_support/get_support_channel',
        'cors: /odoo_im_support/fetch_messages',
    ]);

    messagingMenu.destroy();
});

QUnit.test('post messages in Support channel', async function (assert) {
    assert.expect(8);

    var messagingMenu = new MessagingMenu();
    addMockSupportEnvironment(messagingMenu, {
        data: this.data,
        mockRPC: function (route, args) {
            if (!_.string.endsWith(route, '.png')) { // ignore images
                assert.step(args.method || route);
            }
            return this._super.apply(this, arguments);
        },
        mockSupportRPC: function (route) {
            if (route.split('/')[1] === 'odoo_im_support') {
                assert.step('cors: ' + route);
            }
            return this._super.apply(this, arguments);
        },
        services: this.services,
        session: this.supportParams,
    });
    await testUtils.nextTick();
    await messagingMenu.appendTo($('#qunit-fixture'));

    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_systray_dropdown_bottom .o_mail_preview[data-preview-id=SupportChannel]');

    await testUtils.dom.click(messagingMenu.$('.o_mail_preview[data-preview-id=SupportChannel]'));
    assert.strictEqual($('.o_thread_window .o_composer_input').length, 1,
        "should have a composer");

    await testUtils.fields.editInput($('.o_thread_window .o_composer_input .o_input'), 'some message');
    await testUtils.fields.triggerKeydown($('.o_thread_window .o_composer_input .o_input'), 'enter');

    assert.verifySteps([
        '/mail/init_messaging',
        'message_fetch',
        'cors: /odoo_im_support/get_support_channel',
        'cors: /odoo_im_support/fetch_messages',
        'cors: /odoo_im_support/chat_post',
    ]);

    messagingMenu.destroy();
});

QUnit.test('fold Support channel', async function (assert) {
    assert.expect(11);

    var messagingMenu = new MessagingMenu();
    addMockSupportEnvironment(messagingMenu, {
        data: this.data,
        mockRPC: function (route, args) {
            if (!_.string.endsWith(route, '.png')) { // ignore images
                assert.step(args.method || route);
            }
            return this._super.apply(this, arguments);
        },
        mockSupportRPC: function (route) {
            if (route.split('/')[1] === 'odoo_im_support') {
                assert.step('cors: ' + route);
            }
            return this._super.apply(this, arguments);
        },
        services: this.services,
        session: this.supportParams,
    });
    await testUtils.nextTick();
    testUtils.mock.intercept(messagingMenu, 'call_service', function (ev) {
        if (ev.data.service === 'local_storage') {
            assert.step('LocalStorage: ' + ev.data.method + ' ' + ev.data.args);
        }
    }, true);
    await messagingMenu.appendTo($('#qunit-fixture'));

    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_systray_dropdown_bottom .o_mail_preview[data-preview-id=SupportChannel]');

    await testUtils.dom.click(messagingMenu.$('.o_mail_preview[data-preview-id=SupportChannel]'));
    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open a chat window");

    // fold, re-open and close channel
    await testUtils.dom.click($('.o_thread_window .o_thread_window_title'));
    await testUtils.dom.click($('.o_thread_window .o_thread_window_title'));
    testUtils.dom.click($('.o_thread_window .o_thread_window_close'));

    assert.verifySteps([
        '/mail/init_messaging',
        'message_fetch',
        'cors: /odoo_im_support/get_support_channel',
        'LocalStorage: setItem im_support.channel_state,open',
        'cors: /odoo_im_support/fetch_messages',
        'LocalStorage: setItem im_support.channel_state,folded',
        'LocalStorage: setItem im_support.channel_state,open',
        'LocalStorage: setItem im_support.channel_state,closed',
    ]);

    messagingMenu.destroy();
});

QUnit.test('restore Support channel if necessary', async function (assert) {
    assert.expect(5);

    var messagingMenu = new MessagingMenu();
    addMockSupportEnvironment(messagingMenu, {
        data: this.data,
        enableSupportPoll: true,
        mockRPC: function (route, args) {
            if (!_.string.endsWith(route, '.png')) { // ignore images
                assert.step(args.method || route);
            }
            return this._super.apply(this, arguments);
        },
        mockSupportRPC: function (route) {
            if (route.split('/')[1] === 'odoo_im_support') {
                assert.step('cors: ' + route);
            }
            return this._super.apply(this, arguments);
        },
        services: this.services,
        session: this.supportParams,
    });
    await testUtils.nextTick();
    await messagingMenu.appendTo($('#qunit-fixture'));

    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open a chat window");

    assert.verifySteps([
        'cors: /odoo_im_support/get_support_channel',
        '/mail/init_messaging',
        'cors: /odoo_im_support/fetch_messages',
    ]);

    messagingMenu.destroy();
});

QUnit.test('receive messages in the Support channel', async function (assert) {
    assert.expect(10);

    var supportChannelID;

    var messagingMenu = new MessagingMenu();
    addMockSupportEnvironment(messagingMenu, {
        data: this.data,
        enableSupportPoll: true,
        mockRPC: function (route, args) {
            if (!_.string.endsWith(route, '.png')) { // ignore images
                assert.step(args.method || route);
            }
            return this._super.apply(this, arguments);
        },
        mockSupportRPC: function (route) {
            if (route.split('/')[1] === 'odoo_im_support') {
                assert.step('cors: ' + route);
            }
            return this._super.apply(this, arguments);
        },
        services: this.services,
        session: this.supportParams,
    });
    await testUtils.nextTick();
    await messagingMenu.appendTo($('#qunit-fixture'));

    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open a chat window");
    assert.strictEqual($('.o_thread_window .o_thread_message').length, 0,
        "there should be no message in the thread");

    // simulate an incoming message on the supportBus
    var data = {
        author_id: [42, 'An operator'],
        body: 'A message',
        channel_ids: [supportChannelID],
    };
    var notification = [[false, 'mail.channel', 1], data];
    messagingMenu.call('support_bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();

    assert.strictEqual($('.o_thread_window .o_thread_message').length, 1,
        "there should be a new message in the thread");
    assert.strictEqual($('.o_thread_window .o_thread_message .o_thread_author ').text().trim(),
        'An operator', "should correctly display the author");
    assert.hasAttrValue($('.o_thread_window .o_thread_message .o_thread_message_avatar'), 'data-src',
        '/mail/static/src/img/odoo_o.png', "should have correct avatar");
    assert.strictEqual($('.o_thread_window .o_thread_message .o_thread_message_content ').text().trim(),
        'A message', "message is correct");

    assert.verifySteps([
        'cors: /odoo_im_support/get_support_channel',
        '/mail/init_messaging',
        'cors: /odoo_im_support/fetch_messages',
    ]);

    messagingMenu.destroy();
});

});

});
