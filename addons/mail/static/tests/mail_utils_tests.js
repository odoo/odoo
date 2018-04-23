odoo.define('mail.mail_utils_tests', function (require) {
"use strict";

var utils = require('mail.utils');

QUnit.module('mail', {}, function () {

QUnit.module('Mail utils');

QUnit.test('add_link utility function', function (assert) {
    assert.expect(15);

    var testInputs = {
        'http://admin:password@example.com:8/%2020': true,
        'https://admin:password@example.com/test': true,
        'www.example.com:8/test': true,
        'https://127.0.0.5:8069': true,
        'www.127.0.0.5': false,
        'should.notmatch': false,
        'fhttps://test.example.com/test': false,
        "https://www.transifex.com/odoo/odoo-11/translate/#fr/lunch?q=text%3A'La+Tartiflette'": true,
        'https://www.transifex.com/odoo/odoo-11/translate/#fr/$/119303430?q=text%3ATartiflette': true,
    };

    _.each(testInputs, function (willLinkify, content) {
        var output = utils.parse_and_transform(content, utils.add_link);
        if (willLinkify) {
            assert.strictEqual(output.indexOf('<a '), 0, "There should be a link");
            assert.strictEqual(output.indexOf('</a>'), (output.length - 4), "Link should match the whole text");
        } else {
            assert.strictEqual(output.indexOf('<a '), -1, "There should be no link");
        }
    });
});

});
});
