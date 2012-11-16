$(document).ready(function () {
    var instance;
    var $fix = $('#qunit-fixture');

    module('list.buttons', {
        setup: function () {
            instance = openerp.testing.instanceFor('list');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance);
        }
    });
    asyncTest('record-deletion', 2, function () {
        instance.session.responses['/web/view/load'] = function () {
            return {result: {
                type: 'tree',
                fields: {
                    a: {type: 'char', string: "A"}
                },
                arch: {
                    tag: 'tree',
                    attrs: { },
                    children: [
                        {tag: 'field', attrs: {name: 'a'}},
                        {tag: 'button', attrs: {type: 'object', name: 'foo'}}
                    ]
                }
            }};
        };
        instance.session.responses['/web/dataset/call_kw:read'] = function (req) {
            var args = req.params.args[0];
            if (_.isEqual(args, [1, 2, 3])) {
                return {result: [
                    {id: 1, a: 'foo'}, {id: 2, a: 'bar'}, {id: 3, a: 'baz'}
                ]};
            } else if (_.isEqual(args, [2])) {
                // button action virtually removed record
                return {result: []};
            }
            throw new Error(JSON.stringify(req.params));
        };
        instance.session.responses['/web/dataset/call_button'] = function () {
            return {result: false};
        };
        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1, 2, 3]);
        var l = new instance.web.ListView({}, ds, false, {editable: 'top'});
        l.appendTo($fix)
        .then(l.proxy('reload_content'))
        .then(function () {
            var d = $.Deferred();
            l.records.bind('remove', function () {
                d.resolve();
            });
            $fix.find('table tbody tr:eq(1) button').click();
            return d.promise();
        })
        .always(function () { start(); })
        .then(function () {
            strictEqual(l.records.length, 2,
                        "should have 2 records left");
            strictEqual($fix.find('table tbody tr[data-id]').length, 2,
                        "should have 2 rows left");
        }, function (e) {
            ok(false, e && e.message || e);
        });
    });
});
