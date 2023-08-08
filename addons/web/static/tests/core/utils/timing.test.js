import { describe, destroy, expect, mountOnFixture, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { Deferred, advanceTime, animationFrame, microTick, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";

import {
    batched,
    debounce,
    throttleForAnimation,
    useDebounced,
    useThrottleForAnimation,
} from "@web/core/utils/timing";

describe.current.tags("headless");

function nextMicroTick() {
    return Promise.resolve();
}

function nextAnimationFrame() {
    return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

function nextSetTimeout() {
    return new Promise((resolve) => setTimeout(() => resolve()));
}

describe("batched", () => {
    test("callback is called only once after operations", async () => {
        let n = 0;
        const fn = batched(() => n++);
        expect(n).toBe(0);

        fn();
        fn();
        expect(n).toBe(0);

        await nextMicroTick();
        expect(n).toBe(1);

        await nextMicroTick();
        expect(n).toBe(1);
    });

    test("callback is called only once after operations (synchronize at nextAnimationFrame)", async () => {
        let n = 0;
        const fn = batched(
            () => n++,
            () => nextAnimationFrame()
        );
        expect(n).toBe(0);

        fn();
        fn();
        expect(n).toBe(0);

        await nextMicroTick();
        expect(n).toBe(0);

        await nextAnimationFrame();
        expect(n).toBe(1);

        await nextAnimationFrame();
        expect(n).toBe(1);
    });

    test("callback is called only once after operations (synchronize at setTimeout)", async () => {
        let n = 0;
        const fn = batched(
            () => n++,
            () => new Promise(setTimeout)
        );
        expect(n).toBe(0);

        fn();
        fn();
        expect(n).toBe(0);

        await nextMicroTick();
        expect(n).toBe(0);

        await nextSetTimeout();
        expect(n).toBe(1);

        await nextSetTimeout();
        expect(n).toBe(1);
    });

    test("calling batched function from within the callback is not treated as part of the original batch", async () => {
        let n = 0;
        const fn = batched(() => {
            n++;
            if (n === 1) {
                fn();
            }
        });
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await nextMicroTick(); // First batch
        expect(n).toBe(1);

        await nextMicroTick(); // Second batch initiated from within the callback
        expect(n).toBe(2);

        await nextMicroTick();
        expect(n).toBe(2);
    });

    test("calling batched function from within the callback is not treated as part of the original batch (synchronize at nextAnimationFrame)", async () => {
        let n = 0;
        const fn = batched(
            () => {
                n++;
                if (n === 1) {
                    fn();
                }
            },
            () => nextAnimationFrame()
        );
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await nextAnimationFrame(); // First batch
        expect(n).toBe(1);

        await nextAnimationFrame(); // Second batch initiated from within the callback
        expect(n).toBe(2);

        await nextAnimationFrame();
        expect(n).toBe(2);
    });

    test("calling batched function from within the callback is not treated as part of the original batch (synchronize at setTimeout)", async () => {
        let n = 0;
        const fn = batched(
            () => {
                n++;
                if (n === 1) {
                    fn();
                }
            },
            () => nextSetTimeout()
        );
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await nextSetTimeout(); // First batch
        expect(n).toBe(1);

        await nextSetTimeout(); // Second batch initiated from within the callback
        expect(n).toBe(2);

        await nextSetTimeout();
        expect(n).toBe(2);
    });

    test("callback is called twice", async () => {
        let n = 0;
        const fn = batched(() => n++);
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await nextMicroTick();
        expect(n).toBe(1);

        fn();
        expect(n).toBe(1);

        await nextMicroTick();
        expect(n).toBe(2);
    });

    test("callback is called twice (synchronize at nextAnimationFrame)", async () => {
        let n = 0;
        const fn = batched(
            () => n++,
            () => nextAnimationFrame()
        );

        expect(n).toBe(0);
        fn();

        expect(n).toBe(0);
        await nextAnimationFrame();
        expect(n).toBe(1);

        fn();
        expect(n).toBe(1);

        await nextAnimationFrame();
        expect(n).toBe(2);
    });

    test("callback is called twice (synchronize at setTimeout)", async () => {
        let n = 0;
        const fn = batched(
            () => n++,
            () => nextSetTimeout()
        );
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await nextSetTimeout();
        expect(n).toBe(1);

        fn();
        expect(n).toBe(1);

        await nextSetTimeout();
        expect(n).toBe(2);
    });
});

describe("debounce", () => {
    test("debounce on a sync function", async () => {
        const myFunc = () => {
            expect.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then(() => {
            throw new Error("Should never be resolved");
        });
        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect([]).toVerifySteps();

        await advanceTime(3000);
        expect(["myFunc", "resolved 42"]).toVerifySteps();
    });

    test("debounce on an async function", async () => {
        const imSearchDef = new Deferred();
        const myFunc = () => {
            expect.step("myFunc");
            return imSearchDef;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then(() => {
            throw new Error("Should never be resolved");
        });
        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect([]).toVerifySteps();

        await advanceTime(3000);
        expect(["myFunc"]).toVerifySteps();

        imSearchDef.resolve(42);
        await microTick(); // wait for promise returned by myFunc
        await microTick(); // wait for promise returned by debounce
        expect(["resolved 42"]).toVerifySteps();
    });

    test("debounce with immediate", async () => {
        const myFunc = () => {
            expect.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000, { immediate: true });
        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect(["myFunc"]).toVerifySteps();

        await microTick(); // wait for promise returned by debounce
        await microTick(); // wait for promise returned chained onto it (step resolved x)
        expect(["resolved 42"]).toVerifySteps();

        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        await runAllTimers();
        expect([]).toVerifySteps(); // not called 3000ms did not elapse between the previous call and the first

        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect(["myFunc"]).toVerifySteps();

        await microTick(); // wait for promise returned by debounce
        await microTick(); // wait for promise returned chained onto it (step resolved x)
        expect(["resolved 42"]).toVerifySteps();
    });

    test("debounce with 'animationFrame' delay", async () => {
        const myFunc = () => expect.step("myFunc");

        debounce(myFunc, "animationFrame")();
        expect([]).toVerifySteps();
        await nextAnimationFrame();
        expect(["myFunc"]).toVerifySteps();
    });

    test("debounced call can be cancelled", async () => {
        const myFunc = () => {
            expect.step("myFunc");
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc();
        myDebouncedFunc.cancel();
        await runAllTimers();
        expect([]).toVerifySteps(); // Debounced call was cancelled

        myDebouncedFunc();
        await runAllTimers();
        expect(["myFunc"]).toVerifySteps(); // Debounced call was not cancelled
    });
});

describe("throttleForAnimation", () => {
    test("single call is executed immediately", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
        });
        throttledFn(1);
        expect(["1"]).toVerifySteps({ message: "has been called on the leading edge" });

        await runAllTimers();
        expect([]).toVerifySteps({ message: "has not been called" });
    });

    test("successive calls", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
        });
        throttledFn(1);
        expect(["1"]).toVerifySteps({ message: "has been called on the leading edge" });

        throttledFn(2);
        throttledFn(3);
        expect([]).toVerifySteps({ message: "has not been called" });

        await runAllTimers();
        expect(["3"]).toVerifySteps({ message: "only the last queued call was executed" });
    });

    test("successive calls (more precise timing)", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
        });
        throttledFn(1);
        expect(["1"]).toVerifySteps({ message: "has been called on the leading edge" });

        await nextAnimationFrame();
        throttledFn(2);
        expect(["2"]).toVerifySteps({ message: "has been called on the leading edge" });

        throttledFn(3);
        throttledFn(4);
        await nextAnimationFrame();
        expect(["4"]).toVerifySteps({ message: "last call is executed on the trailing edge" });

        await runAllTimers();
        expect([]).toVerifySteps({ message: "has not been called" });
    });

    test("can be cancelled", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
        });
        throttledFn(1);
        expect(["1"]).toVerifySteps({ message: "has been called on the leading edge" });

        throttledFn(2);
        throttledFn(3);
        throttledFn.cancel();
        await runAllTimers();
        expect([]).toVerifySteps({
            message: "queued throttled function calls were cancelled correctly",
        });
    });
});

