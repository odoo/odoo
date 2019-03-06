odoo.define('im_support.systray_no_support_tests', function (require) {
"use strict";

/**
 * The purpose of these tests is to ensure that im_support doesn't have an impact
 * on the webclient when the support is not available.
 */

var mailTestUtils = require('mail.testUtils');
var MessagingMenu = require('mail.systray.MessagingMenu');

var testUtils = require('web.test_utils');

mailTestUtils.MockMailService.include({
    getServices: function () {
        return _.extend(this._super(), {
            support_bus_service: this.bus_service(),
        });
    },
});

QUnit.module('im_support', {}, function () {

QUnit.module('systray', {
    beforeEach: function () {
        this.data = {
            'mail.message': {
                fields: {},
            },
        };
        this.services = mailTestUtils.getMailServices();
    },
});

QUnit.test('messaging menu does not display the Support channel if not available', async function (assert) {
    // the Support channel should only be displayed if a support_token and a support_origin are
    // specified in the session, which is not the case for this test
    assert.expect(1);

    var messagingMenu = new MessagingMenu();
    testUtils.mock.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    await messagingMenu.appendTo($('#qunit-fixture'));

    testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsNone(messagingMenu, '.o_mail_systray_dropdown_bottom .o_mail_preview[data-preview-id=SupportChannel]', "should not display the Support channel");

    messagingMenu.destroy();
});

});

});
