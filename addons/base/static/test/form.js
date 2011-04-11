$(document).ready(function () {
    var widget;
    module("form.widget", {
        setup: function () {
            var openerp = window.openerp.init(true);
            window.openerp.base.chrome(openerp);
            // views loader stuff
            window.openerp.base.data(openerp);
            window.openerp.base.views(openerp);
            window.openerp.base.form(openerp);
            widget = new openerp.base.form.Widget({
                'widgets': {},
                'fields': {}
            }, {
                'attrs': {}
            });
        }
    });
    test("compute_domain", function () {
        widget.view.fields = {
            'a': {value: 3},
            'group_method': {value: 'line'},
            'select1': {value: 'day'},
            'rrule_type': {value: 'monthly'}
        };
        ok(widget.compute_domain([['a', '=', 3]]));
        ok(widget.compute_domain([['group_method','!=','count']]));
        ok(widget.compute_domain([['select1','=','day'],
                                  ['rrule_type','=','monthly']]));
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

        widget.view.fields = _.extend(
            {}, base, {'section_id': {value: 42}});
        ok(widget.compute_domain(domain));

        widget.view.fields =  _.extend(
            {}, base, {'user_id': {value: 3}});
        ok(widget.compute_domain(domain));

        widget.view.fields =  _.extend(
            {}, base, {'member_ids': {value: 3}});
        ok(widget.compute_domain(domain));
    });
});