describe("throttleForAnimationScrollEvent", () => {
    test("scroll loses target", async () => {
        let resolveThrottled;
        let throttled = new Promise(resolve => resolveThrottled = resolve);
        const throttledFn = throttleForAnimation((val, targetEl) => {
            // In Chrome, the currentTarget of scroll events is lost after the
            // event was handled, it is therefore null here.
            // Because of this, if it is needed, it must be included in the
            // callback signature.
            const nodeName = val && val.currentTarget && val.currentTarget.nodeName;
            const targetName = targetEl && targetEl.nodeName;
            expect.step(`throttled function called with ${nodeName} in event, but ${targetName} in parameter`);
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
            expect.step("before scroll");
            throttledFn(ev, ev.currentTarget);
            expect.step("after scroll");
            resolveScrolled();
        });
        document.body.appendChild(el);
        el.scrollBy(1, 1);
        el.scrollBy(2, 2);
        await scrolled;
        await throttled;
    
        expect([
            "before scroll",
            "throttled function called with DIV in event, but DIV in parameter",
            "after scroll",
        ]).toVerifySteps({ message: "scroll happened and direct first call to throttled function happened too" });
    
        throttled = new Promise(resolve => resolveThrottled = resolve);
        scrolled = new Promise(resolve => resolveScrolled = resolve);
        el.scrollBy(3, 3);
        await scrolled;
        expect([
            "before scroll",
            // Further call is delayed.
            "after scroll",
        ]).toVerifySteps({ message: "scroll happened but throttled function hasn't been called yet" });
        setTimeout(async () => {
            await nextAnimationFrame();
        });
        await throttled;
        expect([
            "throttled function called with null in event, but DIV in parameter",
        ]).toVerifySteps({ message: "currentTarget was not available in throttled function's event" });
        el.remove();
    });
});

