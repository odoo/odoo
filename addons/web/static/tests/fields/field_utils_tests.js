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
    assert.expect(11);

    var originalParameters = _.clone(core._t.database.parameters);

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

    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: ',',
        thousands_sep: '.'
    });
    assert.strictEqual(fieldUtils.format.percentage(0.125), '12,5%');
    assert.strictEqual(fieldUtils.format.percentage(0.666666), '66,67%');

    core._t.database.parameters = originalParameters;
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
    assert.expect(15);
    var originalCurrencies = session.currencies;
    const originalParameters = _.clone(core._t.database.parameters);
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

    // In some languages, the non-breaking space character is used as thousands separator.
    const nbsp = '\u00a0';
    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: '.',
        thousands_sep: nbsp,
    });
    assert.strictEqual(fieldUtils.parse.monetary(`1${nbsp}000.00${nbsp}€`, {}, {currency_id: 1}), 1000);
    assert.strictEqual(fieldUtils.parse.monetary(`$${nbsp}1${nbsp}000.00`, {}, {currency_id: 3}), 1000);
    assert.strictEqual(fieldUtils.parse.monetary(`1${nbsp}000.00`), 1000);
    assert.strictEqual(fieldUtils.parse.monetary(`1${nbsp}000${nbsp}000.00`), 1000000);

    session.currencies = originalCurrencies;
    core._t.database.parameters = originalParameters;
});

QUnit.test('parse percentage', function(assert) {
    assert.expect(9);

    var originalParameters = _.clone(core._t.database.parameters);

    assert.strictEqual(fieldUtils.parse.percentage(""), 0);
    assert.strictEqual(fieldUtils.parse.percentage("0"), 0);
    assert.strictEqual(fieldUtils.parse.percentage("0%"), 0);
    assert.strictEqual(fieldUtils.parse.percentage("0.02"), 0.02);
    assert.strictEqual(fieldUtils.parse.percentage("1"), 1);
    assert.strictEqual(fieldUtils.parse.percentage("2%"), 0.02);
    assert.strictEqual(fieldUtils.parse.percentage("100%"), 1);

    _.extend(core._t.database.parameters, {
        grouping: [3, 0],
        decimal_point: ',',
        thousands_sep: '.'
    });

    assert.strictEqual(fieldUtils.parse.percentage("0,04"), 0.04);
    assert.strictEqual(fieldUtils.parse.percentage("6,02%"), 0.0602);

    core._t.database.parameters = originalParameters;

});

QUnit.test('parse datetime', function (assert) {
    assert.expect(5);

    var originalParameters = _.clone(core._t.database.parameters);
    var originalLocale = moment.locale();
    var dateStr, date1, date2;

    moment.defineLocale('englishForTest', {
        dayOfMonthOrdinalParse: /\d{1,2}(st|nd|rd|th)/,
        ordinal: function (number) {
            var b = number % 10,
                output = (~~(number % 100 / 10) === 1) ? 'th' :
                (b === 1) ? 'st' :
                (b === 2) ? 'nd' :
                (b === 3) ? 'rd' : 'th';
            return number + output;
        },
    });

    moment.defineLocale('norvegianForTest', {
        monthsShort: 'jan._feb._mars_april_mai_juni_juli_aug._sep._okt._nov._des.'.split('_'),
        monthsParseExact: true,
        dayOfMonthOrdinalParse: /\d{1,2}\./,
        ordinal: '%d.',
    });

    moment.locale('englishForTest');
    _.extend(core._t.database.parameters, {date_format: '%m/%d/%Y', time_format: '%H:%M:%S'});
    assert.throws(function () {fieldUtils.parse.datetime("13/01/2019 12:00:00", {}, {})}, /is not a correct/, "Wrongly formated dates should be invalids");
    assert.throws(function () {fieldUtils.parse.datetime("1899-01-01 12:00:00", {}, {})}, /is not a correct/, "Dates before 1900 should be invalids");

    dateStr = '01/13/2019 10:05:45';
    date1 = fieldUtils.parse.datetime(dateStr);
    date2 = moment.utc(dateStr, ['MM/DD/YYYY HH:mm:ss'], true);
    assert.equal(date1.format(), date2.format(), "Date with leading 0");

    dateStr = '1/14/2019 10:5:45';
    date1 = fieldUtils.parse.datetime(dateStr);
    date2 = moment.utc(dateStr, ['M/D/YYYY H:m:s'], true);
    assert.equal(date1.format(), date2.format(), "Date without leading 0");

    moment.locale('norvegianForTest');
    _.extend(core._t.database.parameters, {date_format: '%d. %b %Y', time_format: '%H:%M:%S'});
    dateStr = '16. jan. 2019 10:05:45';
    date1 = fieldUtils.parse.datetime(dateStr);
    date2 = moment.utc(dateStr, ['DD. MMM YYYY HH:mm:ss'], true);
    assert.equal(date1.format(), date2.format(), "Day/month inverted + month i18n");

    moment.locale(originalLocale);
    moment.updateLocale("englishForTest", null);
    moment.updateLocale("norvegianForTest", null);
    core._t.database.parameters = originalParameters;
});

QUnit.test('parse date without separator', function (assert) {
    assert.expect(8);

    var originalParameters = _.clone(core._t.database.parameters);

    _.extend(core._t.database.parameters, {date_format: '%d.%m/%Y'});
    var dateFormat = "DD.MM/YYYY";

    assert.throws(function () {fieldUtils.parse.date("1197")}, /is not a correct/, "Wrongly formated dates should be invalid");
    assert.throws(function () {fieldUtils.parse.date("0131")}, /is not a correct/, "Wrongly formated dates should be invalid");
    assert.throws(function () {fieldUtils.parse.date("970131")}, /is not a correct/, "Wrongly formated dates should be invalid");
    assert.equal(fieldUtils.parse.date("3101").format(dateFormat), "31.01/" + moment.utc().year());
    assert.equal(fieldUtils.parse.date("31.01").format(dateFormat), "31.01/" + moment.utc().year());
    assert.equal(fieldUtils.parse.date("310197").format(dateFormat), "31.01/1997");
    assert.equal(fieldUtils.parse.date("310117").format(dateFormat), "31.01/2017");
    assert.equal(fieldUtils.parse.date("31011985").format(dateFormat), "31.01/1985");

    core._t.database.parameters = originalParameters;
});

QUnit.test('parse datetime without separator', function (assert) {
    assert.expect(3);

    var originalParameters = _.clone(core._t.database.parameters);

    _.extend(core._t.database.parameters, {date_format: '%d.%m/%Y', time_format: '%H:%M/%S'});
    var dateTimeFormat = "DD.MM/YYYY HH:mm/ss";

    assert.equal(fieldUtils.parse.datetime("3101198508").format(dateTimeFormat), "31.01/1985 08:00/00");
    assert.equal(fieldUtils.parse.datetime("310119850833").format(dateTimeFormat), "31.01/1985 08:33/00");
    assert.equal(fieldUtils.parse.datetime("31/01/1985 08").format(dateTimeFormat), "31.01/1985 08:00/00");

    core._t.database.parameters = originalParameters;
});
});
});
