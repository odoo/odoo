openerp.testing.section('list.events', {
    dependencies: ['web.list']
}, function (test) {
    var create = function (o) {
        if (typeof Object.create === 'function') {
            return Object.create(o);
        }
        function Cls() {}
        Cls.prototype = o;
        return new Cls();
    };
    test('Simple event triggering', function (instance) {
        var e = create(instance.web.list.Events), passed = false;
        e.bind('foo', function () { passed = true; });
        e.trigger('foo');
        ok(passed);
    });
    test('Bind all', function (instance) {
        var e = create(instance.web.list.Events), event = null;
        e.bind(null, function (ev) { event = ev; });
        e.trigger('foo');
        strictEqual(event, 'foo');
    });
    test('Propagate trigger params', function (instance) {
       var e = create(instance.web.list.Events), p = false;
        e.bind(null, function (_, param) { p = param; });
        e.trigger('foo', true);
        strictEqual(p, true);
    });
    test('Bind multiple callbacks', function (instance) {
        var e = create(instance.web.list.Events), count;
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
    test('Mixin events', function (instance) {
        var cls = instance.web.Class.extend({
            method: function () { this.trigger('e'); }
        });
        cls.include(instance.web.list.Events);
        var i = new cls(), triggered = false;

        i.bind('e', function () { triggered = true; });
        i.method();

        ok(triggered);
    });
    test('Unbind all handlers', function (instance) {
        var e = create(instance.web.list.Events), passed = 0;
        e.bind('foo', function () { passed++; });
        e.trigger('foo');
        strictEqual(passed, 1);
        e.unbind('foo');
        e.trigger('foo');
        strictEqual(passed, 1);
    });
    test('Unbind one handler', function (instance) {
        var e = create(instance.web.list.Events), p1 = 0, p2 = 0,
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
});
openerp.testing.section('list.records', {
    dependencies: ['web.list']
}, function (test) {
    test('Basic record initialization', function (instance) {
        var r = new instance.web.list.Record({qux: 3});
        r.set('foo', 1);
        r.set('bar', 2);
        strictEqual(r.get('foo'), 1);
        strictEqual(r.get('bar'), 2);
        strictEqual(r.get('qux'), 3);
    });
    test('Change all the things', function (instance) {
        var r = new instance.web.list.Record(), changed = false, field;
        r.bind('change', function () { changed = true; });
        r.bind(null, function (e) { field = field || e.split(':')[1]; });
        r.set('foo', 1);
        strictEqual(r.get('foo'), 1);
        ok(changed);
        strictEqual(field, 'foo');
    });
    test('Change single field', function (instance) {
        var r = new instance.web.list.Record(), changed = 0;
        r.bind('change:foo', function () { changed++; });
        r.set('foo', 1);
        r.set('bar', 1);
        strictEqual(r.get('foo'), 1);
        strictEqual(r.get('bar'), 1);
        strictEqual(changed, 1);
    });
});
openerp.testing.section('list.collections', {
    dependencies: ['web.list']
}, function (test) {
    test('degenerate-fetch', function (instance) {
        var c = new instance.web.list.Collection();
        strictEqual(c.length, 0);
        c.add({id: 1, value: 2});
        c.add({id: 2, value: 3});
        c.add({id: 3, value: 5});
        c.add({id: 4, value: 7});
        strictEqual(c.length, 4);
        var r = c.at(2), r2 = c.get(1);

        ok(r instanceof instance.web.list.Record);
        strictEqual(r.get('id'), 3);
        strictEqual(r.get('value'), 5);

        ok(r2 instanceof instance.web.list.Record);
        strictEqual(r2.get('id'), 1);
        strictEqual(r2.get('value'), 2);
    });
    test('degenerate-indexed-add', function (instance) {
        var c = new instance.web.list.Collection([
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
    test('degenerate-remove', function (instance) {
        var c = new instance.web.list.Collection([
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
    test('degenerate-remove-bound', function (instance) {
        var changed = false,
            c = new instance.web.list.Collection([ {id: 1, value: 5} ]);
        c.bind('change', function () { changed = true; });
        var record = c.get(1);
        c.remove(record);
        record.set('value', 42);
        ok(!changed, 'removed records should not trigger events in their ' +
                     'parent collection');
    });
    test('degenerate-reset', function (instance) {
        var event, obj, c = new instance.web.list.Collection([
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
    test('degenerate-reset-bound', function (instance) {
        var changed = false,
            c = new instance.web.list.Collection([ {id: 1, value: 5} ]);
        c.bind('change', function () { changed = true; });
        var record = c.get(1);
        c.reset();
        record.set('value', 42);
        ok(!changed, 'removed records should not trigger events in their ' +
                     'parent collection');
    });

    test('degenerate-propagations', function (instance) {
        var values = [];
        var c = new instance.web.list.Collection([
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
    test('BTree', function (instance) {
        var root = new instance.web.list.Collection(),
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
    test('degenerate-successor', function (instance) {
        var root = new instance.web.list.Collection([
            {id: 1, value: 1},
            {id: 2, value: 2},
            {id: 3, value: 3},
            {id: 4, value: 5},
            {id: 5, value: 8}
        ]);

        deepEqual(root.succ(root.at(2)).attributes,
                  root.at(3).attributes,
                  "should return the record at (index + 1) from the pivot");
        equal(root.succ(root.at(4)), null,
              "should return null as successor to last record");
        deepEqual(root.succ(root.at(4), {wraparound: true}).attributes,
                  root.at(0).attributes,
                  "should return index 0 as successor to last record if" +
                  " wraparound is set");
        deepEqual(root.succ(root.at(2), {wraparound: true}).attributes,
                  root.at(3).attributes,
                  "wraparound should have no effect if not succ(last_record)");
    });
    test('successor', function (instance) {
        var root = new instance.web.list.Collection();
        root.proxy('first').add([{id: 1, value: 1}, {id: 2, value: 2}]);
        root.proxy('second').add([{id: 3, value: 3}, {id: 4, value: 5}]);
        root.proxy('third').add([{id: 5, value: 8}, {id: 6, value: 13}]);

        deepEqual(root.succ(root.get(3)).attributes,
                  root.get(4).attributes,
                  "should get successor");
        equal(root.succ(root.get(4)),
              null,
              "successors do not cross collections");
        deepEqual(root.succ(root.get(4), {wraparound: true}).attributes,
                  root.get(3).attributes,
                  "should wraparound within a collection");
    });
    test('degenerate-predecessor', function (instance) {
        var root = new instance.web.list.Collection([
            {id: 1, value: 1},
            {id: 2, value: 2},
            {id: 3, value: 3},
            {id: 4, value: 5},
            {id: 5, value: 8}
        ]);

        deepEqual(root.pred(root.at(2)).attributes,
                  root.at(1).attributes,
                  "should return the record at (index - 1) from the pivot");
        equal(root.pred(root.at(0)), null,
              "should return null as predecessor to first record");
        deepEqual(root.pred(root.at(0), {wraparound: true}).attributes,
                  root.at(4).attributes,
                  "should return last record as predecessor to first record" +
                  " if wraparound is set");
        deepEqual(root.pred(root.at(1), {wraparound: true}).attributes,
                  root.at(0).attributes,
                  "wraparound should have no effect if not pred(first_record)");
    });
    test('predecessor', function (instance) {
        var root = new instance.web.list.Collection();
        root.proxy('first').add([{id: 1, value: 1}, {id: 2, value: 2}]);
        root.proxy('second').add([{id: 3, value: 3}, {id: 4, value: 5}]);
        root.proxy('third').add([{id: 5, value: 8}, {id: 6, value: 13}]);

        deepEqual(root.pred(root.get(4)).attributes,
                  root.get(3).attributes,
                  "should get predecessor");
        equal(root.pred(root.get(3)),
              null,
              "predecessor do not cross collections");
        deepEqual(root.pred(root.get(3), {wraparound: true}).attributes,
                  root.get(4).attributes,
                  "should wraparound within a collection");
    });
});
openerp.testing.section('list.collections.hom', {
    dependencies: ['web.list']
}, function (test) {
    test('each, degenerate', function (instance) {
        var c = new instance.web.list.Collection([
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
    test('each, deep', function (instance) {
        var root = new instance.web.list.Collection(),
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
    test('map, degenerate', function (instance) {
        var c = new instance.web.list.Collection([
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
    test('map, deep', function (instance) {
        var root = new instance.web.list.Collection();
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
openerp.testing.section('list.collection.weirdoes', {
    dependencies: ['web.list']
}, function (test) {
    test('set-from-noid', function (instance) {
        var root = new instance.web.list.Collection();
        root.add({v: 3});
        root.at(0).set('id', 42);
        var record = root.get(42);
        equal(root.length, 1);
        equal(record.get('v'), 3, "should have fetched the original record");
    });
    test('set-from-previd', function (instance) {
        var root = new instance.web.list.Collection();
        root.add({id: 1, v: 2});
        root.get(1).set('id', 42);
        var record = root.get(42);
        equal(root.length, 1);
        equal(record.get('v'), 2, "should have fetched the original record");
    });
});
