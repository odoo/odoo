import { describe, destroy, expect, getFixture, test } from "@odoo/hoot";
import { click, tick } from "@odoo/hoot-dom";
import { Deferred, advanceTime, animationFrame, microTick, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import {
    batched,
    debounce,
    throttleForAnimation,
    useDebounced,
    useThrottleForAnimation,
} from "@web/core/utils/timing";

describe.current.tags("headless");

describe("batched", () => {
    test("callback is called only once after operations", async () => {
        let n = 0;
        const fn = batched(() => n++);
        expect(n).toBe(0);

        fn();
        fn();
        expect(n).toBe(0);

        await microTick();
        expect(n).toBe(1);

        await microTick();
        expect(n).toBe(1);
    });

    test("callback is called only once after operations (synchronize at animationFrame)", async () => {
        let n = 0;
        const fn = batched(() => n++, animationFrame);
        expect(n).toBe(0);

        fn();
        fn();
        expect(n).toBe(0);

        await microTick();
        expect(n).toBe(0);

        await animationFrame();
        expect(n).toBe(1);

        await animationFrame();
        expect(n).toBe(1);
    });

    test("callback is called only once after operations (synchronize at setTimeout)", async () => {
        let n = 0;
        const fn = batched(() => n++, tick);
        expect(n).toBe(0);

        fn();
        fn();
        expect(n).toBe(0);

        await microTick();
        expect(n).toBe(0);

        await tick();
        expect(n).toBe(1);

        await tick();
        expect(n).toBe(1);
    });

    test("calling batched function from within the callback is not treated as part of the original batch", async () => {
        let n = 0;
        const fn = batched(() => ++n == 1 && fn());
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await Promise.resolve(); // First batch
        expect(n).toBe(1);

        await Promise.resolve(); // Second batch initiated from within the callback
        expect(n).toBe(2);

        await Promise.resolve();
        expect(n).toBe(2);
    });

    test("calling batched function from within the callback is not treated as part of the original batch (synchronize at animationFrame)", async () => {
        let n = 0;
        const fn = batched(() => ++n == 1 && fn(), animationFrame);
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await animationFrame(); // First batch
        expect(n).toBe(1);

        await animationFrame(); // Second batch initiated from within the callback
        expect(n).toBe(2);

        await animationFrame();
        expect(n).toBe(2);
    });

    test("calling batched function from within the callback is not treated as part of the original batch (synchronize at setTimeout)", async () => {
        let n = 0;
        const fn = batched(() => ++n === 1 && fn(), tick);
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await tick(); // First batch
        expect(n).toBe(1);

        await tick(); // Second batch initiated from within the callback
        expect(n).toBe(2);

        await tick();
        expect(n).toBe(2);
    });

    test("callback is called twice", async () => {
        let n = 0;
        const fn = batched(() => n++);
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await microTick();
        expect(n).toBe(1);

        fn();
        expect(n).toBe(1);

        await microTick();
        expect(n).toBe(2);
    });

    test("callback is called twice (synchronize at animationFrame)", async () => {
        let n = 0;
        const fn = batched(() => n++, animationFrame);

        expect(n).toBe(0);
        fn();

        expect(n).toBe(0);
        await animationFrame();
        expect(n).toBe(1);

        fn();
        expect(n).toBe(1);

        await animationFrame();
        expect(n).toBe(2);
    });

    test("callback is called twice (synchronize at setTimeout)", async () => {
        let n = 0;
        const fn = batched(() => n++, tick);
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await tick();
        expect(n).toBe(1);

        fn();
        expect(n).toBe(1);

        await tick();
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
        expect.verifySteps([]);

        await advanceTime(3000);
        expect.verifySteps(["myFunc", "resolved 42"]);
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
        expect.verifySteps([]);

        await advanceTime(3000);
        expect.verifySteps(["myFunc"]);

        imSearchDef.resolve(42);
        await microTick(); // wait for promise returned by myFunc
        await microTick(); // wait for promise returned by debounce

        expect.verifySteps(["resolved 42"]);
    });

    test("debounce with immediate", async () => {
        const myFunc = () => {
            expect.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000, true);
        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect.verifySteps(["myFunc"]);

        await microTick(); // wait for promise returned by myFunc
        await microTick(); // wait for promise returned by debounce

        expect.verifySteps(["resolved 42"]);

        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        await runAllTimers();
        expect.verifySteps([]); // not called 3000ms did not elapse between the previous call and the first

        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect.verifySteps(["myFunc"]);

        await microTick(); // wait for promise returned by debounce
        await microTick(); // wait for promise returned chained onto it (step resolved x)
        expect.verifySteps(["resolved 42"]);
    });

    test("debounce with 'animationFrame' delay", async () => {
        const myFunc = () => expect.step("myFunc");

        debounce(myFunc, "animationFrame")();
        expect.verifySteps([]);
        await animationFrame();
        expect.verifySteps(["myFunc"]);
    });

    test("debounced call can be cancelled", async () => {
        const myFunc = () => {
            expect.step("myFunc");
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc();
        myDebouncedFunc.cancel();
        await runAllTimers();
        expect.verifySteps([]); // Debounced call was cancelled

        myDebouncedFunc();
        await runAllTimers();
        expect.verifySteps(["myFunc"]); // Debounced call was not cancelled
    });

    test("debounce with leading and trailing", async () => {
        const myFunc = (lastValue) => {
            expect.step("myFunc");
            return lastValue;
        };
        const myDebouncedFunc = debounce(myFunc, 3000, { leading: true, trailing: true });
        myDebouncedFunc(42).then((x) => expect.step("resolved " + x));
        myDebouncedFunc(43).then((x) => expect.step("resolved " + x));
        myDebouncedFunc(44).then((x) => expect.step("resolved " + x));
        expect.verifySteps(["myFunc"]);
        await microTick(); // wait for promise returned by debounce
        await microTick(); // wait for promise returned chained onto it (step resolved x)
        expect.verifySteps(["resolved 42"]);

        await runAllTimers();
        await microTick(); // wait for the inner promise
        expect.verifySteps(["myFunc", "resolved 44"]);
    });
});

describe("throttleForAnimation", () => {
    test("single call is executed immediately", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
        });
        throttledFn(1);
        expect.verifySteps(["1"]);

        await runAllTimers();
        expect.verifySteps([]);
    });

    test("successive calls", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
        });
        throttledFn(1);
        expect.verifySteps(["1"]);

        throttledFn(2);
        throttledFn(3);
        expect.verifySteps([]);

        await runAllTimers();
        expect.verifySteps(["3"]);
    });

    test("successive calls (more precise timing)", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
        });
        throttledFn(1);
        expect.verifySteps(["1"]);

        await animationFrame();
        throttledFn(2);
        expect.verifySteps(["2"]);

        throttledFn(3);
        throttledFn(4);
        await animationFrame();
        expect.verifySteps(["4"]);

        await runAllTimers();
        expect.verifySteps([]);
    });

    test("can be cancelled", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
        });
        throttledFn(1);
        expect.verifySteps(["1"]);

        throttledFn(2);
        throttledFn(3);
        throttledFn.cancel();
        await runAllTimers();
        expect.verifySteps([]);
    });
});

