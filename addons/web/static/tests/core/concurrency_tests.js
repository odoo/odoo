odoo.define('web.concurrency_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');

QUnit.module('core', {}, function () {

    QUnit.module('concurrency');


    QUnit.test('mutex: simple scheduling', function (assert) {
        assert.expect(6);

        var m = new concurrency.Mutex();

        var def1 = $.Deferred(),
            def2 = $.Deferred();

        var p1 = m.exec(function () { return def1; });
        var p2 = m.exec(function () { return def2; });

        assert.strictEqual(p1.state(), "pending");
        assert.strictEqual(p2.state(), "pending");

        def1.resolve();
        assert.strictEqual(p1.state(), "resolved");
        assert.strictEqual(p2.state(), "pending");

        def2.resolve();
        assert.strictEqual(p1.state(), "resolved");
        assert.strictEqual(p2.state(), "resolved");
    });

    QUnit.test('mutex: simpleScheduling2', function (assert) {
        assert.expect(6);

        var m = new concurrency.Mutex();

        var def1 = $.Deferred(),
            def2 = $.Deferred();

        var p1 = m.exec(function() { return def1; });
        var p2 = m.exec(function() { return def2; });

        assert.strictEqual(p1.state(), "pending");
        assert.strictEqual(p2.state(), "pending");
        def2.resolve();

        assert.strictEqual(p1.state(), "pending");
        assert.strictEqual(p2.state(), "pending");

        def1.resolve();
        assert.strictEqual(p1.state(), "resolved");
        assert.strictEqual(p2.state(), "resolved");
    });

    QUnit.test('mutex: reject', function (assert) {
        assert.expect(12);

        var m = new concurrency.Mutex();

        var def1 = $.Deferred(),
            def2 = $.Deferred(),
            def3 = $.Deferred();

        var p1 = m.exec(function() {return def1;});
        var p2 = m.exec(function() {return def2;});
        var p3 = m.exec(function() {return def3;});

        assert.strictEqual(p1.state(), "pending");
        assert.strictEqual(p2.state(), "pending");
        assert.strictEqual(p3.state(), "pending");

        def1.resolve();
        assert.strictEqual(p1.state(), "resolved");
        assert.strictEqual(p2.state(), "pending");
        assert.strictEqual(p3.state(), "pending");

        def2.reject();
        assert.strictEqual(p1.state(), "resolved");
        assert.strictEqual(p2.state(), "rejected");
        assert.strictEqual(p3.state(), "pending");

        def3.resolve();
        assert.strictEqual(p1.state(), "resolved");
        assert.strictEqual(p2.state(), "rejected");
        assert.strictEqual(p3.state(), "resolved");
    });

    QUnit.test('DropMisordered: resolve all correctly ordered, sync', function (assert) {
        assert.expect(1);

        var dm = new concurrency.DropMisordered(),
            flag = false;

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        var r1 = dm.add(d1),
            r2 = dm.add(d2);

        $.when(r1, r2).done(function () {
            flag = true;
        });

        d1.resolve();
        d2.resolve();

        assert.ok(flag);
    });

    QUnit.test("DropMisordered: don't resolve mis-ordered, sync", function (assert) {
        assert.expect(4);

        var dm = new concurrency.DropMisordered(),
            done1 = false,
            done2 = false,
            fail1 = false,
            fail2 = false;

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        dm.add(d1).done(function () { done1 = true; })
                    .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                    .fail(function () { fail2 = true; });

        d2.resolve();
        d1.resolve();

        // d1 is in limbo
        assert.ok(!done1);
        assert.ok(!fail1);

        // d2 is resolved
        assert.ok(done2);
        assert.ok(!fail2);
    });

    QUnit.test('DropMisordered: fail mis-ordered flag, sync', function (assert) {
        assert.expect(4);

        var dm = new concurrency.DropMisordered(true),
            done1 = false,
            done2 = false,
            fail1 = false,
            fail2 = false;

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        dm.add(d1).done(function () { done1 = true; })
                    .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                    .fail(function () { fail2 = true; });

        d2.resolve();
        d1.resolve();

        // d1 is in limbo
        assert.ok(!done1);
        assert.ok(fail1);

        // d2 is resolved
        assert.ok(done2);
        assert.ok(!fail2);

    });

    QUnit.test('DropMisordered: resolve all correctly ordered, async', function (assert) {
        var done = assert.async();
        assert.expect(1);

        var dm = new concurrency.DropMisordered();

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        var r1 = dm.add(d1),
            r2 = dm.add(d2);

        setTimeout(function () { d1.resolve(); }, 10);
        setTimeout(function () { d2.resolve(); }, 20);

        $.when(r1, r2).done(function () {
            assert.ok(true);
            done();
        });
    });

    QUnit.test("DropMisordered: don't resolve mis-ordered, async", function (assert) {
        var done = assert.async();
        assert.expect(4);

        var dm = new concurrency.DropMisordered(),
            done1 = false, done2 = false,
            fail1 = false, fail2 = false;

        var d1 = $.Deferred(), 
            d2 = $.Deferred();
        
        dm.add(d1).done(function () { done1 = true; })
                    .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                    .fail(function () { fail2 = true; });

        setTimeout(function () { d1.resolve(); }, 20);
        setTimeout(function () { d2.resolve(); }, 10);

        setTimeout(function () {
            // d1 is in limbo
            assert.ok(!done1);
            assert.ok(!fail1);

            // d2 is resolved
            assert.ok(done2);
            assert.ok(!fail2);
            done();
        }, 30);
    });

    QUnit.test('DropMisordered: fail mis-ordered flag, async', function (assert) {
        var done = assert.async();
        assert.expect(4);

        var dm = new concurrency.DropMisordered(true),
            done1 = false, done2 = false,
            fail1 = false, fail2 = false;

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        dm.add(d1).done(function () { done1 = true; })
                    .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                    .fail(function () { fail2 = true; });

        setTimeout(function () { d1.resolve(); }, 20);
        setTimeout(function () { d2.resolve(); }, 10);

        setTimeout(function () {
            // d1 is failed
            assert.ok(!done1);
            assert.ok(fail1);

            // d2 is resolved
            assert.ok(done2);
            assert.ok(!fail2);
            done();
        }, 30);
    });

});

});