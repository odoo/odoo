/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { debounce, throttle, throttleForAnimation } from "@web/core/utils/timing";
import {
    makeDeferred,
    patchWithCleanup,
    mockTimeout,
    mockAnimationFrame,
} from "../../helpers/utils";

QUnit.module("utils", () => {
    QUnit.module("timing");

    QUnit.test("debounce on an async function", async function (assert) {
        let callback;
        patchWithCleanup(browser, {
            setTimeout: (later) => {
                callback = later;
            },
        });
        const imSearchDef = makeDeferred();
        const myFunc = () => {
            assert.step("myFunc");
            return imSearchDef;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then(() => {
            throw new Error("Should never be resolved");
        });
        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        assert.verifySteps([]);
        callback();
        assert.verifySteps(["myFunc"]);
        imSearchDef.resolve(42);
        await Promise.resolve(); // wait for promise returned by myFunc
        await Promise.resolve(); // wait for promise returned by debounce

        assert.verifySteps(["resolved 42"]);
    });

    QUnit.test("debounce on a sync function", async function (assert) {
        let callback;
        patchWithCleanup(browser, {
            setTimeout: (later) => {
                callback = later;
            },
        });
        const myFunc = () => {
            assert.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then(() => {
            throw new Error("Should never be resolved");
        });
        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        assert.verifySteps([]);
        callback();
        assert.verifySteps(["myFunc"]);
        await Promise.resolve(); // wait for promise returned by myFunc
        await Promise.resolve(); // wait for promise returned by debounce

        assert.verifySteps(["resolved 42"]);
    });

    QUnit.test("debounce with immediate", async function (assert) {
        const { execRegisteredTimeouts } = mockTimeout();
        const myFunc = () => {
            assert.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000, { immediate: true });
        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        assert.verifySteps(["myFunc"]);
        await Promise.resolve(); // wait for promise returned by debounce
        await Promise.resolve(); // wait for promise returned chained onto it (step resolved x)
        assert.verifySteps(["resolved 42"]);

        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        await execRegisteredTimeouts();
        assert.verifySteps([]); // not called 3000ms did not elapse between the previous call and the first

        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        assert.verifySteps(["myFunc"]);
        await Promise.resolve(); // wait for promise returned by debounce
        await Promise.resolve(); // wait for promise returned chained onto it (step resolved x)
        assert.verifySteps(["resolved 42"]);
    });

    QUnit.test("debounce with 'animationFrame' delay", async function (assert) {
        const { execRegisteredTimeouts } = mockTimeout();
        const execRegisteredAnimationFrames = mockAnimationFrame();
        const myFunc = () => {
            assert.step("myFunc");
        };
        debounce(myFunc, "animationFrame")();
        assert.verifySteps([]);

        execRegisteredTimeouts(); // should have no effect as we wait for the animation frame
        assert.verifySteps([]);

        execRegisteredAnimationFrames(); // should call the function
        assert.verifySteps(["myFunc"]);
    });

    QUnit.test("debounced call can be cancelled", async function (assert) {
        assert.expect(3);
        const { execRegisteredTimeouts } = mockTimeout();
        const myFunc = () => {
            assert.step("myFunc");
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc();
        myDebouncedFunc.cancel();
        execRegisteredTimeouts();
        assert.verifySteps([], "Debounced call was cancelled");

        myDebouncedFunc();
        execRegisteredTimeouts();
        assert.verifySteps(["myFunc"], "Debounced call was not cancelled");
    });

    QUnit.test("throttleForAnimation", async (assert) => {
        assert.expect(4);
        const execAnimationFrameCallbacks = mockAnimationFrame();
        const throttledFn = throttleForAnimation((val) => {
            assert.step(`throttled function called with ${val}`);
        });

        throttledFn(0);
        throttledFn(1);
        assert.verifySteps([], "throttled function hasn't been called yet");
        execAnimationFrameCallbacks();
        assert.verifySteps(
            ["throttled function called with 1"],
            "only the last queued call was executed"
        );
        throttledFn(2);
        throttledFn(3);
        throttledFn.cancel();
        execAnimationFrameCallbacks();
        assert.verifySteps([], "queued throttled function calls were cancelled correctly");
    });

    QUnit.test("throttle", async (assert) => {
        const { execRegisteredTimeouts, advanceTime } = mockTimeout();
        const throttledFn = throttle((val) => assert.step(`${val}`), 3000);

        // A single call to the throttled function should execute immediately
        throttledFn(1);
        assert.verifySteps(["1"], "has been called on the leading edge");
        execRegisteredTimeouts();
        assert.verifySteps([], "has not been called on the trailing edge");

        // Successive calls
        throttledFn(1);
        throttledFn(2);
        throttledFn(3);
        assert.verifySteps(["1"], "has been called on the leading edge");
        execRegisteredTimeouts();
        assert.verifySteps(["3"], "last call is executed on the trailing edge");

        // Successive calls: more precise timing case
        throttledFn(1);
        assert.verifySteps(["1"], "has been called on the leading edge");
        await advanceTime(2000);
        throttledFn(2);
        await advanceTime(999);
        throttledFn(3);
        assert.verifySteps([], "has not been called");
        await advanceTime(1);
        assert.verifySteps(["3"], "last call is executed on the trailing edge");
        throttledFn(4);
        assert.verifySteps([], "has not been called");
        await advanceTime(3000);
        assert.verifySteps(["4"], "last call is executed on the trailing edge");
        execRegisteredTimeouts();

        // Can be cancelled
        throttledFn(1);
        throttledFn(2);
        assert.verifySteps(["1"], "has been called on the leading edge");
        throttledFn.cancel();
        execRegisteredTimeouts();
        assert.verifySteps([], "has been cancelled");
    });
});
