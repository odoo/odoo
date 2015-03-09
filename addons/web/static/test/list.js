odoo.define_section('list.buttons', ['web.ListView', 'web.data'], function (test, mock) {

    test('record-deletion', function (assert, ListView, data) {
        assert.expect(2);
        
        mock.add('demo:fields_view_get', function () {
            return {
                type: 'tree',
                fields: {
                    a: {type: 'char', string: "A"}
                },
                arch: '<tree><field name="a"/><button type="object" name="foo"/></tree>',
            };
        });
        mock.add('demo:read', function (args, kwargs) {
            if (_.isEqual(args[0], [1, 2, 3])) {
                return [
                    {id: 1, a: 'foo'}, {id: 2, a: 'bar'}, {id: 3, a: 'baz'}
                ];
            }
            throw new Error(JSON.stringify(_.toArray(arguments)));
        });
        mock.add('demo:search_read', function (args, kwargs) {
            console.log(args);
            if (_.isEqual(args[0], [['id', 'in', [2]]])) {
                return [];
            }
            throw new Error(JSON.stringify(_.toArray(arguments)));
        });
        mock.add('/web/dataset/call_button', function () { return false; });

        var ds = new data.DataSetStatic(null, 'demo', null, [1, 2, 3]);
        var list = new ListView({
            do_action: odoo.testing.noop
        }, ds, false, {editable: 'top'});

        var $fix = $( "#qunit-fixture");

        return list.appendTo($fix)
        .then(list.proxy('reload_content'))
        .then(function () {
            var d = $.Deferred();
            list.records.bind('remove', function () {
                d.resolve();
            });
            $fix.find('table tbody tr:eq(1) button').click();
            return d.promise();
        })
        .then(function () {
            assert.strictEqual(list.records.length, 2,
                        "should have 2 records left");
            assert.strictEqual($fix.find('table tbody tr[data-id]').length, 2,
                        "should have 2 rows left");
        });

    });
});
