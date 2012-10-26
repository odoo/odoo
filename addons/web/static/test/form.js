openerp.testing.section('compute_domain', {
    dependencies: ['web.form']
}, function (test) {
    test("basic", function (instance) {
        var fields = {
            'a': {value: 3},
            'group_method': {value: 'line'},
            'select1': {value: 'day'},
            'rrule_type': {value: 'monthly'}
        };
        ok(instance.web.form.compute_domain(
            [['a', '=', 3]], fields));
        ok(instance.web.form.compute_domain(
            [['group_method','!=','count']], fields));
        ok(instance.web.form.compute_domain(
            [['select1','=','day'], ['rrule_type','=','monthly']], fields));
    });
    test("or", function (instance) {
        var web = {
            'section_id': {value: null},
            'user_id': {value: null},
            'member_ids': {value: null}
        };

        var domain = ['|', ['section_id', '=', 42],
                      '|', ['user_id','=',3],
                           ['member_ids', 'in', [3]]];

        ok(instance.web.form.compute_domain(domain, _.extend(
            {}, web, {'section_id': {value: 42}})));
        ok(instance.web.form.compute_domain(domain, _.extend(
            {}, web, {'user_id': {value: 3}})));

        ok(instance.web.form.compute_domain(domain, _.extend(
            {}, web, {'member_ids': {value: 3}})));
    });
    test("not", function (instance) {
        var fields = {
            'a': {value: 5},
            'group_method': {value: 'line'}
        };
        ok(instance.web.form.compute_domain(
            ['!', ['a', '=', 3]], fields));
        ok(instance.web.form.compute_domain(
            ['!', ['group_method','=','count']], fields));
    });
});
