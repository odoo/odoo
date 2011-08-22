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
        console.log(str);
    });
});