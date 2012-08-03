$(document).ready(function () {
    var openerp;

    module('server-formats', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.web.core(openerp);
            window.openerp.web.dates(openerp);
        }
    });
    test('Parse server datetime', function () {
        var date = openerp.web.str_to_datetime("2009-05-04 12:34:23");
        deepEqual(
            [date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(),
             date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()],
            [2009, 5 - 1, 4, 12, 34, 23]);
        deepEqual(
            [date.getFullYear(), date.getMonth(), date.getDate(),
             date.getHours(), date.getMinutes(), date.getSeconds()],
            [2009, 5 - 1, 4, 12 - (date.getTimezoneOffset() / 60), 34, 23]);

        var date2 = openerp.web.str_to_datetime('2011-12-10 00:00:00');
        deepEqual(
            [date2.getUTCFullYear(), date2.getUTCMonth(), date2.getUTCDate(),
             date2.getUTCHours(), date2.getUTCMinutes(), date2.getUTCSeconds()],
            [2011, 12 - 1, 10, 0, 0, 0]);
    });
    test('Server datetime: CET -> EST', function () {
        // NOTE: this test may only work in the EU (CET/EST), no idea how to handle *that*
        // DST transition is at 01:00 UTC on a specific day
        // http://en.wikipedia.org/wiki/European_Summer_Time

        // right before transition
        strictEqual(
            openerp.web.str_to_datetime('2012-03-25 00:59:46').toString(),
            new Date(Date.UTC(2012, 2, 25, 0, 59, 46)).toString());
        // Right after transition
        strictEqual(
            openerp.web.str_to_datetime('2012-03-25 01:01:33').toString(),
            new Date(Date.UTC(2012, 2, 25, 1, 1, 33)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-03-25 01:24:33').toString(),
            new Date(Date.UTC(2012, 2, 25, 1, 24, 33)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-03-25 01:42:33').toString(),
            new Date(Date.UTC(2012, 2, 25, 1, 42, 33)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-03-25 02:05:14').toString(),
            new Date(Date.UTC(2012, 2, 25, 2, 5, 14)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-03-25 02:42:14').toString(),
            new Date(Date.UTC(2012, 2, 25, 2, 42, 14)).toString());
        // End of overlapping time
        strictEqual(
            openerp.web.str_to_datetime('2012-03-25 03:05:14').toString(),
            new Date(Date.UTC(2012, 2, 25, 3, 5, 14)).toString());
    });
    test('Server datetime: EST -> CET', function () {
        strictEqual(
            openerp.web.str_to_datetime('2012-10-27 23:59:46').toString(),
            new Date(Date.UTC(2012, 9, 27, 23, 59, 46)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-10-28 00:59:46').toString(),
            new Date(Date.UTC(2012, 9, 28, 0, 59, 46)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-10-28 01:01:33').toString(),
            new Date(Date.UTC(2012, 9, 28, 1, 1, 33)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-10-28 01:24:33').toString(),
            new Date(Date.UTC(2012, 9, 28, 1, 24, 33)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-10-28 01:42:33').toString(),
            new Date(Date.UTC(2012, 9, 28, 1, 42, 33)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-10-28 02:05:14').toString(),
            new Date(Date.UTC(2012, 9, 28, 2, 5, 14)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-10-28 02:42:14').toString(),
            new Date(Date.UTC(2012, 9, 28, 2, 42, 14)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-10-28 03:05:14').toString(),
            new Date(Date.UTC(2012, 9, 28, 3, 5, 14)).toString());
        strictEqual(
            openerp.web.str_to_datetime('2012-10-28 05:05:14').toString(),
            new Date(Date.UTC(2012, 9, 28, 5, 5, 14)).toString());
    });
    test('Parse server date', function () {
        var date = openerp.web.str_to_date("2009-05-04");
        deepEqual(
            [date.getFullYear(), date.getMonth(), date.getDate()],
            [2009, 5 - 1, 4]);
    });
    test('Parse server time', function () {
        var date = openerp.web.str_to_time("12:34:23");
        deepEqual(
            [date.getHours(), date.getMinutes(), date.getSeconds()],
            [12, 34, 23]);
    });

    module('web-formats', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.web.core(openerp);
            window.openerp.web.dates(openerp);
            window.openerp.web.formats(openerp);
        }
    });
    test("format_datetime", function () {
        var date = openerp.web.str_to_datetime("2009-05-04 12:34:23");
        var str = openerp.web.format_value(date, {type:"datetime"});
        equal(str, date.toString("MM/dd/yyyy HH:mm:ss"));
    });
    test("format_date", function () {
        var date = openerp.web.str_to_datetime("2009-05-04 12:34:23");
        var str = openerp.web.format_value(date, {type:"date"});
        equal(str, date.toString("MM/dd/yyyy"));
    });
    test("format_time", function () {
        var date = openerp.web.str_to_datetime("2009-05-04 12:34:23");
        var str = openerp.web.format_value(date, {type:"time"});
        equal(str, date.toString("HH:mm:ss"));
    });
    test("format_float_time", function () {
        strictEqual(
            openerp.web.format_value(1.0, {type:'float', widget:'float_time'}),
            '01:00');
        strictEqual(
            openerp.web.format_value(0.9853, {type:'float', widget:'float_time'}),
            '00:59');
        strictEqual(
            openerp.web.format_value(0.0085, {type:'float', widget:'float_time'}),
            '00:01');
        strictEqual(
            openerp.web.format_value(-1.0, {type:'float', widget:'float_time'}),
            '-01:00');
        strictEqual(
            openerp.web.format_value(-0.9853, {type:'float', widget:'float_time'}),
            '-00:59');
        strictEqual(
            openerp.web.format_value(-0.0085, {type:'float', widget:'float_time'}),
            '-00:01');
    });
    test("format_float", function () {
        var fl = 12.1234;
        var str = openerp.web.format_value(fl, {type:"float"});
        equal(str, "12.12");
        equal(openerp.web.format_value(12.02, {type: 'float'}),
              '12.02');
        equal(openerp.web.format_value(0.0002, {type: 'float', digits: [1, 3]}),
              '0.000');
        equal(openerp.web.format_value(0.0002, {type: 'float', digits: [1, 4]}),
              '0.0002');
        equal(openerp.web.format_value(0.0002, {type: 'float', digits: [1, 6]}),
              '0.000200');
        equal(openerp.web.format_value(1, {type: 'float', digits: [1, 6]}),
              '1.000000');
        equal(openerp.web.format_value(1, {type: 'float'}),
              '1.00');
        equal(openerp.web.format_value(-11.25, {type: 'float'}),
              "-11.25");
        openerp.web._t.database.parameters.grouping = [1, 2, -1];
        equal(openerp.web.format_value(1111111.25, {type: 'float'}),
              "1111,11,1.25");
        openerp.web._t.database.parameters.grouping = [1, 0];
        equal(openerp.web.format_value(-11.25, {type: 'float'}),
              "-1,1.25");
    });
//    test("parse_datetime", function () {
//        var val = openerp.web.str_to_datetime("2009-05-04 12:34:23");
//        var res = openerp.web.parse_value(val.toString("MM/dd/yyyy HH:mm:ss"), {type:"datetime"});
//        equal(val.toString("MM/dd/yyyy HH:mm:ss"), res.toString("MM/dd/yyyy HH:mm:ss"));
//    });
//    test("parse_date", function () {
//        var val = openerp.web.str_to_date("2009-05-04");
//        var res = openerp.web.parse_value(val.toString("MM/dd/yyyy"), {type:"date"});
//        equal(val.toString("MM/dd/yyyy"), res.toString("MM/dd/yyyy"));
//    });
//    test("parse_time", function () {
//        var val = openerp.web.str_to_time("12:34:23");
//        var res = openerp.web.parse_value(val.toString("HH:mm:ss"), {type:"time"});
//        equal(val.toString("HH:mm:ss"), res.toString("HH:mm:ss"));
//    });
    test('parse_integer', function () {
        var val = openerp.web.parse_value('123,456', {type: 'integer'});
        equal(val, 123456);
        openerp.web._t.database.parameters.thousands_sep = '|';
        var val2 = openerp.web.parse_value('123|456', {type: 'integer'});
        equal(val2, 123456);
    });
    test("parse_float", function () {
        var str = "134,112.1234";
        var val = openerp.web.parse_value(str, {type:"float"});
        equal(val, 134112.1234);
        var str = "-134,112.1234";
        var val = openerp.web.parse_value(str, {type:"float"});
        equal(val, -134112.1234);
        _.extend(openerp.web._t.database.parameters, {
            decimal_point: ',',
            thousands_sep: '.'
        });
        var val3 = openerp.web.parse_value('123.456,789', {type: 'float'});
        equal(val3, 123456.789);
    });
    test('intersperse', function () {
        var g = openerp.web.intersperse;
        equal(g("", []), "");
        equal(g("0", []), "0");
        equal(g("012", []), "012");
        equal(g("1", []), "1");
        equal(g("12", []), "12");
        equal(g("123", []), "123");
        equal(g("1234", []), "1234");
        equal(g("123456789", []), "123456789");
        equal(g("&ab%#@1", []), "&ab%#@1");

        equal(g("0", []), "0");
        equal(g("0", [1]), "0");
        equal(g("0", [2]), "0");
        equal(g("0", [200]), "0");

        equal(g("12345678", [0], '.'), '12345678');
        equal(g("", [1], '.'), '');
        equal(g("12345678", [1], '.'), '1234567.8');
        equal(g("12345678", [1], '.'), '1234567.8');
        equal(g("12345678", [2], '.'), '123456.78');
        equal(g("12345678", [2, 1], '.'), '12345.6.78');
        equal(g("12345678", [2, 0], '.'), '12.34.56.78');
        equal(g("12345678", [-1, 2], '.'), '12345678');
        equal(g("12345678", [2, -1], '.'), '123456.78');
        equal(g("12345678", [2, 0, 1], '.'), '12.34.56.78');
        equal(g("12345678", [2, 0, 0], '.'), '12.34.56.78');
        equal(g("12345678", [2, 0, -1], '.'), '12.34.56.78');
        equal(g("12345678", [3,3,3,3], '.'), '12.345.678');
        equal(g("12345678", [3,0], '.'), '12.345.678');
    });
    test('format_integer', function () {
        openerp.web._t.database.parameters.grouping = [3, 3, 3, 3];
        equal(openerp.web.format_value(1000000, {type: 'integer'}),
              '1,000,000');
        openerp.web._t.database.parameters.grouping = [3, 2, -1];
        equal(openerp.web.format_value(106500, {type: 'integer'}),
              '1,06,500');
        openerp.web._t.database.parameters.grouping = [1, 2, -1];
        equal(openerp.web.format_value(106500, {type: 'integer'}),
              '106,50,0');
    });
    test('format_float', function () {
        openerp.web._t.database.parameters.grouping = [3, 3, 3, 3];
        equal(openerp.web.format_value(1000000, {type: 'float'}),
              '1,000,000.00');
        openerp.web._t.database.parameters.grouping = [3, 2, -1];
        equal(openerp.web.format_value(106500, {type: 'float'}),
              '1,06,500.00');
        openerp.web._t.database.parameters.grouping = [1, 2, -1];
        equal(openerp.web.format_value(106500, {type: 'float'}),
              '106,50,0.00');

        _.extend(openerp.web._t.database.parameters, {
            grouping: [3, 0],
            decimal_point: ',',
            thousands_sep: '.'
        });
        equal(openerp.web.format_value(6000, {type: 'float'}),
              '6.000,00');
    });
    module('custom-date-formats', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.web.core(openerp);
            window.openerp.web.dates(openerp);
            window.openerp.web.formats(openerp);
        }
    });
    test('format stripper', function () {
        strictEqual(openerp.web.strip_raw_chars('%a, %Y %b %d'), '%a, %Y %b %d');
        strictEqual(openerp.web.strip_raw_chars('%a, %Y.eko %bren %da'), '%a, %Y. %b %d');
    });
    test('ES date format', function () {
        openerp.web._t.database.parameters.date_format = '%a, %Y %b %d';
        var date = openerp.web.str_to_date("2009-05-04");
        strictEqual(openerp.web.format_value(date, {type:"date"}), 'Mon, 2009 May 04');
        strictEqual(openerp.web.parse_value('Mon, 2009 May 04', {type: 'date'}), '2009-05-04');
    });
    test('extended ES date format', function () {
            openerp.web._t.database.parameters.date_format = '%a, %Y.eko %bren %da';
            var date = openerp.web.str_to_date("2009-05-04");
            strictEqual(openerp.web.format_value(date, {type:"date"}), 'Mon, 2009. May 04');
            strictEqual(openerp.web.parse_value('Mon, 2009. May 04', {type: 'date'}), '2009-05-04');
        });

});
