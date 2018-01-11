openerp.testing.section('data.dataset', {
    rpc: 'mock',
    dependencies: ['web.data'],
}, function (test) {
    test('read_ids', {asserts: 2}, function (instance, _, mock) {
        var d = new instance.web.DataSet(null, 'foo');
        mock('foo:read', function (args) {
            var ids = args[0];
            deepEqual(ids, [3, 1, 2]);
            return [
                {id: 1, a: 'bar'},
                {id: 2, a: 'baz'},
                {id: 3, a: 'foo'}
            ];
        });

        return d.read_ids([3, 1, 2]).then(function (records) {
            deepEqual(
                records,
                [
                    {id: 3, a: 'foo'},
                    {id: 1, a: 'bar'},
                    {id: 2, a: 'baz'}
                ]
            )
        });
    })
});

openerp.testing.section('data.model.group_by', {
    rpc: 'mock',
    dependencies: ['web.data'],
}, function (test) {
    var group_result = [{
        bar: 3, bar_count: 5, __context: {}, __domain: [['bar', '=', 3]],
    }, {
        bar: 5, bar_count: 3, __context: {}, __domain: [['bar', '=', 5]],
    }, {
        bar: 8, bar_count: 0, __context: {}, __domain: [['bar', '=', 8]],
    }];
    test('basic', {asserts: 7}, function (instance, $fix, mock) {
        var m = new instance.web.Model('foo');
        mock('foo:read_group', function (args, kwargs) {
            deepEqual(kwargs.fields, ['bar'],
                      "should read grouping field");
            deepEqual(kwargs.groupby, ['bar'],
                      "should have single grouping field");
            return group_result;
        });
        mock('/web/dataset/search_read', function (args) {
            deepEqual(args.params.domain, [['bar', '=', 3]],
                      "should have domain matching that of group_by result");
            return {records: [
                {bar: 3, id: 1},
                {bar: 3, id: 2},
                {bar: 3, id: 4},
                {bar: 3, id: 8},
                {bar: 3, id: 16}
            ], length: 5};
        });

        return m.query().group_by('bar')
        .then(function (groups) {
            ok(groups, "should have data");
            equal(groups.length, 3, "should have three results");
            var first = groups[0];
            ok(first.attributes.has_children, "should have children");
            return  first.query().all();
        }).done(function (first) {
            equal(first.length, 5, "should have 5 records");
        });
    });
    test('noleaf', {asserts: 5}, function (instance, $fix, mock) {
        var m = new instance.web.Model('foo', {group_by_no_leaf: true});
        mock('foo:read_group', function (args, kwargs) {
            deepEqual(kwargs.fields, ['bar'],
                      "should read grouping field");
            deepEqual(kwargs.groupby, ['bar'],
                      "should have single grouping field");

            return  group_result;
        });
        return m.query().group_by('bar')
        .then(function (groups) {
            ok(groups, "should have data");
            equal(groups.length, 3, "should have three results");
            ok(!groups[0].attributes.has_children,
                "should not have children because no_leaf");
        });
    });
    test('nogroup', {rpc: false}, function (instance, $f, mock) {
        var m = new instance.web.Model('foo');
        strictEqual(m.query().group_by(), null, "should not group");
    });
    test('empty.noleaf', {asserts: 1}, function (instance, $f, mock) {
        var m = new instance.web.Model('foo',  {group_by_no_leaf: true});
        mock('foo:read_group', function (args, kwargs) {
            return [{__context: [], __domain: []}];
        });
        return m.query().group_by().done(function (groups) {
            strictEqual(groups.length, 1,
                        "should generate a single fake-ish group");
        });
    });
});
