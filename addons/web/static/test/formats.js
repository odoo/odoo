$(document).ready(function () {
    var openerp;
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
    test("parse_float", function () {
        var str = "134,112.1234";
        var val = openerp.web.parse_value(str, {type:"float"});
        equal(val, 134112.1234);
        var str = "-134,112.1234";
        var val = openerp.web.parse_value(str, {type:"float"});
        equal(val, -134112.1234);
    });
});
