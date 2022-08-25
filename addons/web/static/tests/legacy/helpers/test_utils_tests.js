odoo.define('web.testUtilsTests', function (require) {
"use strict";

var testUtils = require('web.test_utils');

QUnit.module('web', {}, function () {
QUnit.module('testUtils', {}, function () {

QUnit.module('patch date');

QUnit.test('new date', function (assert) {
    assert.expect(5);
    const unpatchDate = testUtils.mock.patchDate(2018, 9, 23, 14, 50, 0);

    const date = new Date();

    assert.strictEqual(date.getFullYear(), 2018);
    assert.strictEqual(date.getMonth(), 9);
    assert.strictEqual(date.getDate(), 23);
    assert.strictEqual(date.getHours(), 14);
    assert.strictEqual(date.getMinutes(), 50);
    unpatchDate();
});

QUnit.test('new moment', function (assert) {
    assert.expect(1);
    const unpatchDate = testUtils.mock.patchDate(2018, 9, 23, 14, 50, 0);

    const m = moment();
    assert.strictEqual(m.format('YYYY-MM-DD HH:mm'), '2018-10-23 14:50');
    unpatchDate();
});

});
});
});