$(document).ready(function () {
    var t = window.openerp.test_support;
    function context_(c) {
        return _.extend({ lang: 'en_US', tz: 'UTC', uid: 87539319 }, c);
    }

    t.module('Dataset shortcuts', 'data');
    t.test('read_index', function (openerp) {
        var ds = new openerp.web.DataSet(
            {session: openerp.session}, 'some.model');
        ds.ids = [10, 20, 30, 40, 50];
        ds.index = 2;
        t.expect(ds.read_index(['a', 'b', 'c']), function (result) {
            strictEqual(result.method, 'read');
            strictEqual(result.model, 'some.model');

            strictEqual(result.args.length, 2);
            deepEqual(result.args[0], [30]);

            deepEqual(result.kwargs, {
                context: context_()
            });
        });
    });
    t.test('default_get', function (openerp) {
        var ds = new openerp.web.DataSet(
            {session: openerp.session}, 'some.model', {foo: 'bar'});
        t.expect(ds.default_get(['a', 'b', 'c']), function (result) {
            strictEqual(result.method, 'default_get');
            strictEqual(result.model, 'some.model');

            strictEqual(result.args.length, 1);
            deepEqual(result.args[0], ['a', 'b', 'c']);

            deepEqual(result.kwargs, {
                context: context_({foo: 'bar'})
            });
        });
    });
    t.test('create', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.session}, 'some.model');
        t.expect(ds.create({foo: 1, bar: 2}), function (r) {
            strictEqual(r.method, 'create');

            strictEqual(r.args.length, 1);
            deepEqual(r.args[0], {foo: 1, bar: 2});

            deepEqual(r.kwargs, {
                context: context_()
            });
        });
    });
    t.test('write', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.session}, 'mod');
        t.expect(ds.write(42, {foo: 1}), function (r) {
            strictEqual(r.method, 'write');

            strictEqual(r.args.length, 2);
            deepEqual(r.args[0], [42]);
            deepEqual(r.args[1], {foo: 1});
            deepEqual(r.kwargs, {
                context: context_()
            });
        });
        // FIXME: can't run multiple sessions in the same test(), fucks everything up
//        t.expect(ds.write(42, {foo: 1}, { context: {lang: 'bob'} }), function (r) {
//            strictEqual(r.args.length, 3);
//            strictEqual(r.args[2].lang, 'bob');
//        });
    });
    t.test('unlink', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.session}, 'mod');
        t.expect(ds.unlink([42]), function (r) {
            strictEqual(r.method, 'unlink');

            strictEqual(r.args.length, 1);
            deepEqual(r.args[0], [42]);
            deepEqual(r.kwargs, {
                context: context_()
            });
        });
    });
    t.test('call', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.session}, 'mod');
        t.expect(ds.call('frob', ['a', 'b', 42]), function (r) {
            strictEqual(r.method, 'frob');

            strictEqual(r.args.length, 3);
            deepEqual(r.args, ['a', 'b', 42]);

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('name_get', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.session}, 'mod');
        t.expect(ds.name_get([1, 2], null), function (r) {
            strictEqual(r.method, 'name_get');

            strictEqual(r.args.length, 1);
            deepEqual(r.args[0], [1, 2]);
            deepEqual(r.kwargs, {
                context: context_()
            });
        });
    });
    t.test('name_search, name', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.session}, 'mod');
        t.expect(ds.name_search('bob'), function (r) {
            strictEqual(r.method, 'name_search');

            strictEqual(r.args.length, 0);
            deepEqual(r.kwargs, {
                name: 'bob',
                args: false,
                operator: 'ilike',
                context: context_(),
                limit: 0
            });
        });
    });
    t.test('name_search, domain & operator', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.session}, 'mod');
        t.expect(ds.name_search(0, [['foo', '=', 3]], 'someop'), function (r) {
            strictEqual(r.method, 'name_search');

            strictEqual(r.args.length, 0);
            deepEqual(r.kwargs, {
                name: '',
                args: [['foo', '=', 3]],
                operator: 'someop',
                context: context_(),
                limit: 0
            });
        });
    });
    t.test('exec_workflow', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.session}, 'mod');
        t.expect(ds.exec_workflow(42, 'foo'), function (r) {
            strictEqual(r['service'], 'object');
            strictEqual(r.method, 'exec_workflow');

            // db, id, password, model, method, id
            strictEqual(r.args.length, 6);
            strictEqual(r.args[4], 'foo');
            strictEqual(r.args[5], 42);
        });
    });

    t.test('DataSetSearch#read_slice', function (openerp) {
        var ds = new openerp.web.DataSetSearch({session: openerp.session}, 'mod');
        t.expect(ds.read_slice(['foo', 'bar'], {
            domain: [['foo', '>', 42], ['qux', '=', 'grault']],
            context: {peewee: 'herman'},
            offset: 160,
            limit: 80
        }), function (r) {
            strictEqual(r.method, 'search');

            strictEqual(r.args.length, 5);
            deepEqual(r.args[0], [['foo', '>', 42], ['qux', '=', 'grault']]);
            strictEqual(r.args[1], 160);
            strictEqual(r.args[2], 80);
            strictEqual(r.args[3], false);
            strictEqual(r.args[4].peewee, 'herman');

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('DataSetSearch#read_slice sorted', function (openerp) {
        var ds = new openerp.web.DataSetSearch({session: openerp.session}, 'mod');
        ds.sort('foo');
        ds.sort('foo');
        ds.sort('bar');
        t.expect(ds.read_slice(['foo', 'bar'], { }), function (r) {
            strictEqual(r.method, 'search');

            strictEqual(r.args.length, 5);
            deepEqual(r.args[0], []);
            strictEqual(r.args[1], 0);
            strictEqual(r.args[2], false);
            strictEqual(r.args[3], 'bar ASC, foo DESC');
            deepEqual(r.args[4], context_());

            ok(_.isEmpty(r.kwargs));
        });
    });

    t.module('Nonliterals', 'data', {
        domains: [
            "[('model_id', '=', parent.model)]",
            "[('product_id','=',product_id)]"
        ],
        contexts: ['{a: b > c}']
    });
    t.test('Dataset', function (openerp) {
        var ds = new openerp.web.DataSetSearch(
            {session: openerp.session}, 'mod');
        var c = new openerp.web.CompoundContext(
            {a: 'foo', b: 3, c: 5}, openerp.contexts[0]);
        t.expect(ds.read_slice(['foo', 'bar'], {
            context: c
        }), function (r) {
            strictEqual(r.method, 'search');

            deepEqual(r.args[4], context_({
                foo: false,
                a: 'foo',
                b: 3,
                c: 5
            }));

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('name_search', function (openerp) {
        var eval_context = {
            active_id: 42,
            active_ids: [42],
            active_model: 'mod',
            parent: {model: 'qux'}
        };
        var ds = new openerp.web.DataSet(
            {session: openerp.session}, 'mod',
             new openerp.web.CompoundContext({})
                 .set_eval_context(eval_context));
        var domain = new openerp.web.CompoundDomain(openerp.domains[0])
                .set_eval_context(eval_context);
        t.expect(ds.name_search('foo', domain, 'ilike', 0), function (r) {
            strictEqual(r.method, 'name_search');

            strictEqual(r.args.length, 0);
            deepEqual(r.kwargs, {
                name: 'foo',
                args: [['model_id', '=', 'qux']],
                operator: 'ilike',
                context: context_(),
                limit: 0
            });
        });
    });
});
