odoo.define('im_support.systray_no_support_tests', function (require) {
"use strict";

/**
 * The purpose of these tests is to ensure that im_support doesn't have an impact
 * on the webclient when the support is not available.
 */

var ChatManager = require('mail.ChatManager');
var systray = require('mail.systray');
var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

var createBusService = mailTestUtils.createBusService;

QUnit.module('im_support', {}, function () {

QUnit.module('systray', {
    beforeEach: function () {
        this.services = [ChatManager, createBusService()];
    },
});

QUnit.test('messaging menu does not display the Support channel if not available', function (assert) {
    // the Support channel should only be displayed if a support_token and a support_origin are
    // specified in the session, which is not the case for this test
    assert.expect(1);

    var messagingMenu = new systray.MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    messagingMenu.$('.dropdown-toggle').click();
    assert.strictEqual(messagingMenu.$('.o_mail_channel_preview[data-channel_id=SupportChannel]').length,
        0, "should not display the Support channel");

    messagingMenu.destroy();
});

});

});