describe("throttleForAnimationScrollEvent", () => {
    test("scroll loses target", async () => {
        let throttled = new Deferred();
        const throttledFn = throttleForAnimation((val, targetEl) => {
            // In Chrome, the currentTarget of scroll events is lost after the
            // event was handled, it is therefore null here.
            // Because of this, if it is needed, it must be included in the
            // callback signature.
            const nodeName = val && val.currentTarget && val.currentTarget.nodeName;
            const targetName = targetEl && targetEl.nodeName;
            expect.step(
                `throttled function called with ${nodeName} in event, but ${targetName} in parameter`
            );
            throttled.resolve();
        });

        const el = document.createElement("div");
        el.style = "position: absolute; overflow: scroll; height: 100px; width: 100px;";
        const childEl = document.createElement("div");
        childEl.style = "height: 200px; width: 200px;";
        let scrolled = new Deferred();
        el.appendChild(childEl);
        el.addEventListener("scroll", (ev) => {
            expect.step("before scroll");
            throttledFn(ev, ev.currentTarget);
            expect.step("after scroll");
            scrolled.resolve();
        });
        getFixture().appendChild(el);
        el.scrollBy(1, 1);
        el.scrollBy(2, 2);
        await scrolled;
        await throttled;

        expect.verifySteps([
            "before scroll",
            "throttled function called with DIV in event, but DIV in parameter",
            "after scroll",
        ]);

        throttled = new Deferred();
        scrolled = new Deferred();
        el.scrollBy(3, 3);
        await scrolled;
        expect.verifySteps([
            "before scroll",
            // Further call is delayed.
            "after scroll",
        ]);
        await throttled;
        expect.verifySteps(["throttled function called with null in event, but DIV in parameter"]);
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
        const component = await mountWithCleanup(TestComponent);
        expect.verifySteps([]);
        expect("button.c").toHaveCount(1);

        await click(`button.c`);
        await advanceTime(900);
        expect.verifySteps([]);

        await advanceTime(200);
        expect.verifySteps(["debounced"]);

        await click(`button.c`);
        await advanceTime(900);
        expect.verifySteps([]);

        destroy(component);
        await advanceTime(200);
        expect.verifySteps([]);
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
        const component = await mountWithCleanup(TestComponent);
        expect.verifySteps([]);
        expect(`button.c`).toHaveCount(1);

        await click(`button.c`);
        await advanceTime(900);
        expect.verifySteps([]);

        await advanceTime(200);
        expect.verifySteps(["debounced: hello"]);

        await click(`button.c`);
        await advanceTime(900);
        expect.verifySteps([]);

        destroy(component);
        expect.verifySteps(["debounced: hello"]);
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
        const component = await mountWithCleanup(TestComponent);
        expect.verifySteps([]);
        expect(`button.c`).toHaveCount(1);

        await click(`button.c`);
        await advanceTime(900);
        expect.verifySteps([]);

        await advanceTime(200);
        expect.verifySteps(["debounced"]);

        destroy(component);
        await advanceTime(1000);
        expect.verifySteps([]);
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
        const component = await mountWithCleanup(TestComponent);
        expect.verifySteps([]);
        expect(`button.c`).toHaveCount(1);

        // Without destroy
        await click(`button.c`);
        expect.verifySteps(["throttled"]);

        await click(`button.c`);
        expect.verifySteps([]);

        await animationFrame();
        expect.verifySteps(["throttled"]);

        // Clean restart
        await runAllTimers();
        expect.verifySteps([]);

        // With destroy
        await click(`button.c`);
        expect.verifySteps(["throttled"]);

        await click(`button.c`);
        expect.verifySteps([]);

        destroy(component);
        await animationFrame();
        expect.verifySteps([]);
    });
});
