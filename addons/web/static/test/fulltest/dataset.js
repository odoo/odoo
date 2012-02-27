$(document).ready(function () {
    var t = window.openerp.test_support;
    function context_(c) {
        return _.extend({ lang: 'en_US', tz: 'UTC', uid: 87539319 }, c);
    }

    t.module('Dataset shortcuts', 'data');
    t.test('read_index', function (openerp) {
        var ds = new openerp.web.DataSet(
            {session: openerp.connection}, 'some.model');
        ds.ids = [10, 20, 30, 40, 50];
        ds.index = 2;
        t.expect(ds.read_index(['a', 'b', 'c']), function (result) {
            strictEqual(result.method, 'read');
            strictEqual(result.model, 'some.model');

            strictEqual(result.args.length, 3);
            deepEqual(result.args[0], [30]);
            deepEqual(result.args[1], ['a', 'b', 'c']);
            deepEqual(result.args[2], context_());

            ok(_.isEmpty(result.kwargs));
        });
    });
    t.test('default_get', function (openerp) {
        var ds = new openerp.web.DataSet(
            {session: openerp.connection}, 'some.model', {foo: 'bar'});
        t.expect(ds.default_get(['a', 'b', 'c']), function (result) {
            strictEqual(result.method, 'default_get');
            strictEqual(result.model, 'some.model');

            strictEqual(result.args.length, 2);
            deepEqual(result.args[0], ['a', 'b', 'c']);
            console.log(result.args[1]);
            console.log(context_({foo: 'bar'}));
            deepEqual(result.args[1], context_({foo: 'bar'}));

            ok(_.isEmpty(result.kwargs));
        });
    });
    t.test('create', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'some.model');
        t.expect(ds.create({foo: 1, bar: 2}), function (r) {
            strictEqual(r.method, 'create');

            strictEqual(r.args.length, 2);
            deepEqual(r.args[0], {foo: 1, bar: 2});
            deepEqual(r.args[1], context_());

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('write', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'mod');
        t.expect(ds.write(42, {foo: 1}), function (r) {
            strictEqual(r.method, 'write');

            strictEqual(r.args.length, 3);
            deepEqual(r.args[0], [42]);
            deepEqual(r.args[1], {foo: 1});
            deepEqual(r.args[2], context_());

            ok(_.isEmpty(r.kwargs));
        });
        // FIXME: can't run multiple sessions in the same test(), fucks everything up
//        t.expect(ds.write(42, {foo: 1}, { context: {lang: 'bob'} }), function (r) {
//            strictEqual(r.args.length, 3);
//            strictEqual(r.args[2].lang, 'bob');
//        });
    });
    t.test('unlink', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'mod');
        t.expect(ds.unlink([42]), function (r) {
            strictEqual(r.method, 'unlink');

            strictEqual(r.args.length, 2);
            deepEqual(r.args[0], [42]);
            deepEqual(r.args[1], context_());

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('call', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'mod');
        t.expect(ds.call('frob', ['a', 'b', 42]), function (r) {
            strictEqual(r.method, 'frob');

            strictEqual(r.args.length, 3);
            deepEqual(r.args, ['a', 'b', 42]);

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('name_get', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'mod');
        t.expect(ds.name_get([1, 2], null), function (r) {
            strictEqual(r.method, 'name_get');

            strictEqual(r.args.length, 2);
            deepEqual(r.args[0], [1, 2]);
            deepEqual(r.args[1], context_());

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('name_search, name', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'mod');
        t.expect(ds.name_search('bob'), function (r) {
            strictEqual(r.method, 'name_search');

            strictEqual(r.args.length, 5);
            strictEqual(r.args[0], 'bob');
            // domain
            deepEqual(r.args[1], []);
            strictEqual(r.args[2], 'ilike');
            deepEqual(r.args[3], context_());
            strictEqual(r.args[4], 0);

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('name_search, domain & operator', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'mod');
        t.expect(ds.name_search(0, [['foo', '=', 3]], 'someop'), function (r) {
            strictEqual(r.method, 'name_search');

            strictEqual(r.args.length, 5);
            strictEqual(r.args[0], '');
            // domain
            deepEqual(r.args[1], [['foo', '=', 3]]);
            strictEqual(r.args[2], 'someop');
            deepEqual(r.args[3], context_());
            // limit
            strictEqual(r.args[4], 0);

            ok(_.isEmpty(r.kwargs));
        });
    });
    t.test('exec_workflow', function (openerp) {
        var ds = new openerp.web.DataSet({session: openerp.connection}, 'mod');
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
        var ds = new openerp.web.DataSetSearch({session: openerp.connection}, 'mod');
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
        var ds = new openerp.web.DataSetSearch({session: openerp.connection}, 'mod');
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
        domains: ['mary had a little lamb', 'bob the builder'],
        contexts: ['{a: b > c}']
    });
    t.test('Dataset', function (openerp) {
        var ds = new openerp.web.DataSetSearch(
            {session: openerp.connection}, 'mod');
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
    // TODO: non-literal domains and contexts basics
    // TODO: call_and_eval
    // TODO: name_search, non-literal domains

});
