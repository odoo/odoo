/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import {
    batched,
    debounce,
    throttleForAnimation,
    useDebounced,
    useThrottleForAnimation,
} from "@web/core/utils/timing";
import {
    makeDeferred,
    patchWithCleanup,
    mockTimeout,
    mockAnimationFrame,
    mount,
    getFixture,
    click,
    destroy,
} from "../../helpers/utils";

function nextMicroTick() {
    return Promise.resolve();
}

function nextAnimationFrame() {
    return new Promise((resolve) => window.requestAnimationFrame(resolve));
}

function nextSetTimeout() {
    return new Promise(setTimeout);
}

QUnit.module("utils", () => {
    QUnit.module("timing", () => {
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
            const { execRegisteredAnimationFrames } = mockAnimationFrame();
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
            const { advanceFrame, execRegisteredAnimationFrames } = mockAnimationFrame();
            const throttledFn = throttleForAnimation((val) => {
                assert.step(`${val}`);
            });

            // A single call is executed immediately
            throttledFn(1);
            assert.verifySteps(["1"], "has been called on the leading edge");
            execRegisteredAnimationFrames();
            assert.verifySteps([], "has not been called");

            // Successive calls
            throttledFn(1);
            assert.verifySteps(["1"], "has been called on the leading edge");
            throttledFn(2);
            throttledFn(3);
            assert.verifySteps([], "has not been called");
            execRegisteredAnimationFrames();
            assert.verifySteps(["3"], "only the last queued call was executed");

            // Can be cancelled
            throttledFn(1);
            assert.verifySteps(["1"], "has been called on the leading edge");
            throttledFn(2);
            throttledFn(3);
            throttledFn.cancel();
            execRegisteredAnimationFrames();
            assert.verifySteps([], "queued throttled function calls were cancelled correctly");

            // Successive calls: more precise timing case
            throttledFn(1);
            assert.verifySteps(["1"], "has been called on the leading edge");
            await advanceFrame();
            throttledFn(2);
            assert.verifySteps(["2"], "has been called on the leading edge");
            throttledFn(3);
            throttledFn(4);
            await advanceFrame();
            assert.verifySteps(["4"], "last call is executed on the trailing edge");
            execRegisteredAnimationFrames();
            assert.verifySteps([], "has not been called");
        });

        QUnit.module("hooks", () => {
            QUnit.test("useDebounced: cancels on comp destroy", async function (assert) {
                const { advanceTime } = mockTimeout();
                class C extends Component {
                    static template = xml`<button class="c" t-on-click="debounced">C</button>`;
                    setup() {
                        this.debounced = useDebounced(() => assert.step("debounced"), 1000);
                    }
                }
                const fixture = getFixture();
                const comp = await mount(C, fixture);
                assert.verifySteps([]);
                assert.containsOnce(fixture, "button.c");

                await click(fixture, "button.c");
                await advanceTime(999);
                assert.verifySteps([]);
                await advanceTime(1);
                assert.verifySteps(["debounced"]);

                await click(fixture, "button.c");
                await advanceTime(999);
                assert.verifySteps([]);
                destroy(comp);
                await advanceTime(1);
                assert.verifySteps([]);
            });

            QUnit.test(
                "useDebounced with execBeforeUnmount option (callback not resolved before comp destroy)",
                async function (assert) {
                    const { advanceTime } = mockTimeout();
                    class C extends Component {
                        static template = xml`<button class="c" t-on-click="() => this.debounced('hello')">C</button>`;
                        setup() {
                            this.debounced = useDebounced(
                                (p) => assert.step(`debounced: ${p}`),
                                1000,
                                {
                                    execBeforeUnmount: true,
                                }
                            );
                        }
                    }
                    const fixture = getFixture();
                    const comp = await mount(C, fixture);
                    assert.verifySteps([]);
                    assert.containsOnce(fixture, "button.c");

                    await click(fixture, "button.c");
                    await advanceTime(999);
                    assert.verifySteps([]);
                    await advanceTime(1);
                    assert.verifySteps(["debounced: hello"]);

                    await click(fixture, "button.c");
                    await advanceTime(999);
                    assert.verifySteps([]);
                    destroy(comp);
                    assert.verifySteps(["debounced: hello"]);
                }
            );

            QUnit.test(
                "useDebounced with execBeforeUnmount option (callback resolved before comp destroy)",
                async function (assert) {
                    const { advanceTime } = mockTimeout();
                    class C extends Component {
                        static template = xml`<button class="c" t-on-click="debounced">C</button>`;
                        setup() {
                            this.debounced = useDebounced(() => assert.step("debounced"), 1000, {
                                execBeforeUnmount: true,
                            });
                        }
                    }
                    const fixture = getFixture();
                    const comp = await mount(C, fixture);
                    assert.verifySteps([]);
                    assert.containsOnce(fixture, "button.c");

                    await click(fixture, "button.c");
                    await advanceTime(999);
                    assert.verifySteps([]);
                    await advanceTime(1);
                    assert.verifySteps(["debounced"]);

                    destroy(comp);
                    await advanceTime(1);
                    assert.verifySteps([]);
                }
            );

            QUnit.test("useThrottleForAnimation: cancels on comp destroy", async function (assert) {
                const { advanceFrame, execRegisteredAnimationFrames } = mockAnimationFrame();
                class C extends Component {
                    static template = xml`<button class="c" t-on-click="throttled">C</button>`;
                    setup() {
                        this.throttled = useThrottleForAnimation(
                            () => assert.step("throttled"),
                            1000
                        );
                    }
                }
                const fixture = getFixture();
                const comp = await mount(C, fixture);
                assert.verifySteps([]);
                assert.containsOnce(fixture, "button.c");

                // Without destroy
                await click(fixture, "button.c");
                assert.verifySteps(["throttled"]);
                await click(fixture, "button.c");
                assert.verifySteps([]);
                await advanceFrame();
                assert.verifySteps(["throttled"]);

                // Clean restart
                execRegisteredAnimationFrames();
                assert.verifySteps([]);

                // With destroy
                await click(fixture, "button.c");
                assert.verifySteps(["throttled"]);
                await click(fixture, "button.c");
                assert.verifySteps([]);
                destroy(comp);
                await advanceFrame();
                assert.verifySteps([]);
            });
        });

        QUnit.module("batched", () => {
            QUnit.test("callback is called only once after operations", async (assert) => {
                let n = 0;
                const fn = batched(() => n++);
                assert.strictEqual(n, 0);
                fn();
                fn();
                assert.strictEqual(n, 0);

                await nextMicroTick();
                assert.strictEqual(n, 1);
                await nextMicroTick();
                assert.strictEqual(n, 1);
            });

            QUnit.test(
                "calling batched function from within the callback is not treated as part of the original batch",
                async (assert) => {
                    let n = 0;
                    const fn = batched(() => {
                        n++;
                        if (n === 1) {
                            fn();
                        }
                    });

                    assert.strictEqual(n, 0);
                    fn();
                    assert.strictEqual(n, 0);
                    await nextMicroTick(); // First batch
                    assert.strictEqual(n, 1);
                    await nextMicroTick(); // Second batch initiated from within the callback
                    assert.strictEqual(n, 2);
                    await nextMicroTick();
                    assert.strictEqual(n, 2);
                }
            );

            QUnit.test("callback is called twice", async (assert) => {
                let n = 0;
                const fn = batched(() => n++);
                assert.strictEqual(n, 0);
                fn();
                assert.strictEqual(n, 0);
                await nextMicroTick();
                assert.strictEqual(n, 1);
                fn();
                assert.strictEqual(n, 1);
                await nextMicroTick();
                assert.strictEqual(n, 2);
            });

            QUnit.test(
                "callback is called only once after operations (synchronize at nextAnimationFrame)",
                async (assert) => {
                    let n = 0;

                    const fn = batched(
                        () => n++,
                        () => new Promise((resolve) => window.requestAnimationFrame(resolve))
                    );
                    assert.strictEqual(n, 0);
                    fn();
                    fn();
                    assert.strictEqual(n, 0);

                    await nextAnimationFrame();
                    assert.strictEqual(n, 1);
                    await nextAnimationFrame();
                    assert.strictEqual(n, 1);
                }
            );

            QUnit.test(
                "calling batched function from within the callback is not treated as part of the original batch (synchronize at nextAnimationFrame)",
                async (assert) => {
                    let n = 0;
                    const fn = batched(
                        () => {
                            n++;
                            if (n === 1) {
                                fn();
                            }
                        },
                        () => new Promise((resolve) => window.requestAnimationFrame(resolve))
                    );

                    assert.strictEqual(n, 0);
                    fn();
                    assert.strictEqual(n, 0);
                    await nextAnimationFrame(); // First batch
                    assert.strictEqual(n, 1);
                    await nextAnimationFrame(); // Second batch initiated from within the callback
                    assert.strictEqual(n, 2);
                    await nextAnimationFrame();
                    assert.strictEqual(n, 2);
                }
            );

            QUnit.test(
                "callback is called twice (synchronize at nextAnimationFrame)",
                async (assert) => {
                    let n = 0;
                    const fn = batched(
                        () => n++,
                        () => new Promise((resolve) => window.requestAnimationFrame(resolve))
                    );
                    assert.strictEqual(n, 0);
                    fn();
                    assert.strictEqual(n, 0);
                    await nextAnimationFrame();
                    assert.strictEqual(n, 1);
                    fn();
                    assert.strictEqual(n, 1);
                    await nextAnimationFrame();
                    assert.strictEqual(n, 2);
                }
            );

            QUnit.test(
                "callback is called only once after operations (synchronize at setTimeout)",
                async (assert) => {
                    let n = 0;

                    const fn = batched(
                        () => n++,
                        () => new Promise(setTimeout)
                    );
                    assert.strictEqual(n, 0);
                    fn();
                    fn();
                    assert.strictEqual(n, 0);

                    await nextSetTimeout();
                    assert.strictEqual(n, 1);
                    await nextSetTimeout();
                    assert.strictEqual(n, 1);
                }
            );

            QUnit.test(
                "calling batched function from within the callback is not treated as part of the original batch (synchronize at setTimeout)",
                async (assert) => {
                    let n = 0;
                    const fn = batched(
                        () => {
                            n++;
                            if (n === 1) {
                                fn();
                            }
                        },
                        () => new Promise(setTimeout)
                    );

                    assert.strictEqual(n, 0);
                    fn();
                    assert.strictEqual(n, 0);
                    await nextSetTimeout(); // First batch
                    assert.strictEqual(n, 1);
                    await nextSetTimeout(); // Second batch initiated from within the callback
                    assert.strictEqual(n, 2);
                    await nextSetTimeout();
                    assert.strictEqual(n, 2);
                }
            );

            QUnit.test("callback is called twice (synchronize at setTimeout)", async (assert) => {
                let n = 0;
                const fn = batched(
                    () => n++,
                    () => new Promise(setTimeout)
                );
                assert.strictEqual(n, 0);
                fn();
                assert.strictEqual(n, 0);
                await nextSetTimeout();
                assert.strictEqual(n, 1);
                fn();
                assert.strictEqual(n, 1);
                await nextSetTimeout();
                assert.strictEqual(n, 2);
            });
        });
    });

    QUnit.test("throttleForAnimationScrollEvent", async (assert) => {
        assert.expect(9);
        const { advanceFrame, execRegisteredAnimationFrames } = mockAnimationFrame();
        let resolveThrottled;
        let throttled = new Promise(resolve => resolveThrottled = resolve);
        const throttledFn = throttleForAnimation((val, targetEl) => {
            // In Chrome, the currentTarget of scroll events is lost after the
            // event was handled, it is therefore null here.
            // Because of this, if it is needed, it must be included in the
            // callback signature.
            const nodeName = val && val.currentTarget && val.currentTarget.nodeName;
            const targetName = targetEl && targetEl.nodeName;
            assert.step(`throttled function called with ${nodeName} in event, but ${targetName} in parameter`);
            resolveThrottled();
        });

        const el = document.createElement("div");
        el.style = "position: absolute; overflow: scroll; height: 100px; width: 100px;";
        const childEl = document.createElement("div");
        childEl.style = "height: 200px; width: 200px;";
        let resolveScrolled;
        let scrolled = new Promise(resolve => resolveScrolled = resolve);
        el.appendChild(childEl);
        el.addEventListener("scroll", (ev) => {
            assert.step("before scroll");
            throttledFn(ev, ev.currentTarget);
            assert.step("after scroll");
            resolveScrolled();
        });
        document.body.appendChild(el);
        el.scrollBy(1, 1);
        el.scrollBy(2, 2);
        await scrolled;
        await throttled;

        assert.verifySteps([
            "before scroll",
            "throttled function called with DIV in event, but DIV in parameter",
            "after scroll",
        ], "scroll happened and direct first call to throttled function happened too");

        throttled = new Promise(resolve => resolveThrottled = resolve);
        scrolled = new Promise(resolve => resolveScrolled = resolve);
        el.scrollBy(3, 3);
        await scrolled;
        assert.verifySteps([
            "before scroll",
            // Further call is delayed.
            "after scroll",
        ], "scroll happened but throttled function hasn't been called yet");
        setTimeout(() => {
            advanceFrame();
            execRegisteredAnimationFrames();
        });
        await throttled;
        assert.verifySteps(
            ["throttled function called with null in event, but DIV in parameter"],
            "currentTarget was not available in throttled function's event"
        );
        el.remove();
    });

});
