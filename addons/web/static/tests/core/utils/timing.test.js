// @ts-check

import { describe, destroy, expect, getFixture, test } from "@odoo/hoot";
import { click, tick } from "@odoo/hoot-dom";
import {
    advanceFrame,
    advanceTime,
    animationFrame,
    Deferred,
    freezeTime,
    microTick,
    runAllTimers,
} from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    batched,
    debounce,
    throttleForAnimation,
    useDebounced,
    useThrottleForAnimation,
} from "@web/core/utils/timing";

describe.current.tags("headless");

describe("batched", () => {
    for (const asynchronous of [false, true]) {
        test(`a ${asynchronous ? "rejecting" : "throwing"} synchronizer rejects the batch and permits recovery`, async () => {
            patchWithCleanup(console, { error: () => {} });
            const failure = new Error("synchronization failed");
            let shouldFail = true;
            const fn = batched(
                (value) => value * 2,
                () => {
                    if (shouldFail) {
                        if (asynchronous) {
                            return Promise.reject(failure);
                        }
                        throw failure;
                    }
                    return Promise.resolve();
                },
            );
            const outcomes = await Promise.allSettled([fn(1), fn(2)]);
            expect(outcomes).toEqual([
                { status: "rejected", reason: failure },
                { status: "rejected", reason: failure },
            ]);
            shouldFail = false;
            expect(await fn(3)).toBe(6);
        });
    }

    test("a throwing callback is mirrored to console.error and still rejects", async () => {
        const errors = [];
        patchWithCleanup(console, {
            error: (...args) => errors.push(args),
        });
        const boom = new Error("boom");
        const fn = batched(() => {
            throw boom;
        });
        await expect(fn()).rejects.toThrow("boom");
        expect(errors).toHaveLength(1);
        expect(errors[0][0]).toBe(boom);
    });

    test("every caller in a batch is settled after the callback ran, not before", async () => {
        let ran = 0;
        const fn = batched(() => ran++, animationFrame);

        fn();
        const later = fn();

        await later;
        expect(ran).toBe(1);
    });

    test("the returned promise carries the callback's resolved value", async () => {
        const fn = batched((n) => n * 2);
        expect(await fn(21)).toBe(42);
    });

    test("an async callback is awaited before the batch settles", async () => {
        let done = false;
        const fn = batched(async () => {
            await animationFrame();
            done = true;
            return "ok";
        });
        expect(await fn()).toBe("ok");
        expect(done).toBe(true);
    });

    test("a throwing callback rejects every caller in the batch", async () => {
        patchWithCleanup(console, { error: () => {} });
        const fn = batched(() => {
            throw new Error("boom");
        }, animationFrame);
        const first = fn();
        const second = fn();
        await expect(first).rejects.toThrow("boom");
        await expect(second).rejects.toThrow("boom");
    });

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
        const fn = batched(() => ++n === 1 && fn());
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await Promise.resolve();
        expect(n).toBe(1);

        await Promise.resolve();
        expect(n).toBe(2);

        await Promise.resolve();
        expect(n).toBe(2);
    });

    test("calling batched function from within the callback is not treated as part of the original batch (synchronize at animationFrame)", async () => {
        let n = 0;
        const fn = batched(() => ++n === 1 && fn(), animationFrame);
        expect(n).toBe(0);

        fn();
        expect(n).toBe(0);

        await animationFrame();
        expect(n).toBe(1);

        await animationFrame();
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

        await tick();
        expect(n).toBe(1);

        await tick();
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
    test("a throwing delay leaves the previous invocation scheduled and permits recovery", async () => {
        let fail = false;
        const calls = [];
        const fn = debounce(
            (value) => {
                calls.push(value);
                return value;
            },
            () => {
                if (fail) {
                    throw new Error("delay failed");
                }
                return 10;
            },
        );
        const previous = fn(1);
        fail = true;
        await expect(fn(2)).rejects.toThrow("delay failed");
        await advanceTime(10);
        expect(await previous).toBe(1);
        expect(calls).toEqual([1]);
        fail = false;
        const next = fn(3);
        await advanceTime(10);
        expect(await next).toBe(3);
        expect(calls).toEqual([1, 3]);
    });

    for (const flush of [false, true]) {
        test(`a ${flush ? "flushed" : "trailing"} callback can schedule the next invocation`, async () => {
            const calls = [];
            /** @type {Promise<number> | undefined} */
            let next;
            const fn = debounce(function (value) {
                calls.push([this.name, value]);
                if (value === 1) {
                    next = fn.call({ name: "second" }, 2);
                }
                return value;
            }, 10);
            const first = fn.call({ name: "first" }, 1);
            if (flush) {
                fn.cancel(true);
            } else {
                await advanceTime(10);
            }
            expect(await first).toBe(1);
            await advanceTime(10);
            expect(await next).toBe(2);
            expect(calls).toEqual([
                ["first", 1],
                ["second", 2],
            ]);
        });
    }

    test("a leading callback schedules reentrant work on the trailing edge", async () => {
        const calls = [];
        /** @type {Promise<number> | undefined} */
        let next;
        const fn = debounce(
            (value) => {
                calls.push(value);
                if (value === 1) {
                    next = fn(2);
                }
                return value;
            },
            10,
            { leading: true, trailing: true },
        );
        expect(await fn(1)).toBe(1);
        expect(calls).toEqual([1]);
        await advanceTime(10);
        expect(await next).toBe(2);
        expect(calls).toEqual([1, 2]);
    });

    test("each call restarts the wait, so the first deadline is abandoned", async () => {
        const myFunc = (/** @type {number} */ n) => {
            expect.step(`myFunc:${n}`);
            return n;
        };
        const debounced = debounce(myFunc, 1000);

        debounced(1);
        await advanceTime(600);
        expect.verifySteps([], { message: "600ms is short of the 1000ms wait" });

        debounced(2);
        await advanceTime(600);
        expect.verifySteps([], {
            message: "the second call must abandon the first call's deadline",
        });

        await advanceTime(400);
        expect.verifySteps(["myFunc:2"], {
            message: "one execution, 1000ms after the LAST call, with its arguments",
        });

        await runAllTimers();
        expect.verifySteps([], { message: "and no second execution is left armed" });
    });

    test("debounce on a sync function settles superseded calls too", async () => {
        const myFunc = () => {
            expect.step("myFunc");
            return 42;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then((x) => {
            expect.step("superseded " + x);
        });
        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect.verifySteps([]);

        await advanceTime(3000);
        expect.verifySteps(["myFunc", "superseded 42", "resolved 42"]);
    });

    test("debounce on an async function settles superseded calls too", async () => {
        const imSearchDef = new Deferred();
        const myFunc = () => {
            expect.step("myFunc");
            return imSearchDef;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then((x) => {
            expect.step("superseded " + x);
        });
        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect.verifySteps([]);

        await advanceTime(3000);
        expect.verifySteps(["myFunc"]);

        imSearchDef.resolve(42);
        await microTick();
        await microTick();

        expect.verifySteps(["superseded 42", "resolved 42"]);
    });

    test("debounce propagates a rejection to every superseded call", async () => {
        const myFunc = () => {
            expect.step("myFunc");
            throw new Error("boom");
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().catch((e) => expect.step("rejected1 " + e.message));
        myDebouncedFunc().catch((e) => expect.step("rejected2 " + e.message));
        expect.verifySteps([]);

        await advanceTime(3000);
        expect.verifySteps(["myFunc", "rejected1 boom", "rejected2 boom"]);
    });

    test("debounce propagates an async rejection to every pending call", async () => {
        const imSearchDef = new Deferred();
        const myFunc = () => {
            expect.step("myFunc");
            return imSearchDef;
        };
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().catch((e) => expect.step("rejected1 " + e));
        myDebouncedFunc().catch((e) => expect.step("rejected2 " + e));

        await advanceTime(3000);
        expect.verifySteps(["myFunc"]);

        imSearchDef.reject("nope");
        await microTick();
        await microTick();
        expect.verifySteps(["rejected1 nope", "rejected2 nope"]);
    });

    test("cancel() releases a pending awaiter instead of hanging", async () => {
        const myFunc = () => expect.step("myFunc");
        const myDebouncedFunc = debounce(myFunc, 3000);
        myDebouncedFunc().then((v) => expect.step("settled " + v));
        myDebouncedFunc.cancel();
        await microTick();
        await microTick();
        expect.verifySteps(["settled undefined"]);
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

        await microTick();
        await microTick();

        expect.verifySteps(["resolved 42"]);

        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        await runAllTimers();
        expect.verifySteps(["resolved undefined"]);

        myDebouncedFunc().then((x) => {
            expect.step("resolved " + x);
        });
        expect.verifySteps(["myFunc"]);

        await microTick();
        await microTick();
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
        expect.verifySteps([]);

        myDebouncedFunc();
        await runAllTimers();
        expect.verifySteps(["myFunc"]);
    });

    test("debounce with leading and trailing", async () => {
        const myFunc = (lastValue) => {
            expect.step("myFunc");
            return lastValue;
        };
        const myDebouncedFunc = debounce(myFunc, 3000, {
            leading: true,
            trailing: true,
        });
        myDebouncedFunc(42).then((x) => expect.step("resolved " + x));
        myDebouncedFunc(43).then((x) => expect.step("resolved " + x));
        myDebouncedFunc(44).then((x) => expect.step("resolved " + x));
        expect.verifySteps(["myFunc"]);
        await microTick();
        await microTick();
        expect.verifySteps(["resolved 42"]);

        await runAllTimers();
        await microTick();
        expect.verifySteps(["myFunc", "resolved 44", "resolved 44"]);
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

    test("a rejected leading call rejects the returned promise (not swallowed)", async () => {
        const throttledFn = throttleForAnimation(() =>
            Promise.reject(new Error("boom")),
        );
        /** @type {Error} */
        let caught;
        await throttledFn().catch((error) => (caught = error));
        expect(caught).toBeInstanceOf(Error);
        expect(caught.message).toBe("boom");
    });

    test("a rejected trailing call rejects its awaiter", async () => {
        let calls = 0;
        const throttledFn = throttleForAnimation(() => {
            calls++;
            return calls === 1 ? "ok" : Promise.reject(new Error("boom2"));
        });
        throttledFn();
        const trailing = throttledFn();
        /** @type {Error} */
        let caught;
        const settled = Promise.resolve(trailing).catch((error) => (caught = error));
        await runAllTimers();
        await settled;
        expect(caught).toBeInstanceOf(Error);
        expect(caught.message).toBe("boom2");
    });

    test("cancel() releases the pending trailing call's awaiter", async () => {
        const throttledFn = throttleForAnimation((value) => {
            expect.step(`${value}`);
            return value;
        });
        throttledFn(1);
        expect.verifySteps(["1"]);

        throttledFn(2).then((v) => expect.step(`settled ${v}`));
        throttledFn.cancel();
        await runAllTimers();
        expect.verifySteps(["settled undefined"]);
    });
});

describe("throttleForAnimationScrollEvent", () => {
    test("scroll loses target", async () => {
        // The frame requested inside a scroll listener runs in the SAME
        // rendering update, after the scroll steps, so on a real clock the
        // throttle's frame is spent before the next scroll event arrives and
        // nothing is left to coalesce. Freeze the clock: frames then advance
        // only through advanceFrame(), which is what the test is about.
        freezeTime();
        let throttled = new Deferred();
        const throttledFn = throttleForAnimation((val, targetEl) => {
            // Whether `val.currentTarget` still reads after dispatch is the
            // browser's business (Chrome 153 keeps it on a trusted scroll
            // event, earlier versions and synthetic events null it), which is
            // exactly why the target travels as a parameter; assert that.
            const targetName = targetEl && targetEl.nodeName;
            expect.step(`throttled function called with ${targetName} in parameter`);
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
            "throttled function called with DIV in parameter",
            "after scroll",
        ]);

        throttled = new Deferred();
        scrolled = new Deferred();
        // a second scroll in the same frame: scrollBy would dispatch it in the
        // next frame, after the animation-frame callback has already run and
        // released the throttle, so it is dispatched here, before that stage
        el.dispatchEvent(new Event("scroll"));
        await scrolled;
        expect.verifySteps(["before scroll", "after scroll"]);
        await advanceFrame(1);
        await throttled;
        expect.verifySteps(["throttled function called with DIV in parameter"]);
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
                this.debounced = useDebounced(
                    (p) => expect.step(`debounced: ${p}`),
                    1000,
                    {
                        execBeforeUnmount: true,
                    },
                );
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
                this.throttled = useThrottleForAnimation(() =>
                    expect.step("throttled"),
                );
            }
        }
        const component = await mountWithCleanup(TestComponent);
        expect.verifySteps([]);
        expect(`button.c`).toHaveCount(1);

        await click(`button.c`);
        expect.verifySteps(["throttled"]);

        await click(`button.c`);
        expect.verifySteps([]);

        await animationFrame();
        expect.verifySteps(["throttled"]);

        await runAllTimers();
        expect.verifySteps([]);

        await click(`button.c`);
        expect.verifySteps(["throttled"]);

        await click(`button.c`);
        expect.verifySteps([]);

        destroy(component);
        await animationFrame();
        expect.verifySteps([]);
    });
});
