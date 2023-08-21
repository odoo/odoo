/** @odoo-module **/

import concurrency from "@web/legacy/js/core/concurrency";
import { Mutex } from "@web/core/utils/concurrency";
import testUtils from "@web/../tests/legacy/helpers/test_utils";

var makeTestPromise = testUtils.makeTestPromise;
var makeTestPromiseWithAssert = testUtils.makeTestPromiseWithAssert;

QUnit.module('core', {}, function () {

    QUnit.module('concurrency');

    QUnit.test('mutex: simple scheduling', async function (assert) {
        assert.expect(5);
        var mutex = new Mutex();

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
        var mutex = new Mutex();

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
        var mutex = new Mutex();

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

        var mutex = new Mutex();

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

    QUnit.test('mutex: error and getUnlockedDef', async function (assert) {
        const mutex = new Mutex();
        mutex.exec(async () => {
            await Promise.resolve();
            throw new Error("boom");
        }).catch(() => assert.step("prom rejected"));
        await testUtils.nextTick();
        assert.verifySteps(['prom rejected']);

        mutex.getUnlockedDef().then(function () {
            assert.step('mutex unlocked');
        });
        await testUtils.nextMicrotaskTick();
        assert.verifySteps(['mutex unlocked']);
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
