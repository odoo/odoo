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

        // Patch mailbot_service so that it does do not do any RPC, and
        // the detection of push notifications permissions can be simulated in
        // the test cases. By default, shows 'OdooBot has a request'
        this.hasMailbotRequest = true;
        testUtils.patch(MailBotService, {
            /**
             * @override
             */
            start: function () {},
            /**
             * @override
             * @returns {boolean}
             */
            hasRequest: function () {
                return self.hasMailbotRequest;
            },
        });

        this.services = _.extend({}, mailTestUtils.getMailServices(), {
            mailbot_service: MailBotService
        });
    },
    afterEach: function () {
        // unpatch MailBotService
        testUtils.unpatch(MailBotService);
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

    assert.strictEqual(messagingMenu.$('.o_notification_counter').length, 1,
        "should display a notification counter next to the messaging menu");
    assert.strictEqual(messagingMenu.$('.o_notification_counter').text(), '1',
        "should display a counter of '1' next to the messaging menu");

    messagingMenu.$('.dropdown-toggle').click();
    assert.strictEqual(messagingMenu.$('.o_preview_info').length, 1,
        "should display a preview in the messaging menu");
    assert.strictEqual(messagingMenu.$('.o_preview_name').text().trim(),
        'OdooBot has a request',
        "preview should display that OdooBot has a request");
    assert.strictEqual(messagingMenu.$('.o_preview_counter').text().replace(/\s/g, ''),
        '(1)', "should display an counter of '1' next to the preview");

    messagingMenu.destroy();
});

QUnit.test('messaging menu widget: rendering without OdooBot has a request', function (assert) {
    assert.expect(3);

    this.hasMailbotRequest = false;

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    assert.strictEqual(messagingMenu.$('.o_notification_counter').length, 1,
        "should display a notification counter next to the messaging menu");
    assert.strictEqual(messagingMenu.$('.o_notification_counter').text(), '0',
        "should display a counter of '0' next to the messaging menu");
    messagingMenu.$('.dropdown-toggle').click();
    assert.strictEqual(messagingMenu.$('.o_preview_info').length, 0,
        "should display no preview in the messaging menu");

    messagingMenu.destroy();
});


});
});
