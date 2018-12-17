odoo.define('mail_bot.systray.MessagingMenuTests', function (require) {
"use strict";

var MessagingMenu = require('mail.systray.MessagingMenu');
var mailTestUtils = require('mail.testUtils');

var MailBotService = require('mail_bot.MailBotService');

var testUtils = require('web.test_utils');

QUnit.module('mail_bot', {}, function () {
QUnit.module('MessagingMenu', {
    beforeEach: function () {
        var self = this;

        this.data = {
            'mail.channel': {
                fields: {},
                records: [],
            },
            'mail.message': {
                fields: {},
                records: [],
            },
        };

        this.services = _.extend({}, mailTestUtils.getMailServices(), {
            mailbot_service: MailBotService
        });

        // By default, permission are to ask user for push notification ("default").
        // Use requestPermissionDef to simulate permission change, e.g. "granted"
        this.requestPermissionDef = $.Deferred();
        this.ORIGINAL_WINDOW_NOTIFICATION = window.Notification;
        window.Notification = {
            permission: "default",
            requestPermission: function () {
                return self.requestPermissionDef;
            },
        };

        // Patch mailbot_service so that it does do not do any RPC
        this.hasMailbotRequest = true;
        testUtils.patch(MailBotService, {
            /**
             * @override
             */
            _showOdoobotTimeout: function () {},
        });

        // Patch Bus Service so that it does not play any audio (may raise
        // Uncaught rejected Promise due to Chrome autoplay policy: https://goo.gl/xX8pDD)
        testUtils.patch(this.services.bus_service, {
            /**
             * @override
             */
            _beep: function () {},
        });
    },
    afterEach: function () {
        // unpatch MailBotService and BusService
        testUtils.unpatch(MailBotService);
        testUtils.unpatch(this.services.bus_service);
        window.Notification = this.ORIGINAL_WINDOW_NOTIFICATION;
    }
});

QUnit.test('messaging menu widget: rendering with OdooBot has a request', function (assert) {
    assert.expect(5);

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    assert.containsOnce(messagingMenu, '.o_notification_counter',
        "should display a notification counter next to the messaging menu");
    assert.strictEqual(messagingMenu.$('.o_notification_counter').text(), '1',
        "should display a counter of '1' next to the messaging menu");

    testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_preview_info',
        "should display a preview in the messaging menu");
    assert.strictEqual(messagingMenu.$('.o_preview_name').text().trim(),
        'OdooBot has a request',
        "preview should display that OdooBot has a request");
    assert.strictEqual(messagingMenu.$('.o_preview_counter').text().replace(/\s/g, ''),
        '(1)', "should display an counter of '1' next to the preview");

    messagingMenu.destroy();
});

QUnit.test('messaging menu widget: rendering without OdooBot has a request (denied)', function (assert) {
    assert.expect(3);

    window.Notification.permission = 'denied';

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    assert.containsOnce(messagingMenu, '.o_notification_counter',
        "should display a notification counter next to the messaging menu");
    assert.strictEqual(messagingMenu.$('.o_notification_counter').text(), '0',
        "should display a counter of '0' next to the messaging menu");
    testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsNone(messagingMenu, '.o_preview_info',
        "should display no preview in the messaging menu");

    messagingMenu.destroy();
});

QUnit.test('messaging menu widget: rendering without OdooBot has a request (accepted)', function (assert) {
    assert.expect(3);

    window.Notification.permission = 'granted';

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    assert.containsOnce(messagingMenu, '.o_notification_counter',
        "should display a notification counter next to the messaging menu");
    assert.strictEqual(messagingMenu.$('.o_notification_counter').text(), '0',
        "should display a counter of '0' next to the messaging menu");
    testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsNone(messagingMenu, '.o_preview_info',
        "should display no preview in the messaging menu");

    messagingMenu.destroy();
});

QUnit.test('messaging menu widget: respond to notification prompt', function (assert) {
    assert.expect(4);

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    assert.containsOnce(messagingMenu, '.o_notification_counter',
        "should display a notification counter next to the messaging menu");
    assert.strictEqual(messagingMenu.$('.o_notification_counter').text(), '1',
        "should display a counter of '1' next to the messaging menu");

    testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    testUtils.dom.click(messagingMenu.$('.o_preview_info'));

    // simulate "default" response, which is equivalent to "Not Now" in Firefox.
    this.requestPermissionDef.resolve("default");

    assert.strictEqual(messagingMenu.$('.o_notification_counter').text(), '0',
        "should display a counter of '0' next to the messaging menu");

    testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsNone(messagingMenu, '.o_preview_info',
        "should display no preview in the messaging menu");

    messagingMenu.destroy();
});


});
});
