odoo.define_section('compute_domain', ['web.data'], function (test) {

    test("basic", function (assert, data) {
        var fields = {
            'a': {value: 3},
            'group_method': {value: 'line'},
            'select1': {value: 'day'},
            'rrule_type': {value: 'monthly'}
        };
        ok(data.compute_domain(
            [['a', '=', 3]], fields));
        ok(data.compute_domain(
            [['group_method','!=','count']], fields));
        ok(data.compute_domain(
            [['select1','=','day'], ['rrule_type','=','monthly']], fields));
    });

    test("or", function (assert, data) {
        var web = {
            'section_id': {value: null},
            'user_id': {value: null},
            'member_ids': {value: null}
        };

        var domain = ['|', ['section_id', '=', 42],
                      '|', ['user_id','=',3],
                           ['member_ids', 'in', [3]]];

        ok(data.compute_domain(domain, _.extend(
            {}, web, {'section_id': {value: 42}})));
        ok(data.compute_domain(domain, _.extend(
            {}, web, {'user_id': {value: 3}})));

        ok(data.compute_domain(domain, _.extend(
            {}, web, {'member_ids': {value: 3}})));
    });

    test("not", function (assert, data) {
        var fields = {
            'a': {value: 5},
            'group_method': {value: 'line'}
        };
        ok(data.compute_domain(
            ['!', ['a', '=', 3]], fields));
        ok(data.compute_domain(
            ['!', ['group_method','=','count']], fields));
    });
});

