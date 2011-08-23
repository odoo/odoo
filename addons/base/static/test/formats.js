$(document).ready(function () {
    var openerp;
    module('base-formats', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.base.core(openerp);
            window.openerp.base.dates(openerp);
            window.openerp.base.formats(openerp);
        }
    });
    test("format_datetime", function () {
        var date = openerp.base.str_to_datetime("2009-05-04 12:34:23");
        var str = openerp.base.format_value(date, {type:"datetime"});
        equal(str, date.format("%m/%d/%Y %H:%M:%S"));
    });
    test("format_date", function () {
        var date = openerp.base.str_to_datetime("2009-05-04 12:34:23");
        var str = openerp.base.format_value(date, {type:"date"});
        equal(str, date.format("%m/%d/%Y"));
    });
    test("format_time", function () {
        var date = openerp.base.str_to_datetime("2009-05-04 12:34:23");
        var str = openerp.base.format_value(date, {type:"time"});
        equal(str, date.format("%H:%M:%S"));
    });
    test("format_float", function () {
        var fl = 12.1234;
        var str = openerp.base.format_value(fl, {type:"float"});
        equal(str, "12.12");
    });
    test("parse_datetime", function () {
        var val = openerp.base.str_to_datetime("2009-05-04 12:34:23");
        var res = openerp.base.parse_value(val.format("%m/%d/%Y %H:%M:%S"), {type:"datetime"});
        equal(val.format("%m/%d/%Y %H:%M:%S"), res.format("%m/%d/%Y %H:%M:%S"));
    });
    test("parse_date", function () {
        var val = openerp.base.str_to_date("2009-05-04");
        var res = openerp.base.parse_value(val.format("%m/%d/%Y"), {type:"date"});
        equal(val.format("%m/%d/%Y %H:%M:%S"), res.format("%m/%d/%Y %H:%M:%S"));
    });
    test("parse_time", function () {
        var val = openerp.base.str_to_time("12:34:23");
        var res = openerp.base.parse_value(val.format("%H:%M:%S"), {type:"time"});
        equal(val.format("%m/%d/%Y %H:%M:%S"), res.format("%m/%d/%Y %H:%M:%S"));
    });
    test("parse_float", function () {
        var str = "134,112.1234";
        var val = openerp.base.parse_value(str, {type:"float"});
        equal(val, 134112.1234);
    });
});