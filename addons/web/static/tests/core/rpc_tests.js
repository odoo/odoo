odoo.define('web.rpc_tests', function (require) {
"use strict";

var rpc = require('web.rpc');

QUnit.module('core', {}, function () {

    QUnit.module('RPC Builder');

    QUnit.test('basic rpc (route)', function (assert) {
        assert.expect(1);

        var query = rpc.buildQuery({
            route: '/my/route',
        });
        assert.strictEqual(query.route, '/my/route', "should have the proper route");
    });

    QUnit.test('rpc on route with parameters', function (assert) {
        assert.expect(1);

        var query = rpc.buildQuery({
            route: '/my/route',
            params: {hey: 'there', model: 'test'},
        });

        assert.deepEqual(query.params, {hey: 'there', model: 'test'},
                    "should transfer the proper parameters");
    });

    QUnit.test('basic rpc, with no context', function (assert) {
        assert.expect(1);

        var query = rpc.buildQuery({
            model: 'partner',
            method: 'test',
            kwargs: {},
        });
        assert.notOk(query.params.kwargs.context,
            "does not automatically add a context");
    });

    QUnit.test('basic rpc, with context', function (assert) {
        assert.expect(1);

        var query = rpc.buildQuery({
            model: 'partner',
            method: 'test',
            context: {a: 1},
        });

        assert.deepEqual(query.params.kwargs.context, {a: 1},
            "properly transfer the context");
    });

    QUnit.test('basic rpc, with context, part 2', function (assert) {
        assert.expect(1);

        var query = rpc.buildQuery({
            model: 'partner',
            method: 'test',
            kwargs: {context: {a: 1}},
        });

        assert.deepEqual(query.params.kwargs.context, {a: 1},
            "properly transfer the context");

    });

    QUnit.test('basic rpc (method of model)', function (assert) {
        assert.expect(3);

        var query = rpc.buildQuery({
            model: 'partner',
            method: 'test',
            kwargs: {context: {a: 1}},
        });

        assert.strictEqual(query.route, '/web/dataset/call_kw/partner/test',
            "should call the proper route");
        assert.strictEqual(query.params.model, 'partner',
            "should correctly specify the model");
        assert.strictEqual(query.params.method, 'test',
            "should correctly specify the method");
    });

    QUnit.test('rpc with args and kwargs', function (assert) {
        assert.expect(4);
        var query = rpc.buildQuery({
            model: 'partner',
            method: 'test',
            args: ['arg1', 2],
            kwargs: {k: 78},
        });

        assert.strictEqual(query.route, '/web/dataset/call_kw/partner/test',
            "should call the proper route");
        assert.strictEqual(query.params.args[0], 'arg1',
            "should call with correct args");
        assert.strictEqual(query.params.args[1], 2,
            "should call with correct args");
        assert.strictEqual(query.params.kwargs.k, 78,
            "should call with correct kargs");
    });

    QUnit.test('search_read controller', function (assert) {
        assert.expect(1);
        var query = rpc.buildQuery({
            route: '/web/dataset/search_read',
            model: 'partner',
            domain: ['a', '=', 1],
            fields: ['name'],
            limit: 32,
            offset: 2,
            orderBy: [{name: 'yop', asc: true}, {name: 'aa', asc: false}],
        });
        assert.deepEqual(query.params, {
            context: {},
            domain: ['a', '=', 1],
            fields: ['name'],
            limit: 32,
            offset: 2,
            model: 'partner',
            sort: 'yop ASC, aa DESC',
        }, "should have correct args");
    });

    QUnit.test('search_read method', function (assert) {
        assert.expect(1);
        var query = rpc.buildQuery({
            model: 'partner',
            method: 'search_read',
            domain: ['a', '=', 1],
            fields: ['name'],
            limit: 32,
            offset: 2,
            orderBy: [{name: 'yop', asc: true}, {name: 'aa', asc: false}],
        });
        assert.deepEqual(query.params, {
            args: [['a', '=', 1], ['name'], 2, 32, 'yop ASC, aa DESC'],
            kwargs: {},
            method: 'search_read',
            model: 'partner'
        }, "should have correct args");
    });

    QUnit.test('read_group', function (assert) {
        assert.expect(2);

        var query = rpc.buildQuery({
            model: 'partner',
            method: 'read_group',
            domain: ['a', '=', 1],
            fields: ['name'],
            groupBy: ['product_id'],
            context: {abc: 'def'},
            lazy: true,
        });

        assert.deepEqual(query.params, {
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
        assert.equal(query.route, '/web/dataset/call_kw/partner/read_group',
            "should call correct route");
    });

    QUnit.test('read_group with kwargs', function (assert) {
        assert.expect(1);

        var query = rpc.buildQuery({
            model: 'partner',
            method: 'read_group',
            domain: ['a', '=', 1],
            fields: ['name'],
            groupBy: ['product_id'],
            lazy: false,
            kwargs: {context: {abc: 'def'}}
        });

        assert.deepEqual(query.params, {
            args: [],
            kwargs: {
                context: {abc: 'def'},
                domain: ['a', '=', 1],
                fields: ['name'],
                groupby: ['product_id'],
                lazy: false,
                orderby: false,
            },
            method: 'read_group',
            model: 'partner',
        }, "should have correct args");
    });

    QUnit.test('search_read with no domain, nor fields', function (assert) {
        assert.expect(2);
        var query = rpc.buildQuery({
            model: 'partner',
            route: '/web/dataset/search_read',
        });

        assert.deepEqual(query.params.domain, [], "should have [] as default domain");
        assert.strictEqual(query.params.fields, false, "should have false as default fields");
    });
});

});