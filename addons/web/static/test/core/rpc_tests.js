odoo.define('web.rpc_tests', function (require) {
"use strict";

var rpc = require('web.rpc');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

function createQuery (params) {
    var widget = new Widget();

    if (params.mockRPC) {
        testUtils.intercept(widget, 'call_service', function (event) {
            if (event.data.service === 'ajax') {
                params.mockRPC(event.data.args[0], JSON.parse(JSON.stringify(event.data.args[1])));
            }
        });

    }

    return rpc.query({
        method: params.method,
        model: params.model,
        route: params.route,
        parent: widget,
    });
}

QUnit.module('core', {}, function () {

    QUnit.module('RPC Builder');

    QUnit.test('basic rpc (route)', function (assert) {
        assert.expect(1);
        var query = createQuery({
            route: '/my/route',
            mockRPC: function (route) {
                assert.strictEqual(route, '/my/route',
                    "should call the proper route");
            }
        });
        query.exec();
    });

    QUnit.test('basic rpc, with no context', function (assert) {
        assert.expect(1);
        var query = createQuery({
            route: '/my/route',
            mockRPC: function (route, args) {
                assert.notOk('context' in args.kwargs,
                    "does not automatically add a context");
            }
        });
        query.exec();
    });

    QUnit.test('basic rpc, with context', function (assert) {
        assert.expect(1);
        var query = createQuery({
            route: '/my/route',
            mockRPC: function (route, args) {
                assert.deepEqual(args.kwargs.context, {a: 1},
                    "properly transfer the context");
            }
        });
        query.withContext({a: 1}).exec();
    });

    QUnit.test('basic rpc, with context, part 2', function (assert) {
        assert.expect(1);
        var query = createQuery({
            route: '/my/route',
            mockRPC: function (route, args) {
                assert.deepEqual(args.kwargs.context, {a: 1},
                    "properly transfer the context");
            }
        });
        query.kwargs({context: {a: 1}}).exec();
    });

    QUnit.test('basic rpc (method of model)', function (assert) {
        assert.expect(3);
        var query = createQuery({
            model: 'partner',
            method: 'test',
            mockRPC: function (route, args) {
                assert.strictEqual(route, '/web/dataset/call_kw/partner/test',
                    "should call the proper route");
                assert.strictEqual(args.model, 'partner',
                    "should correctly specify the model");
                assert.strictEqual(args.method, 'test',
                    "should correctly specify the method");
            }
        });
        query.exec();
    });

    QUnit.test('rpc with args and kwargs', function (assert) {
        assert.expect(4);
        var query = createQuery({
            model: 'partner',
            method: 'test',
            mockRPC: function (route, args) {
                assert.strictEqual(route, '/web/dataset/call_kw/partner/test',
                    "should call the proper route");
                assert.strictEqual(args.args[0], 'arg1',
                    "should call with correct args");
                assert.strictEqual(args.args[1], 2,
                    "should call with correct args");
                assert.strictEqual(args.kwargs.k, 78,
                    "should call with correct kargs");
            }
        });
        query
            .args(['arg1', 2])
            .kwargs({k: 78})
            .exec();
    });

    QUnit.test('rpc with context', function (assert) {
        assert.expect(1);
        var query = createQuery({
            model: 'partner',
            method: 'test',
            mockRPC: function (route, args) {
                assert.deepEqual(args.kwargs.context, { a: 'hello' },
                    "should have correct context");
            },
        });
        query
            .withContext({a: 'hello'})
            .exec();
    });

    QUnit.test('search_read', function (assert) {
        assert.expect(1);
        var query = createQuery({
            model: 'partner',
            method: 'search_read',
            mockRPC: function (route, args) {
                assert.deepEqual(args, {
                    context: {},
                    domain: ['a', '=', 1],
                    fields: ['name'],
                    limit: 32,
                    model: 'partner',
                    sort: 'yop ASC, aa DESC',
                }, "should have correct args");
            },
        });
        query
            .withDomain(['a', '=', 1])
            .withFields(['name'])
            .withLimit(32)
            .orderBy([{name: 'yop', asc: true}, {name: 'aa', asc: false}])
            .exec();
    });

    QUnit.test('read_group', function (assert) {
        assert.expect(2);
        var query = createQuery({
            model: 'partner',
            method: 'read_group',
            mockRPC: function (route, args) {
                assert.deepEqual(args, {
                    args: [],
                    kwargs: {
                        context: {abc: 'def'},
                        domain: ['a', '=', 1],
                        fields: ['name'],
                        groupby: ['product_id'],
                        lazy: true,
                        orderby: false,
                    },
                    method: 'read_group',
                    model: 'partner',
                }, "should have correct args");
                assert.equal(route, '/web/dataset/call_kw/partner/read_group',
                    "should call correct route");
            },
        });
        query
            .withDomain(['a', '=', 1])
            .withFields(['name'])
            .groupBy(['product_id'])
            .withContext({abc: 'def'})
            .lazy(true)
            .exec();
    });

    QUnit.test('search_read with no domain, nor fields', function (assert) {
        assert.expect(2);
        createQuery({
            model: 'partner',
            method: 'search_read',
            mockRPC: function (route, args) {
                assert.deepEqual(args.domain, [], "should have [] as default domain");
                assert.strictEqual(args.fields, false, "should have false as default fields");
            },
        }).exec();
    });
});

});