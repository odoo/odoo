odoo.define_section('web-formats', ['web.formats', 'web.time'], function (test) {

    test("format_datetime", function (assert, formats, time) {
        var date = time.str_to_datetime("2009-05-04 12:34:23");
        var str = formats.format_value(date, {type:"datetime"});
        assert.equal(str, moment(date).format("MM/DD/YYYY HH:mm:ss"));
    });

    test("format_date", function (assert, formats, time) {
        var date = time.str_to_datetime("2009-05-04 12:34:23");
        var str = formats.format_value(date, {type:"date"});
        assert.equal(str, moment(date).format("MM/DD/YYYY"));
    });

    test("format_time", function (assert, formats, time) {
        var date = time.str_to_datetime("2009-05-04 12:34:23");
        var str = formats.format_value(date, {type:"time"});
        assert.equal(str, moment(date).format("HH:mm:ss"));
    });

    test("format_float_time", function (assert, formats) {
        assert.strictEqual(
            formats.format_value(1.0, {type:'float', widget:'float_time'}),
            '01:00');
        assert.strictEqual(
            formats.format_value(0.9853, {type:'float', widget:'float_time'}),
            '00:59');
        assert.strictEqual(
            formats.format_value(0.0085, {type:'float', widget:'float_time'}),
            '00:01');
        assert.strictEqual(
            formats.format_value(-1.0, {type:'float', widget:'float_time'}),
            '-01:00');
        assert.strictEqual(
            formats.format_value(-0.9853, {type:'float', widget:'float_time'}),
            '-00:59');
        assert.strictEqual(
            formats.format_value(-0.0085, {type:'float', widget:'float_time'}),
            '-00:01');
        assert.strictEqual(
            formats.format_value(4.9999, {type:'float', widget:'float_time'}),
            '05:00');
        assert.strictEqual(
            formats.format_value(-6.9999, {type:'float', widget:'float_time'}),
            '-07:00');
    });

    test("format_float", ['web.core'], function (assert, formats, time, core) {
        var fl = 12.1234;
        var str = formats.format_value(fl, {type:"float"});
        assert.equal(str, "12.12");
        assert.equal(formats.format_value(12.02, {type: 'float'}),
              '12.02');
        assert.equal(formats.format_value(0.0002, {type: 'float', digits: [1, 3]}),
              '0.000');
        assert.equal(formats.format_value(0.0002, {type: 'float', digits: [1, 4]}),
              '0.0002');
        assert.equal(formats.format_value(0.0002, {type: 'float', digits: [1, 6]}),
              '0.000200');
        assert.equal(formats.format_value(1, {type: 'float', digits: [1, 6]}),
              '1.000000');
        assert.equal(formats.format_value(1, {type: 'float'}),
              '1.00');
        assert.equal(formats.format_value(-11.25, {type: 'float'}),
              "-11.25");
        core._t.database.parameters.grouping = [1, 2, -1];
        assert.equal(formats.format_value(1111111.25, {type: 'float'}),
              "1111,11,1.25");

        core._t.database.parameters.grouping = [1, 0];
        assert.equal(formats.format_value(-11.25, {type: 'float'}),
              "-1,1.25");
    });

    test('parse_integer', ['web.core'], function (assert, formats, time, core) {
        var tmp = core._t.database.parameters.thousands_sep;
        try {
            var val = formats.parse_value('123,456', {type: 'integer'});
            assert.equal(val, 123456);
            core._t.database.parameters.thousands_sep = '|';
            var val2 = formats.parse_value('123|456', {type: 'integer'});
            assert.equal(val2, 123456);
        } finally {
            core._t.database.parameters.thousands_sep = tmp;
        }
    });

    test("parse_float", ['web.core'], function (assert, formats, time, core) {
        var tmp1 = core._t.database.parameters.thousands_sep;
        var tmp2 = core._t.database.parameters.decimal_point;
        try {
            var str = "134,112.1234";
            var val = formats.parse_value(str, {type:"float"});
            assert.equal(val, 134112.1234);
            str = "-134,112.1234";
            val = formats.parse_value(str, {type:"float"});
            assert.equal(val, -134112.1234);
            _.extend(core._t.database.parameters, {
                decimal_point: ',',
                thousands_sep: '.'
            });
            var val3 = formats.parse_value('123.456,789', {type: 'float'});
            assert.equal(val3, 123456.789);
        } finally {
            core._t.database.parameters.thousands_sep = tmp1;
            core._t.database.parameters.decimal_point = tmp2;
        }
    });

    test('intersperse', ['web.utils'], function (assert, formats, time, utils) {
        var intersperse = utils.intersperse;

        assert.equal(intersperse("", []), "");
        assert.equal(intersperse("0", []), "0");
        assert.equal(intersperse("012", []), "012");
        assert.equal(intersperse("1", []), "1");
        assert.equal(intersperse("12", []), "12");
        assert.equal(intersperse("123", []), "123");
        assert.equal(intersperse("1234", []), "1234");
        assert.equal(intersperse("123456789", []), "123456789");
        assert.equal(intersperse("&ab%#@1", []), "&ab%#@1");

        assert.equal(intersperse("0", []), "0");
        assert.equal(intersperse("0", [1]), "0");
        assert.equal(intersperse("0", [2]), "0");
        assert.equal(intersperse("0", [200]), "0");

        assert.equal(intersperse("12345678", [0], '.'), '12345678');
        assert.equal(intersperse("", [1], '.'), '');
        assert.equal(intersperse("12345678", [1], '.'), '1234567.8');
        assert.equal(intersperse("12345678", [1], '.'), '1234567.8');
        assert.equal(intersperse("12345678", [2], '.'), '123456.78');
        assert.equal(intersperse("12345678", [2, 1], '.'), '12345.6.78');
        assert.equal(intersperse("12345678", [2, 0], '.'), '12.34.56.78');
        assert.equal(intersperse("12345678", [-1, 2], '.'), '12345678');
        assert.equal(intersperse("12345678", [2, -1], '.'), '123456.78');
        assert.equal(intersperse("12345678", [2, 0, 1], '.'), '12.34.56.78');
        assert.equal(intersperse("12345678", [2, 0, 0], '.'), '12.34.56.78');
        assert.equal(intersperse("12345678", [2, 0, -1], '.'), '12.34.56.78');
        assert.equal(intersperse("12345678", [3,3,3,3], '.'), '12.345.678');
        assert.equal(intersperse("12345678", [3,0], '.'), '12.345.678');
    });

    test('format_integer', ['web.core'], function (assert, formats, time, core) {
        core._t.database.parameters.grouping = [3, 3, 3, 3];
        assert.equal(formats.format_value(1000000, {type: 'integer'}),
              '1,000,000');

        core._t.database.parameters.grouping = [3, 2, -1];
        assert.equal(formats.format_value(106500, {type: 'integer'}),
              '1,06,500');

        core._t.database.parameters.grouping = [1, 2, -1];
        assert.equal(formats.format_value(106500, {type: 'integer'}),
              '106,50,0');
    });

    test('format_float', ['web.core'], function (assert, formats, time, core) {
        core._t.database.parameters.grouping = [3, 3, 3, 3];
        assert.equal(formats.format_value(1000000, {type: 'float'}),
              '1,000,000.00');

        core._t.database.parameters.grouping = [3, 2, -1];
        assert.equal(formats.format_value(106500, {type: 'float'}),
              '1,06,500.00');
        
        core._t.database.parameters.grouping = [1, 2, -1];
        assert.equal(formats.format_value(106500, {type: 'float'}),
              '106,50,0.00');

        _.extend(core._t.database.parameters, {
            grouping: [3, 0],
            decimal_point: ',',
            thousands_sep: '.'
        });
        assert.equal(formats.format_value(6000, {type: 'float'}),
              '6.000,00');
    });

    test('ES date format', ['web.core'], function (assert, formats, time, core) {
        var old_format = core._t.database.parameters.date_format;
        core._t.database.parameters.date_format = '%a, %Y %b %d';
        
        var date = time.str_to_date("2009-05-04");
        assert.strictEqual(formats.format_value(date, {type:"date"}),
                    'Mon, 2009 May 04');
        assert.strictEqual(formats.parse_value('Mon, 2009 May 04', {type: 'date'}),
                    '2009-05-04');
        core._t.database.parameters.date_format = old_format;
    });

    test('extended ES date format', ['web.core'], function (assert, formats, time, core) {
        var old_format = core._t.database.parameters.date_format;
        core._t.database.parameters.date_format = '%a, %Y.eko %b %da';
        var date = time.str_to_date("2009-05-04");
        assert.strictEqual(formats.format_value(date, {type:"date"}),
                    'Mon, 2009.eko May 04a');
        assert.strictEqual(formats.parse_value('Mon, 2009.eko May 04a', {type: 'date'}),
                    '2009-05-04');
        core._t.database.parameters.date_format = old_format;
    });

});
