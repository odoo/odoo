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
        equal(str, date.toString("M/d/yyyy h:mm:ss tt"));
    });
    test("format_date", function () {
        var date = openerp.base.str_to_datetime("2009-05-04 12:34:23");
        var str = openerp.base.format_value(date, {type:"date"});
        equal(str, date.toString("M/d/yyyy"));
    });
    test("format_time", function () {
        var date = openerp.base.str_to_datetime("2009-05-04 12:34:23");
        var str = openerp.base.format_value(date, {type:"time"});
        equal(str, date.toString("h:mm:ss tt"));
    });
    test("format_float", function () {
        var fl = 12.1234;
        var str = openerp.base.format_value(fl, {type:"float"});
        equal(str, "12.12");
    });
    test("parse_datetime", function () {
        var val = openerp.base.str_to_datetime("2009-05-04 12:34:23");
        var res = openerp.base.parse_value(val.toString("M/d/yyyy h:mm:ss tt"), {type:"datetime"});
        equal(val.toString("M/d/yyyy h:mm:ss tt"), res.toString("M/d/yyyy h:mm:ss tt"));
    });
    test("parse_date", function () {
        var val = openerp.base.str_to_date("2009-05-04");
        var res = openerp.base.parse_value(val.toString("M/d/yyyy"), {type:"date"});
        equal(val.toString("M/d/yyyy"), res.toString("M/d/yyyy"));
    });
    test("parse_time", function () {
        var val = openerp.base.str_to_time("12:34:23");
        var res = openerp.base.parse_value(val.toString("h:mm:ss tt"), {type:"time"});
        equal(val.toString("h:mm:ss tt"), res.toString("h:mm:ss tt"));
    });
    test("parse_float", function () {
        var str = "134,112.1234";
        var val = openerp.base.parse_value(str, {type:"float"});
        equal(val, 134112.1234);
        var str = "-134,112.1234";
        var val = openerp.base.parse_value(str, {type:"float"});
        equal(val, -134112.1234);
    });
});