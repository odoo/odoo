$(document).ready(function () {
    var openerp,
        create = function (o) {
            if (typeof Object.create === 'function') {
                return Object.create(o);
            }
            function Cls() {}
            Cls.prototype = o;
            return new Cls;
        };
    module('list-events', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.base.list(openerp);
        }
    });
    test('Simple event triggering', function () {
        var e = create(openerp.base.list.Events), passed = false;
        e.bind('foo', function () { passed = true; });
        e.trigger('foo');
        ok(passed);
    });
    test('Bind all', function () {
        var e = create(openerp.base.list.Events), event = null;
        e.bind(null, function (ev) { event = ev; });
        e.trigger('foo');
        strictEqual(event, 'foo');
    });
    test('Propagate trigger params', function () {
       var e = create(openerp.base.list.Events), p = false;
        e.bind(null, function (_, param) { p = param });
        e.trigger('foo', true);
        strictEqual(p, true)
    });
    test('Bind multiple callbacks', function () {
        var e = create(openerp.base.list.Events), count;
        e.bind('foo', function () { count++; })
         .bind('bar', function () { count++; })
         .bind(null, function () { count++; })
         .bind('foo', function () { count++; })
         .bind(null, function () { count++; })
         .bind(null, function () { count++; });

        count = 0;
        e.trigger('foo');
        strictEqual(count, 5);

        count = 0;
        e.trigger('bar');
        strictEqual(count, 4);

        count = 0;
        e.trigger('baz');
        strictEqual(count, 3);
    });
    test('Mixin events', function () {
        var cls = openerp.base.Class.extend({
            method: function () { this.trigger('e'); }
        });
        cls.include(openerp.base.list.Events);
        var instance = new cls, triggered = false;

        instance.bind('e', function () { triggered = true; });
        instance.method();

        ok(triggered);
    });
    test('Unbind all handlers', function () {
        var e = create(openerp.base.list.Events), passed = 0;
        e.bind('foo', function () { passed++; });
        e.trigger('foo');
        strictEqual(passed, 1);
        e.unbind('foo');
        e.trigger('foo');
        strictEqual(passed, 1);
    });
    test('Unbind one handler', function () {
        var e = create(openerp.base.list.Events), p1 = 0, p2 = 0,
            h1 = function () { p1++; }, h2 = function () { p2++; };
        e.bind('foo', h1);
        e.bind('foo', h2);
        e.trigger('foo');
        strictEqual(p1, 1);
        strictEqual(p2, 1);
        e.unbind('foo', h1);
        e.trigger('foo');
        strictEqual(p1, 1);
        strictEqual(p2, 2);
    });

    module('list-records', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.base.list(openerp);
        }
    });
    test('Basic record initialization', function () {
        var r = new openerp.base.list.Record({qux: 3});
        r.set('foo', 1);
        r.set('bar', 2);
        strictEqual(r.get('foo'), 1);
        strictEqual(r.get('bar'), 2);
        strictEqual(r.get('qux'), 3);
    });
    test('Change all the things', function () {
        var r = new openerp.base.list.Record(), changed = false, field;
        r.bind('change', function () { changed = true; });
        r.bind(null, function (e) { field = field || e.split(':')[1]});
        r.set('foo', 1);
        strictEqual(r.get('foo'), 1);
        ok(changed);
        strictEqual(field, 'foo');
    });
    test('Change single field', function () {
        var r = new openerp.base.list.Record(), changed = 0;
        r.bind('change:foo', function () { changed++; });
        r.set('foo', 1);
        r.set('bar', 1);
        strictEqual(r.get('foo'), 1);
        strictEqual(r.get('bar'), 1);
        strictEqual(changed, 1);
    });

    module('list-collections-degenerate', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.base.list(openerp);
        }
    });
    test('Fetch from collection', function () {
        var c = new openerp.base.list.Collection();
        strictEqual(c.length, 0);
        c.add({id: 1, value: 2});
        c.add({id: 2, value: 3});
        c.add({id: 3, value: 5});
        c.add({id: 4, value: 7});
        strictEqual(c.length, 4);
        var r = c.at(2), r2 = c.get(1);

        ok(r instanceof openerp.base.list.Record);
        strictEqual(r.get('id'), 3);
        strictEqual(r.get('value'), 5);

        ok(r2 instanceof openerp.base.list.Record);
        strictEqual(r2.get('id'), 1);
        strictEqual(r2.get('value'), 2);
    });
    test('Add at index', function () {
        var c = new openerp.base.list.Collection([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}
        ]);
        strictEqual(c.at(1).get('value'), 10);
        equal(c.at(3), undefined);
        c.add({id:4, value: 55}, {at: 1});
        strictEqual(c.at(1).get('value'), 55);
        strictEqual(c.at(3).get('value'), 20);
    });
    test('Remove record', function () {
        var c = new openerp.base.list.Collection([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}
        ]);
        var record = c.get(2);
        strictEqual(c.length, 3);
        c.remove(record);
        strictEqual(c.length, 2);
        equal(c.get(2), undefined);
        strictEqual(c.at(1).get('value'), 20);
    });
    test('Reset', function () {
        var event, obj, c = new openerp.base.list.Collection([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}
        ]);
        c.bind(null, function (e, instance) { event = e; obj = instance; });
        c.reset();
        strictEqual(c.length, 0);
        strictEqual(event, 'reset');
        strictEqual(obj, c);
        c.add([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}
        ]);
        c.reset([{id: 42, value: 55}]);
        strictEqual(c.length, 1);
        strictEqual(c.get(42).get('value'), 55);
    });

    test('Events propagation', function () {
        var values = [];
        var c = new openerp.base.list.Collection([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}
        ]);
        c.bind('change:value', function (e, record, value) {
            values.push(value);
        });
        c.get(1).set('value', 6);
        c.get(2).set('value', 11);
        c.get(3).set('value', 21);
        deepEqual(values, [6, 11, 21]);
    });
    test('BTree', function () {
        var root = new openerp.base.list.Collection(),
            c = root.proxy('admin'),
            total = 0;
        c.add({id: 1, name: "Administrator", login: 'admin'});
        c.add({id: 3, name: "Demo", login: 'demo'});
        root.bind('change:wealth', function () {
            total = (root.get(1).get('wealth') || 0) + (root.get(3).get('wealth') || 0);
        });

        strictEqual(total, 0);
        c.at(0).set('wealth', 42);
        strictEqual(total, 42);
        c.at(1).set('wealth', 5);
        strictEqual(total, 47);
    });

    module('list-hofs', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.base.list(openerp);
        }
    });
    test('each, degenerate', function () {
        var c = new openerp.base.list.Collection([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}
        ]), ids = [];
        c.each(function (record) {
            ids.push(record.get('id'));
        });
        deepEqual(
            ids, [1, 2, 3],
            'degenerate collections should be iterated in record order');
    });
    test('each, deep', function () {
        var root = new openerp.base.list.Collection(),
            ids = [];
        root.proxy('foo').add([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}]);
        root.proxy('bar').add([
            {id: 10, value: 5},
            {id: 20, value: 10},
            {id: 30, value: 20}]);
        root.each(function (record) {
            ids.push(record.get('id'));
        });
        // No contract on sub-collection iteration order (for now anyway)
        ids.sort(function (a, b) { return a - b; });
        deepEqual(
            ids, [1, 2, 3, 10, 20, 30],
            'tree collections should be deeply iterated');
    });
    test('map, degenerate', function () {
        var c = new openerp.base.list.Collection([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}
        ]);
        var ids = c.map(function (record) {
            return record.get('id');
        });
        deepEqual(
            ids, [1, 2, 3],
            'degenerate collections should be iterated in record order');
    });
    test('map, deep', function () {
        var root = new openerp.base.list.Collection();
        root.proxy('foo').add([
            {id: 1, value: 5},
            {id: 2, value: 10},
            {id: 3, value: 20}]);
        root.proxy('bar').add([
            {id: 10, value: 5},
            {id: 20, value: 10},
            {id: 30, value: 20}]);
        var ids = root.map(function (record) {
            return record.get('id');
        });
        // No contract on sub-collection iteration order (for now anyway)
        ids.sort(function (a, b) { return a - b; });
        deepEqual(
            ids, [1, 2, 3, 10, 20, 30],
            'tree collections should be deeply iterated');
    });
});
