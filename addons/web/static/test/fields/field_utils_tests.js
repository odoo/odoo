odoo.define('web.field_utils_tests', function (require) {
"use strict";

var core = require('web.core');
var fieldUtils = require('web.field_utils');
var time = require('web.time');

QUnit.module('fields', {}, function () {

QUnit.module('field_utils');

QUnit.test('format integer', function(assert) {
    assert.expect(5);

    var originalGrouping = core._t.database.parameters.grouping;

    core._t.database.parameters.grouping = [3, 3, 3, 3];
    assert.strictEqual(fieldUtils.format_integer(1000000), '1,000,000');

    core._t.database.parameters.grouping = [3, 2, -1];
    assert.strictEqual(fieldUtils.format_integer(106500), '1,06,500');

    core._t.database.parameters.grouping = [1, 2, -1];
    assert.strictEqual(fieldUtils.format_integer(106500), '106,50,0');

    assert.strictEqual(fieldUtils.format_integer(0), "0");
    assert.strictEqual(fieldUtils.format_integer(undefined), "");

    core._t.database.parameters.grouping = originalGrouping;
});

QUnit.test('format float', function(assert) {
    assert.expect(4);

    var originalParameters = $.extend(true, {}, core._t.database.parameters);

    core._t.database.parameters.grouping = [3, 3, 3, 3];
    assert.strictEqual(fieldUtils.format_float(1000000), '1,000,000.00');

    core._t.database.parameters.grouping = [3, 2, -1];
    assert.strictEqual(fieldUtils.format_float(106500), '1,06,500.00');

    core._t.database.parameters.grouping = [1, 2, -1];
    assert.strictEqual(fieldUtils.format_float(106500), '106,50,0.00');

    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: ',',
        thousands_sep: '.'
    });
    assert.strictEqual(fieldUtils.format_float(6000), '6.000,00');

    core._t.database.parameters = originalParameters;
});

QUnit.test("format_datetime", function (assert) {
    assert.expect(1);

    var date_string = "2009-05-04 12:34:23";
    var date = time.str_to_datetime(date_string);
    var str = fieldUtils.format_datetime(date_string);
    assert.strictEqual(str, moment(date).format("MM/DD/YYYY HH:mm:ss"));
});

QUnit.test("format_many2one", function (assert) {
    assert.expect(2);

    assert.strictEqual('', fieldUtils.format_many2one(null));
    assert.strictEqual('A M2O value', fieldUtils.format_many2one({
        data: { display_name: 'A M2O value' },
    }));
});


QUnit.test('formatting chars', function(assert) {
    assert.expect(1);

    assert.strictEqual(fieldUtils.format_char(), '',
        "undefined char should be formatted as an empty string");
});
});
});
