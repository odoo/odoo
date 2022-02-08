/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";
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
        patchWithCleanup(browser, {
            setTimeout: (later) => {
                later();
            },
        });
        const myFunc = () => {
            assert.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000, true);
        myDebouncedFunc().then((x) => {
            assert.step("resolved " + x);
        });
        assert.verifySteps(["myFunc"]);
        await Promise.resolve(); // wait for promise returned by myFunc
        await Promise.resolve(); // wait for promise returned by debounce

        assert.verifySteps(["resolved 42"]);
    });

    QUnit.test("debounced call can be canceled", async function (assert) {
        assert.expect(1);
        const execRegisteredTimeouts = mockTimeout();
        const myFunc = () => {
            assert.step("myFunc");
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc();
        myDebouncedFunc.cancel();
        execRegisteredTimeouts();
        assert.verifySteps([], "Debounced call was canceled");
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
});
