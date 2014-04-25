openerp.testing.section('list.buttons', {
    dependencies: ['web.list', 'web.form'],
    rpc: 'mock',
    templates: true
}, function (test) {
    test('record-deletion', {asserts: 2}, function (instance, $fix, mock) {
        mock('demo:fields_view_get', function () {
            return {
                type: 'tree',
                fields: {
                    a: {type: 'char', string: "A"}
                },
                arch: '<tree><field name="a"/><button type="object" name="foo"/></tree>',
            };
        });
        mock('demo:read', function (args, kwargs) {
            if (_.isEqual(args[0], [1, 2, 3])) {
                return [
                    {id: 1, a: 'foo'}, {id: 2, a: 'bar'}, {id: 3, a: 'baz'}
                ];
            }
            throw new Error(JSON.stringify(_.toArray(arguments)));
        });
        mock('demo:search_read', function (args, kwargs) {
            console.log(args);
            if (_.isEqual(args[0], [['id', 'in', [2]]])) {
                return [];
            }
            throw new Error(JSON.stringify(_.toArray(arguments)));
        });
        mock('/web/dataset/call_button', function () { return false; });
        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1, 2, 3]);
        var l = new instance.web.ListView({
            do_action: openerp.testing.noop
        }, ds, false, {editable: 'top'});
        return l.appendTo($fix)
        .then(l.proxy('reload_content'))
        .then(function () {
            var d = $.Deferred();
            l.records.bind('remove', function () {
                d.resolve();
            });
            $fix.find('table tbody tr:eq(1) button').click();
            return d.promise();
        })
        .then(function () {
            strictEqual(l.records.length, 2,
                        "should have 2 records left");
            strictEqual($fix.find('table tbody tr[data-id]').length, 2,
                        "should have 2 rows left");
        });
    });
});
