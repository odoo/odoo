odoo.define('mail.mailServiceTests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('Service', {
    beforeEach: function () {
        this.services = mailTestUtils.getMailServices(this);
    },
});

QUnit.test('should only have a single mail service', function (assert) {
    assert.expect(2);

    // simulate having another service that is also a mail service
    this.services.mail_service2 = this.services.mail_service;

    let hasCrashed = false;
    try {
        testUtils
            .createParent({ services: this.services })
            .destroy();
    } catch (error) {
        assert.strictEqual(
            error.message,
            "Mail manager already started. This may be caused by having multiple service providers.",
            "should crash from having several mail manager started at the same time");
        hasCrashed = true;
    }

    assert.ok(hasCrashed, "should crash when two mail services exist at the same time");
});

});
});
