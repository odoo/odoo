$(document).ready(function () {
    var t = window.openerp.test_support;

    t.module('check', 'data');
    t.test('check1', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'res.users', {});
        t.expect(ds.create({name: 'foo'}), function (result) {
            ok(false, 'ha ha ha')
        });
    });
});
