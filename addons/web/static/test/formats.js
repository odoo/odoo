openerp.testing.section('web-formats', {
    dependencies: ['web.formats']
}, function (test) {
    test("format_datetime", function (instance) {
        var date = instance.web.str_to_datetime("2009-05-04 12:34:23");
        var str = instance.web.format_value(date, {type:"datetime"});
        equal(str, moment(date).format("MM/DD/YYYY HH:mm:ss"));
    });
    test("format_date", function (instance) {
        var date = instance.web.str_to_datetime("2009-05-04 12:34:23");
        var str = instance.web.format_value(date, {type:"date"});
        equal(str, moment(date).format("MM/DD/YYYY"));
    });
    test("format_time", function (instance) {
        var date = instance.web.str_to_datetime("2009-05-04 12:34:23");
        var str = instance.web.format_value(date, {type:"time"});
        equal(str, moment(date).format("HH:mm:ss"));
    });
    test("format_float_time", function (instance) {
        strictEqual(
            instance.web.format_value(1.0, {type:'float', widget:'float_time'}),
            '01:00');
        strictEqual(
            instance.web.format_value(0.9853, {type:'float', widget:'float_time'}),
            '00:59');
        strictEqual(
            instance.web.format_value(0.0085, {type:'float', widget:'float_time'}),
            '00:01');
        strictEqual(
            instance.web.format_value(-1.0, {type:'float', widget:'float_time'}),
            '-01:00');
        strictEqual(
            instance.web.format_value(-0.9853, {type:'float', widget:'float_time'}),
            '-00:59');
        strictEqual(
            instance.web.format_value(-0.0085, {type:'float', widget:'float_time'}),
            '-00:01');
        strictEqual(
            instance.web.format_value(4.9999, {type:'float', widget:'float_time'}),
            '05:00');
        strictEqual(
            instance.web.format_value(-6.9999, {type:'float', widget:'float_time'}),
            '-07:00');
    });
    test("format_float", function (instance) {
        var fl = 12.1234;
        var str = instance.web.format_value(fl, {type:"float"});
        equal(str, "12.12");
        equal(instance.web.format_value(12.02, {type: 'float'}),
              '12.02');
        equal(instance.web.format_value(0.0002, {type: 'float', digits: [1, 3]}),
              '0.000');
        equal(instance.web.format_value(0.0002, {type: 'float', digits: [1, 4]}),
              '0.0002');
        equal(instance.web.format_value(0.0002, {type: 'float', digits: [1, 6]}),
              '0.000200');
        equal(instance.web.format_value(1, {type: 'float', digits: [1, 6]}),
              '1.000000');
        equal(instance.web.format_value(1, {type: 'float'}),
              '1.00');
        equal(instance.web.format_value(-11.25, {type: 'float'}),
              "-11.25");
        instance.web._t.database.parameters.grouping = [1, 2, -1];
        equal(instance.web.format_value(1111111.25, {type: 'float'}),
              "1111,11,1.25");
        instance.web._t.database.parameters.grouping = [1, 0];
        equal(instance.web.format_value(-11.25, {type: 'float'}),
              "-1,1.25");
    });
    test('parse_integer', function (instance) {
        var tmp = instance.web._t.database.parameters.thousands_sep;
        try {
            var val = instance.web.parse_value('123,456', {type: 'integer'});
            equal(val, 123456);
            instance.web._t.database.parameters.thousands_sep = '|';
            var val2 = instance.web.parse_value('123|456', {type: 'integer'});
            equal(val2, 123456);
        } finally {
            instance.web._t.database.parameters.thousands_sep = tmp;
        }
    });
    test("parse_float", function (instance) {
        var tmp1 = instance.web._t.database.parameters.thousands_sep;
        var tmp2 = instance.web._t.database.parameters.decimal_point;
        try {
            var str = "134,112.1234";
            var val = instance.web.parse_value(str, {type:"float"});
            equal(val, 134112.1234);
            str = "-134,112.1234";
            val = instance.web.parse_value(str, {type:"float"});
            equal(val, -134112.1234);
            _.extend(instance.web._t.database.parameters, {
                decimal_point: ',',
                thousands_sep: '.'
            });
            var val3 = instance.web.parse_value('123.456,789', {type: 'float'});
            equal(val3, 123456.789);
        } finally {
            instance.web._t.database.parameters.thousands_sep = tmp1;
            instance.web._t.database.parameters.decimal_point = tmp2;
        }
    });
    test('intersperse', function (instance) {
        var g = instance.web.intersperse;
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
    test('format_integer', function (instance) {
        instance.web._t.database.parameters.grouping = [3, 3, 3, 3];
        equal(instance.web.format_value(1000000, {type: 'integer'}),
              '1,000,000');
        instance.web._t.database.parameters.grouping = [3, 2, -1];
        equal(instance.web.format_value(106500, {type: 'integer'}),
              '1,06,500');
        instance.web._t.database.parameters.grouping = [1, 2, -1];
        equal(instance.web.format_value(106500, {type: 'integer'}),
              '106,50,0');
    });
    test('format_float', function (instance) {
        instance.web._t.database.parameters.grouping = [3, 3, 3, 3];
        equal(instance.web.format_value(1000000, {type: 'float'}),
              '1,000,000.00');
        instance.web._t.database.parameters.grouping = [3, 2, -1];
        equal(instance.web.format_value(106500, {type: 'float'}),
              '1,06,500.00');
        instance.web._t.database.parameters.grouping = [1, 2, -1];
        equal(instance.web.format_value(106500, {type: 'float'}),
              '106,50,0.00');

        _.extend(instance.web._t.database.parameters, {
            grouping: [3, 0],
            decimal_point: ',',
            thousands_sep: '.'
        });
        equal(instance.web.format_value(6000, {type: 'float'}),
              '6.000,00');
    });
});
openerp.testing.section('web-formats', {
    dependencies: ['web.formats']
}, function (test) {
    test('ES date format', function (instance) {
        var old_format = instance.web._t.database.parameters.date_format;
        instance.web._t.database.parameters.date_format = '%a, %Y %b %d';
        var date = instance.web.str_to_date("2009-05-04");
        strictEqual(instance.web.format_value(date, {type:"date"}),
                    'Mon, 2009 May 04');
        strictEqual(instance.web.parse_value('Mon, 2009 May 04', {type: 'date'}),
                    '2009-05-04');
        instance.web._t.database.parameters.date_format = old_format;
    });
    test('extended ES date format', function (instance) {
        var old_format = instance.web._t.database.parameters.date_format;
        instance.web._t.database.parameters.date_format = '%a, %Y.eko %b %da';
        var date = instance.web.str_to_date("2009-05-04");
        strictEqual(instance.web.format_value(date, {type:"date"}),
                    'Mon, 2009.eko May 04a');
        strictEqual(instance.web.parse_value('Mon, 2009.eko May 04a', {type: 'date'}),
                    '2009-05-04');
        instance.web._t.database.parameters.date_format = old_format;
    });

});
