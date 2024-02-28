/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';
import { nextTick } from '@mail/utils/utils';

QUnit.module('mail', {}, function () {
QUnit.module('utils', {}, function () {
QUnit.module('throttle', {}, function () {
QUnit.module('throttle_tests.js', {});

QUnit.test('single call', async function (assert) {
    assert.expect(3);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });
    let hasInvokedFunc = false;
    const throttle = messaging.models['Throttle'].insert({
        func: () => hasInvokedFunc = true,
        qunitTestOwner1: {},
    });
    assert.notOk(
        hasInvokedFunc,
        "func should not have been invoked on immediate throttle initialization"
    );

    await advanceTime(0);
    assert.notOk(
        hasInvokedFunc,
        "func should not have been invoked from throttle initialization after 0ms"
    );

    throttle.do();
    await nextTick();
    assert.ok(
        hasInvokedFunc,
        "func should have been immediately invoked on first throttle call"
    );
});

QUnit.test('2nd (throttled) call', async function (assert) {
    assert.expect(4);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });
    let funcCalledAmount = 0;
    const throttle = messaging.models['Throttle'].insert({
        func: () => funcCalledAmount++,
        qunitTestOwner2: {},
    });
    throttle.do();
    await nextTick();
    assert.strictEqual(
        funcCalledAmount,
        1,
        "throttle call return should forward result of inner func 1"
    );

    throttle.do();
    await nextTick();
    assert.strictEqual(
        funcCalledAmount,
        1,
        "inner function of throttle should not have been immediately invoked after 2nd call immediately after 1st call (throttled with 1s internal clock)"
    );

    await advanceTime(999);
    assert.strictEqual(
        funcCalledAmount,
        1,
        "inner function of throttle should not have been invoked after 999ms of 2nd call (throttled with 1s internal clock)"
    );

    await advanceTime(1);
    assert.strictEqual(
        funcCalledAmount,
        2,
        "throttle call return should forward result of inner func 2"
    );
});

QUnit.test('throttled call reinvocation', async function (assert) {
    assert.expect(4);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });
    let funcCalledAmount = 0;
    const throttle = messaging.models['Throttle'].insert({
        func: () => funcCalledAmount++,
        qunitTestOwner2: {},
    });
    throttle.do();
    await nextTick();
    assert.strictEqual(
        funcCalledAmount,
        1,
        "throttle call return should forward result of inner func 1"
    );

    throttle.do();
    await nextTick();
    assert.strictEqual(
        funcCalledAmount,
        1,
        "inner function of throttle should not have been immediately invoked after 2nd call immediately after 1st call (throttled with 1s internal clock)"
    );

    await advanceTime(999);
    assert.strictEqual(
        funcCalledAmount,
        1,
        "inner function of throttle should not have been invoked after 999ms of 2nd call (throttled with 1s internal clock)"
    );

    throttle.do();
    await nextTick();
    await advanceTime(1);
    assert.strictEqual(
        funcCalledAmount,
        2,
        "throttle call return should forward result of inner func 2"
    );
});

QUnit.test('clear throttled call', async function (assert) {
    assert.expect(4);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });
    let funcCalledAmount = 0;
    const throttle = messaging.models['Throttle'].insert({
        func: () => funcCalledAmount++,
        qunitTestOwner2: {},
    });
    throttle.do();
    await nextTick();
    assert.strictEqual(
        funcCalledAmount,
        1,
        "inner function of throttle should have been invoked on 1st call (immediate return)"
    );

    throttle.do();
    await nextTick();
    assert.strictEqual(
        funcCalledAmount,
        1,
        "inner function of throttle should not have been immediately invoked after 2nd call immediately after 1st call (throttled with 1s internal clock)"
    );

    await advanceTime(500);
    assert.strictEqual(
        funcCalledAmount,
        1,
        "inner function of throttle should not have been invoked after 500ms of 2nd call (throttled with 1s internal clock)"
    );

    throttle.clear();
    await nextTick();
    throttle.do();
    await nextTick();
    assert.strictEqual(
        funcCalledAmount,
        2,
        "3rd throttle function call should have invoke inner function immediately (`.clear()` flushes throttle)"
    );
});

});
});
});
