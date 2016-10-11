odoo.define_section('web.dataset', ['web.data'], function (test, mock) {

    test('read_ids', function (assert, data) {
        assert.expect(2);
        var mock = _.last(arguments);

        mock.add('foo:read', function (args) {
            var ids = args[0];
            assert.deepEqual(ids, [3, 1, 2]);
            return [
                {id: 1, a: 'bar'},
                {id: 2, a: 'baz'},
                {id: 3, a: 'foo'}
            ];
        });

        var d = new data.DataSet(null, 'foo');
        return d.read_ids([3,1,2]).then(function (records) {
            assert.deepEqual(
                records,
                [
                    {id:3, a: 'foo'},
                    {id:1, a: 'bar'},
                    {id:2, a: 'baz'}
                ]
            );
        });
    });
});

odoo.define_section('data.model.group_by', ['web.data'], function (test, mock) {

    function group_result () {
        return [
            { bar: 3, bar_count: 5, __context: {}, __domain: [['bar', '=', 3]], },
            { bar: 5, bar_count: 3, __context: {}, __domain: [['bar', '=', 5]], },
            { bar: 8, bar_count: 0, __context: {}, __domain: [['bar', '=', 8]], }
        ];
    }

    function rec  () {
        return {records: [
            {bar: 3, id: 1},
            {bar: 3, id: 2},
            {bar: 3, id: 4},
            {bar: 3, id: 8},
            {bar: 3, id: 16}
        ], length: 5};
    }

    test('basic', function (assert, data) {
        assert.expect(7);
        var mock = _.last(arguments);

        mock.add('foo:read_group', function (args, kwargs) {
            assert.deepEqual(kwargs.fields, ['bar'], "should read grouping field");
            assert.deepEqual(kwargs.groupby, ['bar'], "should have single grouping field");
            return group_result();
        });

        mock.add('/web/dataset/search_read', function (args) {
            assert.deepEqual(args.params.domain, [['bar', '=', 3]], "should have domain matching that of group_by result");
            return rec();
        });

        var m = new data.Model('foo');

        return m.query().group_by('bar')
        .then(function (groups) {
            assert.ok(groups, "should have data");
            assert.equal(groups.length, 3, "should have three results");
            var first = groups[0];
            assert.ok(first.attributes.has_children, "should have children");
            return  first.query().all();
        }).then(function (first) {
            assert.equal(first.length, 5, "should have 5 records");
        });

    });

    test('noleaf', function (assert, data) {
        assert.expect(5);
        var mock = _.last(arguments);

        mock.add('foo:read_group', function (args, kwargs) {
            assert.deepEqual(kwargs.fields, ['bar'], "should read grouping field");
            assert.deepEqual(kwargs.groupby, ['bar'], "should have single grouping field");
            return group_result();
        });

        mock.add('/web/dataset/search_read', function (args) {
            assert.deepEqual(args.params.domain, [['bar', '=', 3]], "should have domain matching that of group_by result");
            return rec();
        });

        var m = new data.Model('foo', {group_by_no_leaf: true});

        return m.query().group_by('bar')
        .then(function (groups) {
            assert.ok(groups, "should have data");
            assert.equal(groups.length, 3, "should have three results");
            assert.ok(!groups[0].attributes.has_children,
                "should not have children because no_leaf");
        });
    });

    test('nogroup', function (assert, data) {
        var m = new data.Model('foo');
        assert.strictEqual(m.query().group_by(), null, "should not group");
    });

    test('empty.noleaf', function (assert, data) {
        assert.expect(1);
        var mock = _.last(arguments);

        var m = new data.Model('foo',  {group_by_no_leaf: true});
        
        mock.add('foo:read_group', function (args, kwargs) {
            return [{__context: [], __domain: []}];
        });

        return m.query().group_by().done(function (groups) {
            assert.strictEqual(groups.length, 1, "should generate a single fake-ish group");
        });
    });

});
