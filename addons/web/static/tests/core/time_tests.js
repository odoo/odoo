odoo.define('web.time_tests', function (require) {
"use strict";

const core = require('web.core');
var time = require('web.time');

QUnit.module('core', {}, function () {

    QUnit.module('Time utils');

    QUnit.test('Parse server datetime', function (assert) {
        assert.expect(4);

        var date = time.str_to_datetime("2009-05-04 12:34:23");
        assert.deepEqual(
            [date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(),
                date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()],
            [2009, 5 - 1, 4, 12, 34, 23]);
        assert.deepEqual(
            [date.getFullYear(), date.getMonth(), date.getDate(),
                date.getHours(), date.getMinutes(), date.getSeconds()],
            [2009, 5 - 1, 4, 12 - (date.getTimezoneOffset() / 60), 34, 23]);

        var date2 = time.str_to_datetime('2011-12-10 00:00:00');
        assert.deepEqual(
            [date2.getUTCFullYear(), date2.getUTCMonth(), date2.getUTCDate(),
                date2.getUTCHours(), date2.getUTCMinutes(), date2.getUTCSeconds()],
            [2011, 12 - 1, 10, 0, 0, 0]);

        var date3 = time.str_to_datetime("2009-05-04 12:34:23.84565");
        assert.deepEqual(
            [date3.getUTCFullYear(), date3.getUTCMonth(), date3.getUTCDate(),
                date3.getUTCHours(), date3.getUTCMinutes(), date3.getUTCSeconds(), date3.getUTCMilliseconds()],
            [2009, 5 - 1, 4, 12, 34, 23, 845]);
    });

    QUnit.test('Parse server datetime on 31', function (assert) {
        assert.expect(1);

        var wDate = window.Date;

        try {
            window.Date = function (v) {
                if (_.isUndefined(v)) {
                    v = '2013-10-31 12:34:56';
                }
                return new wDate(v);
            };
            var date = time.str_to_datetime('2013-11-11 02:45:21');

            assert.deepEqual(
                    [date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(),
                        date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()],
                    [2013, 11 - 1, 11, 2, 45, 21]);
        }
        finally {
            window.Date = wDate;
        }
    });

    QUnit.test('Parse server date', function (assert) {
        assert.expect(1);

        var date = time.str_to_date("2009-05-04");
        assert.deepEqual(
            [date.getFullYear(), date.getMonth(), date.getDate()],
            [2009, 5 - 1, 4]);
    });

    QUnit.test('Parse server date on 31', function (assert) {
        assert.expect(1);

        var wDate = window.Date;

        try {
            window.Date = function (v) {
                if (_.isUndefined(v)) {
                    v = '2013-10-31 12:34:56';
                }
                return new wDate(v);
            };
            var date = time.str_to_date('2013-11-21');

            assert.deepEqual(
                [date.getFullYear(), date.getMonth(), date.getDate()],
                [2013, 11 - 1, 21]);
        }
        finally {
            window.Date = wDate;
        }
    });

    QUnit.test('Parse server time', function (assert) {
        assert.expect(2);

        var date = time.str_to_time("12:34:23");
        assert.deepEqual(
            [date.getHours(), date.getMinutes(), date.getSeconds()],
            [12, 34, 23]);

        date = time.str_to_time("12:34:23.5467");
        assert.deepEqual(
            [date.getHours(), date.getMinutes(), date.getSeconds(), date.getMilliseconds()],
            [12, 34, 23, 546]);
    });

    QUnit.test('Format server datetime', function (assert) {
        assert.expect(1);

        var date = new Date();
        date.setUTCFullYear(2009);
        date.setUTCMonth(5 - 1);
        date.setUTCDate(4);
        date.setUTCHours(12);
        date.setUTCMinutes(34);
        date.setUTCSeconds(23);
        assert.strictEqual(time.datetime_to_str(date), "2009-05-04 12:34:23");
    });

    QUnit.test('Format server date', function (assert) {
        assert.expect(1);

        var date = new Date();
        date.setUTCFullYear(2009);
        date.setUTCMonth(5 - 1);
        date.setUTCDate(4);
        date.setUTCHours(0);
        date.setUTCMinutes(0);
        date.setUTCSeconds(0);
        assert.strictEqual(time.date_to_str(date), "2009-05-04");
    });

    QUnit.test('Format server time', function (assert) {
        assert.expect(1);

        var date = new Date();
        date.setUTCFullYear(1970);
        date.setUTCMonth(1 - 1);
        date.setUTCDate(1);
        date.setUTCHours(0);
        date.setUTCMinutes(0);
        date.setUTCSeconds(0);
        date.setHours(12);
        date.setMinutes(34);
        date.setSeconds(23);
        assert.strictEqual(time.time_to_str(date), "12:34:23");
    });

    QUnit.test("Get lang datetime format", (assert) => {
        assert.expect(4);
        const originalParameters = Object.assign({}, core._t.database.parameters);
        Object.assign(core._t.database.parameters, {
            date_format: '%m/%d/%Y',
            time_format: '%H:%M:%S',
        });
        assert.strictEqual(time.getLangDateFormat(), "MM/DD/YYYY");
        assert.strictEqual(time.getLangDateFormatWoZero(), "M/D/YYYY");
        assert.strictEqual(time.getLangTimeFormat(), "HH:mm:ss");
        assert.strictEqual(time.getLangTimeFormatWoZero(), "H:m:s");
        Object.assign(core._t.database.parameters, originalParameters);
    });

});

});