describe("useDebounced", () => {
    test("cancels on component destroy", async () => {
        class TestComponent extends Component {
            static template = xml`<button class="c" t-on-click="debounced">C</button>`;
            static props = ["*"];
            setup() {
                this.debounced = useDebounced(() => expect.step("debounced"), 1000);
            }
        }
        const component = await mountOnFixture(TestComponent);
        expect([]).toVerifySteps();
        expect("button.c").toHaveCount(1);

        click(`button.c`);
        await advanceTime(900);
        expect([]).toVerifySteps();

        await advanceTime(200);
        expect(["debounced"]).toVerifySteps();

        click(`button.c`);
        await advanceTime(900);
        expect([]).toVerifySteps();

        destroy(component);
        await advanceTime(200);
        expect([]).toVerifySteps();
    });

    test("execBeforeUnmount option (callback not resolved before component destroy)", async () => {
        class TestComponent extends Component {
            static template = xml`<button class="c" t-on-click="() => this.debounced('hello')">C</button>`;
            static props = ["*"];
            setup() {
                this.debounced = useDebounced((p) => expect.step(`debounced: ${p}`), 1000, {
                    execBeforeUnmount: true,
                });
            }
        }
        const component = await mountOnFixture(TestComponent);
        expect([]).toVerifySteps();
        expect(`button.c`).toHaveCount(1);

        click(`button.c`);
        await advanceTime(900);
        expect([]).toVerifySteps();

        await advanceTime(200);
        expect(["debounced: hello"]).toVerifySteps();

        click(`button.c`);
        await advanceTime(900);
        expect([]).toVerifySteps();

        destroy(component);
        expect(["debounced: hello"]).toVerifySteps();
    });

    test("execBeforeUnmount option (callback resolved before component destroy)", async () => {
        class TestComponent extends Component {
            static template = xml`<button class="c" t-on-click="debounced">C</button>`;
            static props = ["*"];
            setup() {
                this.debounced = useDebounced(() => expect.step("debounced"), 1000, {
                    execBeforeUnmount: true,
                });
            }
        }
        const component = await mountOnFixture(TestComponent);
        expect([]).toVerifySteps();
        expect(`button.c`).toHaveCount(1);

        click(`button.c`);
        await advanceTime(900);
        expect([]).toVerifySteps();

        await advanceTime(200);
        expect(["debounced"]).toVerifySteps();

        destroy(component);
        await advanceTime(1000);
        expect([]).toVerifySteps();
    });
});

describe("useThrottleForAnimation", () => {
    test("cancels on component destroy", async () => {
        class TestComponent extends Component {
            static template = xml`<button class="c" t-on-click="throttled">C</button>`;
            static props = ["*"];
            setup() {
                this.throttled = useThrottleForAnimation(() => expect.step("throttled"), 1000);
            }
        }
        const component = await mountOnFixture(TestComponent);
        expect([]).toVerifySteps();
        expect(`button.c`).toHaveCount(1);

        // Without destroy
        click(`button.c`);
        expect(["throttled"]).toVerifySteps();

        click(`button.c`);
        expect([]).toVerifySteps();

        await animationFrame();
        expect(["throttled"]).toVerifySteps();

        // Clean restart
        await runAllTimers();
        expect([]).toVerifySteps();

        // With destroy
        click(`button.c`);
        expect(["throttled"]).toVerifySteps();

        click(`button.c`);
        expect([]).toVerifySteps();

        destroy(component);
        await animationFrame();
        expect([]).toVerifySteps();
    });
});
