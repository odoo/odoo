$(document).ready(function () {
    var openerp;
    module("form.widget", {
        setup: function () {
            openerp = window.openerp.init(true);
            window.openerp.base.chrome(openerp);
            // views loader stuff
            window.openerp.base.data(openerp);
            window.openerp.base.views(openerp);
            window.openerp.base.form(openerp);
        }
    });
    test("compute_domain", function () {
        var fields = {
            'a': {value: 3},
            'group_method': {value: 'line'},
            'select1': {value: 'day'},
            'rrule_type': {value: 'monthly'}
        };
        ok(openerp.base.form.compute_domain(
            [['a', '=', 3]], fields));
        ok(openerp.base.form.compute_domain(
            [['group_method','!=','count']], fields));
        ok(openerp.base.form.compute_domain(
            [['select1','=','day'], ['rrule_type','=','monthly']], fields));
    });
    test("compute_domain or", function () {
        var base = {
            'section_id': {value: null},
            'user_id': {value: null},
            'member_ids': {value: null}
        };

        var domain = ['|', ['section_id', '=', 42],
                      '|', ['user_id','=',3],
                           ['member_ids', 'in', [3]]];

        ok(openerp.base.form.compute_domain(domain, _.extend(
            {}, base, {'section_id': {value: 42}})));
        ok(openerp.base.form.compute_domain(domain, _.extend(
            {}, base, {'user_id': {value: 3}})));

        ok(openerp.base.form.compute_domain(domain, _.extend(
            {}, base, {'member_ids': {value: 3}})));
    });
});
