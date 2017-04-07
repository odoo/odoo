odoo.define('web.util_tests', function (require) {
"use strict";

var utils = require('web.utils');

QUnit.module('core', {}, function () {

    QUnit.module('utils');


    QUnit.test('intersperse', function (assert) {
        assert.expect(27);

        var intersperse = utils.intersperse;

        assert.strictEqual(intersperse("", []), "");
        assert.strictEqual(intersperse("0", []), "0");
        assert.strictEqual(intersperse("012", []), "012");
        assert.strictEqual(intersperse("1", []), "1");
        assert.strictEqual(intersperse("12", []), "12");
        assert.strictEqual(intersperse("123", []), "123");
        assert.strictEqual(intersperse("1234", []), "1234");
        assert.strictEqual(intersperse("123456789", []), "123456789");
        assert.strictEqual(intersperse("&ab%#@1", []), "&ab%#@1");

        assert.strictEqual(intersperse("0", []), "0");
        assert.strictEqual(intersperse("0", [1]), "0");
        assert.strictEqual(intersperse("0", [2]), "0");
        assert.strictEqual(intersperse("0", [200]), "0");

        assert.strictEqual(intersperse("12345678", [0], '.'), '12345678');
        assert.strictEqual(intersperse("", [1], '.'), '');
        assert.strictEqual(intersperse("12345678", [1], '.'), '1234567.8');
        assert.strictEqual(intersperse("12345678", [1], '.'), '1234567.8');
        assert.strictEqual(intersperse("12345678", [2], '.'), '123456.78');
        assert.strictEqual(intersperse("12345678", [2, 1], '.'), '12345.6.78');
        assert.strictEqual(intersperse("12345678", [2, 0], '.'), '12.34.56.78');
        assert.strictEqual(intersperse("12345678", [-1, 2], '.'), '12345678');
        assert.strictEqual(intersperse("12345678", [2, -1], '.'), '123456.78');
        assert.strictEqual(intersperse("12345678", [2, 0, 1], '.'), '12.34.56.78');
        assert.strictEqual(intersperse("12345678", [2, 0, 0], '.'), '12.34.56.78');
        assert.strictEqual(intersperse("12345678", [2, 0, -1], '.'), '12.34.56.78');
        assert.strictEqual(intersperse("12345678", [3,3,3,3], '.'), '12.345.678');
        assert.strictEqual(intersperse("12345678", [3,0], '.'), '12.345.678');
    });

});

});