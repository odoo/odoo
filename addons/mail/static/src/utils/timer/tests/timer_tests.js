/** @odoo-module **/

import { afterEach, beforeEach, nextTick, start } from '@mail/utils/test_utils';
import Timer from '@mail/utils/timer/timer';

const { TimerClearedError } = Timer;

QUnit.module('mail', {}, function () {
QUnit.module('utils', {}, function () {
QUnit.module('timer', {}, function () {
QUnit.module('timer_tests.js', {
    beforeEach() {
        beforeEach(this);
        this.timers = [];

        this.start = async (params) => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        // Important: tests should cleanly intercept cancelation errors that
        // may result from this teardown.
        for (const timer of this.timers) {
            timer.clear();
        }
        afterEach(this);
    },
});

QUnit.test('timer does not timeout on initialization', async function (assert) {
    assert.expect(3);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => hasTimedOut = true,
            0
        )
    );

    assert.notOk(
        hasTimedOut,
        "timer should not have timed out on immediate initialization"
    );

    await this.env.testUtils.advanceTime(0);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out from initialization after 0ms"
    );

    await this.env.testUtils.advanceTime(1000 * 1000);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out from initialization after 1000s"
    );
});

QUnit.test('timer start (duration: 0ms)', async function (assert) {
    assert.expect(2);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => hasTimedOut = true,
            0
        )
    );

    this.timers[0].start();
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start"
    );

    await this.env.testUtils.advanceTime(0);
    assert.ok(
        hasTimedOut,
        "timer should have timed out on start after 0ms"
    );
});

QUnit.test('timer start observe termination (duration: 0ms)', async function (assert) {
    assert.expect(6);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => {
                hasTimedOut = true;
                return 'timeout_result';
            },
            0
        )
    );

    this.timers[0].start()
        .then(result => {
            assert.strictEqual(
                result,
                'timeout_result',
                "value returned by start should be value returned by function on timeout"
            );
            assert.step('timeout');
        });
    await nextTick();
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start"
    );
    assert.verifySteps(
        [],
        "timer.start() should not have yet observed timeout"
    );

    await this.env.testUtils.advanceTime(0);
    assert.ok(
        hasTimedOut,
        "timer should have timed out on start after 0ms"
    );
    assert.verifySteps(
        ['timeout'],
        "timer.start() should have observed timeout after 0ms"
    );
});

QUnit.test('timer start (duration: 1000s)', async function (assert) {
    assert.expect(5);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => hasTimedOut = true,
            1000 * 1000
        )
    );

    this.timers[0].start();
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start"
    );

    await this.env.testUtils.advanceTime(0);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out on start after 0ms"
    );

    await this.env.testUtils.advanceTime(1000);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out on start after 1000ms"
    );

    await this.env.testUtils.advanceTime(998 * 1000 + 999);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out on start after 9999ms"
    );

    await this.env.testUtils.advanceTime(1);
    assert.ok(
        hasTimedOut,
        "timer should have timed out on start after 10s"
    );
});

QUnit.test('[no cancelation intercept] timer start then immediate clear (duration: 0ms)', async function (assert) {
    assert.expect(4);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => hasTimedOut = true,
            0
        )
    );

    this.timers[0].start();
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start"
    );

    this.timers[0].clear();
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start and clear"
    );

    await this.env.testUtils.advanceTime(0);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out after 0ms of clear"
    );

    await this.env.testUtils.advanceTime(1000);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out after 1s of clear"
    );
});

QUnit.test('[no cancelation intercept] timer start then clear before timeout (duration: 1000ms)', async function (assert) {
    assert.expect(4);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => hasTimedOut = true,
            1000
        )
    );

    this.timers[0].start();
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start"
    );

    await this.env.testUtils.advanceTime(999);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after 999ms of start"
    );

    this.timers[0].clear();
    await this.env.testUtils.advanceTime(1);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out after 1ms of clear that happens 999ms after start (globally 1s await)"
    );

    await this.env.testUtils.advanceTime(1000);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out after 1001ms after clear (timer fully cleared)"
    );
});

QUnit.test('[no cancelation intercept] timer start then reset before timeout (duration: 1000ms)', async function (assert) {
    assert.expect(5);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => hasTimedOut = true,
            1000
        )
    );

    this.timers[0].start();
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start"
    );

    await this.env.testUtils.advanceTime(999);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out after 999ms of start"
    );

    this.timers[0].reset();
    await this.env.testUtils.advanceTime(1);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out after 1ms of reset which happens 999ms after start"
    );

    await this.env.testUtils.advanceTime(998);
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out after 999ms of reset"
    );

    await this.env.testUtils.advanceTime(1);
    assert.ok(
        hasTimedOut,
        "timer should not have timed out after 1s of reset"
    );
});

QUnit.test('[with cancelation intercept] timer start then immediate clear (duration: 0ms)', async function (assert) {
    assert.expect(5);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => hasTimedOut = true,
            0,
            { silentCancelationErrors: false }
        )
    );

    this.timers[0].start()
        .then(() => {
            throw new Error("timer.start() should not be resolved (should have been canceled by clear)");
        })
        .catch(error => {
            assert.ok(
                error instanceof TimerClearedError,
                "Should generate a Timer cleared error (from `.clear()`)"
            );
            assert.step('timer_cleared');
        });
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start"
    );
    await nextTick();
    assert.verifySteps([], "should not have observed cleared timer (timer not yet cleared)");

    this.timers[0].clear();
    await nextTick();
    assert.verifySteps(
        ['timer_cleared'],
        "timer.start() should have observed it has been cleared"
    );
});

QUnit.test('[with cancelation intercept] timer start then immediate reset (duration: 0ms)', async function (assert) {
    assert.expect(9);

    await this.start({
        hasTimeControl: true,
    });

    let hasTimedOut = false;
    this.timers.push(
        new Timer(
            this.env,
            () => hasTimedOut = true,
            0,
            { silentCancelationErrors: false }
        )
    );

    this.timers[0].start()
        .then(() => {
            throw new Error("timer.start() should not observe a timeout");
        })
        .catch(error => {
            assert.ok(error instanceof TimerClearedError, "Should generate a Timer cleared error (from `.reset()`)");
            assert.step('timer_cleared');
        });
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after start"
    );
    await nextTick();
    assert.verifySteps([], "should not have observed cleared timer (timer not yet cleared)");

    this.timers[0].reset()
        .then(() => assert.step('timer_reset_timeout'));
    await nextTick();
    assert.verifySteps(
        ['timer_cleared'],
        "timer.start() should have observed it has been cleared"
    );
    assert.notOk(
        hasTimedOut,
        "timer should not have timed out immediately after reset"
    );

    await this.env.testUtils.advanceTime(0);
    assert.ok(
        hasTimedOut,
        "timer should have timed out after reset timeout"
    );
    assert.verifySteps(
        ['timer_reset_timeout'],
        "timer.reset() should have observed it has timed out"
    );
});

});
});
});
