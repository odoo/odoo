/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('utils', {}, function () {
QUnit.module('timer', {}, function () {
QUnit.module('timer_tests.js', {});

QUnit.test('timer insert (duration: 0ms)', async function (assert) {
    assert.expect(2);

    const { advanceTime, messaging } = await start({ hasTimeControl: true });
    const timer = messaging.models['Timer'].insert({
        qunitTestOwner1: {},
    });
    assert.ok(
        timer.timeoutId,
        "timer should not have timed out immediately after insert"
    );

    await advanceTime(0);
    assert.notOk(
        timer.timeoutId,
        "timer should have timed out on insert after 0ms"
    );
});

QUnit.test('timer insert (duration: 1000s)', async function (assert) {
    assert.expect(5);

    const { advanceTime, messaging } = await start({ hasTimeControl: true });
    const timer = messaging.models['Timer'].insert({
        qunitTestOwner2: {},
    });
    assert.ok(
        timer.timeoutId,
        "timer should not have timed out immediately after insert"
    );

    await advanceTime(0);
    assert.ok(
        timer.timeoutId,
        "timer should not have timed out on insert after 0ms"
    );

    await advanceTime(1000);
    assert.ok(
        timer.timeoutId,
        "timer should not have timed out on insert after 1000ms"
    );

    await advanceTime(998 * 1000 + 999);
    assert.ok(
        timer.timeoutId,
        "timer should not have timed out on insert after 9999ms"
    );

    await advanceTime(1);
    assert.notOk(
        timer.timeoutId,
        "timer should have timed out on insert after 10s"
    );
});

});
});
});
