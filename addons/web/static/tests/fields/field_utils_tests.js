odoo.define('web.field_utils_tests', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var fieldUtils = require('web.field_utils');

QUnit.module('fields', {}, function () {

QUnit.module('field_utils');

QUnit.test('format integer', function(assert) {
    assert.expect(5);

    var originalGrouping = core._t.database.parameters.grouping;

    core._t.database.parameters.grouping = [3, 3, 3, 3];
    assert.strictEqual(fieldUtils.format.integer(1000000), '1,000,000');

    core._t.database.parameters.grouping = [3, 2, -1];
    assert.strictEqual(fieldUtils.format.integer(106500), '1,06,500');

    core._t.database.parameters.grouping = [1, 2, -1];
    assert.strictEqual(fieldUtils.format.integer(106500), '106,50,0');

    assert.strictEqual(fieldUtils.format.integer(0), "0");
    assert.strictEqual(fieldUtils.format.integer(false), "");

    core._t.database.parameters.grouping = originalGrouping;
});

QUnit.test('format float', function(assert) {
    assert.expect(5);

    var originalParameters = $.extend(true, {}, core._t.database.parameters);

    core._t.database.parameters.grouping = [3, 3, 3, 3];
    assert.strictEqual(fieldUtils.format.float(1000000), '1,000,000.00');

    core._t.database.parameters.grouping = [3, 2, -1];
    assert.strictEqual(fieldUtils.format.float(106500), '1,06,500.00');

    core._t.database.parameters.grouping = [1, 2, -1];
    assert.strictEqual(fieldUtils.format.float(106500), '106,50,0.00');

    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: ',',
        thousands_sep: '.'
    });
    assert.strictEqual(fieldUtils.format.float(6000), '6.000,00');
    assert.strictEqual(fieldUtils.format.float(false), '');

    core._t.database.parameters = originalParameters;
});

QUnit.test("format_datetime", function (assert) {
    assert.expect(1);

    var date_string = "2009-05-04 12:34:23";
    var date = fieldUtils.parse.datetime(date_string, {}, {timezone: false});
    var str = fieldUtils.format.datetime(date, {}, {timezone: false});
    assert.strictEqual(str, moment(date).format("MM/DD/YYYY HH:mm:ss"));
});

QUnit.test("format_datetime (with different timezone offset)", function (assert) {
    assert.expect(2);

    // mock the date format to avoid issues due to localisation
    var dateFormat = core._t.database.parameters.date_format;
    core._t.database.parameters.date_format = '%m/%d/%Y';
    session.getTZOffset = function (date) {
        // simulate daylight saving time
        var startDate = new Date(2017, 2, 26);
        var endDate   = new Date(2017, 9, 29);
        if (startDate < date && date < endDate) {
            return 120; // UTC+2
        } else {
            return 60; // UTC+1
        }
    };

    var str = fieldUtils.format.datetime(moment.utc('2017-01-01T10:00:00Z'));
    assert.strictEqual(str, '01/01/2017 11:00:00');
    str = fieldUtils.format.datetime(moment.utc('2017-06-01T10:00:00Z'));
    assert.strictEqual(str, '06/01/2017 12:00:00');

    core._t.database.parameters.date_format = dateFormat;
});

QUnit.test("format_many2one", function (assert) {
    assert.expect(2);

    assert.strictEqual('', fieldUtils.format.many2one(null));
    assert.strictEqual('A M2O value', fieldUtils.format.many2one({
        data: { display_name: 'A M2O value' },
    }));
});

QUnit.test('format monetary', function(assert) {
    assert.expect(1);

    assert.strictEqual(fieldUtils.format.monetary(false), '');
});

QUnit.test('format char', function(assert) {
    assert.expect(1);

    assert.strictEqual(fieldUtils.format.char(), '',
        "undefined char should be formatted as an empty string");
});

QUnit.test('format many2many', function(assert) {
    assert.expect(3);

    assert.strictEqual(fieldUtils.format.many2many({data: []}), 'No records');
    assert.strictEqual(fieldUtils.format.many2many({data: [1]}), '1 record');
    assert.strictEqual(fieldUtils.format.many2many({data: [1, 2]}), '2 records');
});

QUnit.test('format one2many', function(assert) {
    assert.expect(3);

    assert.strictEqual(fieldUtils.format.one2many({data: []}), 'No records');
    assert.strictEqual(fieldUtils.format.one2many({data: [1]}), '1 record');
    assert.strictEqual(fieldUtils.format.one2many({data: [1, 2]}), '2 records');
});

QUnit.test('format binary', function (assert) {
    assert.expect(1);

    // base64 estimated size (bytes) = value.length / 1.37 (http://en.wikipedia.org/wiki/Base64#MIME)
    // Here: 4 / 1.37 = 2.91970800 => 2.92 (rounded 2 decimals by utils.human_size)
    assert.strictEqual(fieldUtils.format.binary('Cg=='), '2.92 Bytes');
});

QUnit.test('format percentage', function (assert) {
    assert.expect(9);

    assert.strictEqual(fieldUtils.format.percentage(0), '0%');
    assert.strictEqual(fieldUtils.format.percentage(0.5), '50%');
    assert.strictEqual(fieldUtils.format.percentage(1), '100%');

    assert.strictEqual(fieldUtils.format.percentage(-0.2), '-20%');
    assert.strictEqual(fieldUtils.format.percentage(2.5), '250%');

    assert.strictEqual(fieldUtils.format.percentage(0.125), '12.5%');
    assert.strictEqual(fieldUtils.format.percentage(0.666666), '66.67%');

    assert.strictEqual(fieldUtils.format.percentage(false), '0%');
    assert.strictEqual(fieldUtils.format.percentage(50, null,
        {humanReadable: function (val) {return true;}}), '5k%'
    );
});

QUnit.test('parse float', function(assert) {
    assert.expect(10);

    var originalParameters = _.clone(core._t.database.parameters);

    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: '.',
        thousands_sep: ','
    });

    assert.strictEqual(fieldUtils.parse.float(""), 0);
    assert.strictEqual(fieldUtils.parse.float("0"), 0);
    assert.strictEqual(fieldUtils.parse.float("100.00"), 100);
    assert.strictEqual(fieldUtils.parse.float("-100.00"), -100);
    assert.strictEqual(fieldUtils.parse.float("1,000.00"), 1000);
    assert.strictEqual(fieldUtils.parse.float("1,000,000.00"), 1000000);
    assert.strictEqual(fieldUtils.parse.float('1,234.567'), 1234.567);
    assert.throws(function () {
        fieldUtils.parse.float("1.000.000");
    }, "Throw an exception if it's not a valid number");

    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: ',',
        thousands_sep: '.'
    });

    assert.strictEqual(fieldUtils.parse.float('1.234,567'), 1234.567);
    assert.throws(function () {
        fieldUtils.parse.float("1,000,000");
    }, "Throw an exception if it's not a valid number");

    _.extend(core._t.database.parameters, originalParameters);
});

