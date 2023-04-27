odoo.define('web.concurrency_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var testUtils = require('web.test_utils');

var makeTestPromise = testUtils.makeTestPromise;
var makeTestPromiseWithAssert = testUtils.makeTestPromiseWithAssert;

QUnit.module('core', {}, function () {

    QUnit.module('concurrency');

    QUnit.test('mutex: simple scheduling', async function (assert) {
        assert.expect(5);
        var mutex = new concurrency.Mutex();

        var prom1 = makeTestPromiseWithAssert(assert, 'prom1');
        var prom2 = makeTestPromiseWithAssert(assert, 'prom2');

        mutex.exec(function () { return prom1; });
        mutex.exec(function () { return prom2; });

        assert.verifySteps([]);

        await prom1.resolve();

        assert.verifySteps(['ok prom1']);

        await prom2.resolve();

        assert.verifySteps(['ok prom2']);
    });

    QUnit.test('mutex: simpleScheduling2', async function (assert) {
        assert.expect(5);
        var mutex = new concurrency.Mutex();

        var prom1 = makeTestPromiseWithAssert(assert, 'prom1');
        var prom2 = makeTestPromiseWithAssert(assert, 'prom2');

        mutex.exec(function () { return prom1; });
        mutex.exec(function () { return prom2; });

        assert.verifySteps([]);

        await prom2.resolve();

        assert.verifySteps(['ok prom2']);

        await prom1.resolve();

        assert.verifySteps(['ok prom1']);
    });

    QUnit.test('mutex: reject', async function (assert) {
        assert.expect(7);
        var mutex = new concurrency.Mutex();

        var prom1 = makeTestPromiseWithAssert(assert, 'prom1');
        var prom2 = makeTestPromiseWithAssert(assert, 'prom2');
        var prom3 = makeTestPromiseWithAssert(assert, 'prom3');

        mutex.exec(function () { return prom1; }).catch(function () {});
        mutex.exec(function () { return prom2; }).catch(function () {});
        mutex.exec(function () { return prom3; }).catch(function () {});

        assert.verifySteps([]);

        prom1.resolve();
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['ok prom1']);

        prom2.catch(function () {
           assert.verifySteps(['ko prom2']);
        });
        prom2.reject({name: "sdkjfmqsjdfmsjkdfkljsdq"});
        await testUtils.nextMicrotaskTick();

        prom3.resolve();
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['ok prom3']);
    });

    QUnit.test('mutex: getUnlockedDef checks', async function (assert) {
        assert.expect(9);

        var mutex = new concurrency.Mutex();

        var prom1 = makeTestPromiseWithAssert(assert, 'prom1');
        var prom2 = makeTestPromiseWithAssert(assert, 'prom2');

        mutex.getUnlockedDef().then(function () {
            assert.step('mutex unlocked (1)');
        });

        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['mutex unlocked (1)']);

        mutex.exec(function () { return prom1; });
        await testUtils.nextMicrotaskTick();

        mutex.getUnlockedDef().then(function () {
            assert.step('mutex unlocked (2)');
        });

        assert.verifySteps([]);

        mutex.exec(function () { return prom2; });
        await testUtils.nextMicrotaskTick();

        assert.verifySteps([]);

        await prom1.resolve();

        assert.verifySteps(['ok prom1']);

        prom2.resolve();
        await testUtils.nextTick();

        assert.verifySteps(['ok prom2', 'mutex unlocked (2)']);
    });

    QUnit.test('DropPrevious: basic usecase', async function (assert) {
        assert.expect(4);

        var dp = new concurrency.DropPrevious();

        var prom1 = makeTestPromise(assert, 'prom1');
        var prom2 = makeTestPromise(assert, 'prom2');

        dp.add(prom1).then(() => assert.step('should not go here'))
                     .catch(()=> assert.step("rejected dp1"));
        dp.add(prom2).then(() => assert.step("ok dp2"));

        await testUtils.nextMicrotaskTick();
        assert.verifySteps(['rejected dp1']);

        prom2.resolve();
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['ok dp2']);
    });

    QUnit.test('DropPrevious: resolve first before last', async function (assert) {
        assert.expect(4);

        var dp = new concurrency.DropPrevious();

        var prom1 = makeTestPromise(assert, 'prom1');
        var prom2 = makeTestPromise(assert, 'prom2');

        dp.add(prom1).then(() => assert.step('should not go here'))
                     .catch(()=> assert.step("rejected dp1"));
        dp.add(prom2).then(() => assert.step("ok dp2"));


        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['rejected dp1']);

        prom1.resolve();
        prom2.resolve();
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['ok dp2']);
    });

    QUnit.test('DropMisordered: resolve all correctly ordered, sync', async function (assert) {
        assert.expect(1);

        var dm = new concurrency.DropMisordered(),
            flag = false;

        var d1 = makeTestPromise();
        var d2 = makeTestPromise();

        var r1 = dm.add(d1),
            r2 = dm.add(d2);

        Promise.all([r1, r2]).then(function () {
            flag = true;
        });

        d1.resolve();
        d2.resolve();
        await testUtils.nextTick();

        assert.ok(flag);
    });

    QUnit.test("DropMisordered: don't resolve mis-ordered, sync", async function (assert) {
        assert.expect(4);

        var dm = new concurrency.DropMisordered(),
            done1 = false,
            done2 = false,
            fail1 = false,
            fail2 = false;

        var d1 = makeTestPromise();
        var d2 = makeTestPromise();

        dm.add(d1).then(function () { done1 = true; })
                    .catch(function () { fail1 = true; });
        dm.add(d2).then(function () { done2 = true; })
                    .catch(function () { fail2 = true; });

        d2.resolve();
        d1.resolve();
        await testUtils.nextMicrotaskTick();

        // d1 is in limbo
        assert.ok(!done1);
        assert.ok(!fail1);

        // d2 is fulfilled
        assert.ok(done2);
        assert.ok(!fail2);
    });

    QUnit.test('DropMisordered: fail mis-ordered flag, sync', async function (assert) {
        assert.expect(4);

        var dm = new concurrency.DropMisordered(true/* failMisordered */),
            done1 = false,
            done2 = false,
            fail1 = false,
            fail2 = false;

        var d1 = makeTestPromise();
        var d2 = makeTestPromise();

        dm.add(d1).then(function () { done1 = true; })
                    .catch(function () { fail1 = true; });
        dm.add(d2).then(function () { done2 = true; })
                    .catch(function () { fail2 = true; });

        d2.resolve();
        d1.resolve();
        await testUtils.nextMicrotaskTick();

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

        var d1 = makeTestPromise();
        var d2 = makeTestPromise();

        var r1 = dm.add(d1),
            r2 = dm.add(d2);

        setTimeout(function () { d1.resolve(); }, 10);
        setTimeout(function () { d2.resolve(); }, 20);

        Promise.all([r1, r2]).then(function () {
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

        var d1 = makeTestPromise();
        var d2 = makeTestPromise();

        dm.add(d1).then(function () { done1 = true; })
                    .catch(function () { fail1 = true; });
        dm.add(d2).then(function () { done2 = true; })
                    .catch(function () { fail2 = true; });

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

        var d1 = makeTestPromise();
        var d2 = makeTestPromise();

        dm.add(d1).then(function () { done1 = true; })
                    .catch(function () { fail1 = true; });
        dm.add(d2).then(function () { done2 = true; })
                    .catch(function () { fail2 = true; });

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

    QUnit.test('MutexedDropPrevious: simple', async function (assert) {
        assert.expect(5);

        var m = new concurrency.MutexedDropPrevious();
        var d1 = makeTestPromise();

        d1.then(function () {
            assert.step("d1 resolved");
        });
        m.exec(function () { return d1; }).then(function (result) {
            assert.step("p1 done");
            assert.strictEqual(result, 'd1');
        });

        assert.verifySteps([]);
        d1.resolve('d1');
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(["d1 resolved","p1 done"]);
    });

    QUnit.test('MutexedDropPrevious: d2 arrives after d1 resolution', async function (assert) {
        assert.expect(8);

        var m = new concurrency.MutexedDropPrevious();
        var d1 = makeTestPromiseWithAssert(assert, 'd1');

        m.exec(function () { return d1; }).then(function () {
            assert.step("p1 resolved");
        });

        assert.verifySteps([]);
        d1.resolve('d1');
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['ok d1','p1 resolved']);

        var d2 = makeTestPromiseWithAssert(assert, 'd2');
        m.exec(function () { return d2; }).then(function () {
            assert.step("p2 resolved");
        });

        assert.verifySteps([]);
        d2.resolve('d2');
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['ok d2','p2 resolved']);
    });

    QUnit.test('MutexedDropPrevious: p1 does not return a deferred', async function (assert) {
        assert.expect(7);

        var m = new concurrency.MutexedDropPrevious();

        m.exec(function () { return 42; }).then(function () {
            assert.step("p1 resolved");
        });

        assert.verifySteps([]);
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['p1 resolved']);

        var d2 = makeTestPromiseWithAssert(assert, 'd2');
        m.exec(function () { return d2; }).then(function () {
            assert.step("p2 resolved");
        });

        assert.verifySteps([]);
        d2.resolve('d2');
        await testUtils.nextMicrotaskTick();
        assert.verifySteps(['ok d2','p2 resolved']);
    });

    QUnit.test('MutexedDropPrevious: p2 arrives before p1 resolution', async function (assert) {
        assert.expect(8);

        var m = new concurrency.MutexedDropPrevious();
        var d1 = makeTestPromiseWithAssert(assert, 'd1');

        m.exec(function () { return d1; }).catch(function () {
            assert.step("p1 rejected");
        });
        assert.verifySteps([]);

        var d2 = makeTestPromiseWithAssert(assert, 'd2');
        m.exec(function () { return d2; }).then(function () {
            assert.step("p2 resolved");
        });

        assert.verifySteps([]);
        d1.resolve('d1');
        await testUtils.nextMicrotaskTick();
        assert.verifySteps(['p1 rejected', 'ok d1']);

        d2.resolve('d2');
        await testUtils.nextMicrotaskTick();
        assert.verifySteps(['ok d2', 'p2 resolved']);
    });

    QUnit.test('MutexedDropPrevious: 3 arrives before 2 initialization', async function (assert) {
        assert.expect(10);
        var m = new concurrency.MutexedDropPrevious();

        var d1 = makeTestPromiseWithAssert(assert, 'd1');
        var d3 = makeTestPromiseWithAssert(assert, 'd3');

        m.exec(function () { return d1; }).catch(function () {
            assert.step('p1 rejected');
        });

        m.exec(function () {
            assert.ok(false, "should not execute this function");
        }).catch(function () {
            assert.step('p2 rejected');
        });

        m.exec(function () { return d3; }).then(function (result) {
            assert.strictEqual(result, 'd3');
            assert.step('p3 resolved');
        });

        assert.verifySteps([]);

        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['p1 rejected', 'p2 rejected']);

        d1.resolve('d1');
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['ok d1']);

        d3.resolve('d3');
        await testUtils.nextTick();


        assert.verifySteps(['ok d3','p3 resolved']);
    });

    QUnit.test('MutexedDropPrevious: 3 arrives after 2 initialization', async function (assert) {
        assert.expect(15);
        var m = new concurrency.MutexedDropPrevious();

        var d1 = makeTestPromiseWithAssert(assert, 'd1');
        var d2 = makeTestPromiseWithAssert(assert, 'd2');
        var d3 = makeTestPromiseWithAssert(assert, 'd3');

        m.exec(function () {
            assert.step('execute d1');
            return d1;
        }).catch(function () {
            assert.step('p1 rejected');
        });

        m.exec(function () {
            assert.step('execute d2');
            return d2;
        }).catch(function () {
            assert.step('p2 rejected');
        });

        assert.verifySteps(['execute d1']);

        await testUtils.nextMicrotaskTick();
        assert.verifySteps(['p1 rejected']);

        d1.resolve('d1');
        await testUtils.nextMicrotaskTick();

        assert.verifySteps(['ok d1', 'execute d2']);

        m.exec(function () {
            assert.step('execute d3');
            return d3;
        }).then(function () {
            assert.step('p3 resolved');
        });
        await testUtils.nextMicrotaskTick();
        assert.verifySteps(['p2 rejected']);

        d2.resolve();
        await testUtils.nextMicrotaskTick();
        assert.verifySteps(['ok d2', 'execute d3']);

        d3.resolve();
        await testUtils.nextTick();
        assert.verifySteps(['ok d3', 'p3 resolved']);

     });

    QUnit.test('MutexedDropPrevious: 2 in then of 1 with 3', async function (assert) {
        assert.expect(9);

        var m = new concurrency.MutexedDropPrevious();

        var d1 = makeTestPromiseWithAssert(assert, 'd1');
        var d2 = makeTestPromiseWithAssert(assert, 'd2');
        var d3 = makeTestPromiseWithAssert(assert, 'd3');
        var p3;

        m.exec(function () { return d1; })
            .catch(function () {
                assert.step('p1 rejected');
                p3 = m.exec(function () {
                    return d3;
                }).then(function () {
                    assert.step('p3 resolved');
                });
                return p3;
            });

        await testUtils.nextTick();
        assert.verifySteps([]);

        m.exec(function () {
            assert.ok(false, 'should not execute this function');
            return d2;
        }).catch(function () {
            assert.step('p2 rejected');
        });

        await testUtils.nextTick();
        assert.verifySteps(['p1 rejected', 'p2 rejected']);

        d1.resolve('d1');
        await testUtils.nextTick();

        assert.verifySteps(['ok d1']);

        d3.resolve('d3');
        await testUtils.nextTick();

        assert.verifySteps(['ok d3', 'p3 resolved']);
    });

});

});