QUnit.test('parse integer', function(assert) {
    assert.expect(11);

    var originalParameters = _.clone(core._t.database.parameters);

    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: '.',
        thousands_sep: ','
    });

    assert.strictEqual(fieldUtils.parse.integer(""), 0);
    assert.strictEqual(fieldUtils.parse.integer("0"), 0);
    assert.strictEqual(fieldUtils.parse.integer("100"), 100);
    assert.strictEqual(fieldUtils.parse.integer("-100"), -100);
    assert.strictEqual(fieldUtils.parse.integer("1,000"), 1000);
    assert.strictEqual(fieldUtils.parse.integer("1,000,000"), 1000000);
    assert.throws(function () {
        fieldUtils.parse.integer("1.000.000");
    }, "Throw an exception if it's not a valid number");
    assert.throws(function () {
        fieldUtils.parse.integer("1,234.567");
    }, "Throw an exception if the number is a float");

    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: ',',
        thousands_sep: '.'
    });

    assert.strictEqual(fieldUtils.parse.integer("1.000.000"), 1000000);
    assert.throws(function () {
        fieldUtils.parse.integer("1,000,000");
    }, "Throw an exception if it's not a valid number");
    assert.throws(function () {
        fieldUtils.parse.integer("1.234,567");
    }, "Throw an exception if the number is a float");

    _.extend(core._t.database.parameters, originalParameters);
});

QUnit.test('parse monetary', function(assert) {
    assert.expect(11);
    var originalCurrencies = session.currencies;
    session.currencies = {
        1: {
            digits: [69, 2],
            position: "after",
            symbol: "€"
        },
        3: {
            digits: [69, 2],
            position: "before",
            symbol: "$"
        }
    };

    assert.strictEqual(fieldUtils.parse.monetary(""), 0);
    assert.strictEqual(fieldUtils.parse.monetary("0"), 0);
    assert.strictEqual(fieldUtils.parse.monetary("100.00"), 100);
    assert.strictEqual(fieldUtils.parse.monetary("-100.00"), -100);
    assert.strictEqual(fieldUtils.parse.monetary("1,000.00"), 1000);
    assert.strictEqual(fieldUtils.parse.monetary("1,000,000.00"), 1000000);
    assert.strictEqual(fieldUtils.parse.monetary("$&nbsp;125.00", {}, {currency_id: 3}), 125);
    assert.strictEqual(fieldUtils.parse.monetary("1,000.00&nbsp;€", {}, {currency_id: 1}), 1000);
    assert.throws(function() {fieldUtils.parse.monetary("$ 12.00", {}, {currency_id: 3})}, /is not a correct/);
    assert.throws(function() {fieldUtils.parse.monetary("$&nbsp;12.00", {}, {currency_id: 1})}, /is not a correct/);
    assert.throws(function() {fieldUtils.parse.monetary("$&nbsp;12.00&nbsp;34", {}, {currency_id: 3})}, /is not a correct/);

    session.currencies = originalCurrencies;
});

QUnit.test('parse percentage', function(assert) {
    assert.expect(7);

    assert.strictEqual(fieldUtils.parse.percentage(""), 0);
    assert.strictEqual(fieldUtils.parse.percentage("0"), 0);
    assert.strictEqual(fieldUtils.parse.percentage("0%"), 0);
    assert.strictEqual(fieldUtils.parse.percentage("0.02"), 0.02);
    assert.strictEqual(fieldUtils.parse.percentage("1"), 1);
    assert.strictEqual(fieldUtils.parse.percentage("2%"), 0.02);
    assert.strictEqual(fieldUtils.parse.percentage("100%"), 1);
})

});
});
