import { describe, expect, test } from "@odoo/hoot";
import { EventBus, reactive } from "@odoo/owl";
import { Reactive, effect, withComputedProperties } from "@web/core/utils/reactive";

describe.current.tags("headless");

describe("class", () => {
    test("callback registered without Reactive class constructor will not notify", async () => {
        // This test exists to showcase why we need the Reactive class
        const bus = new EventBus();
        class MyReactiveClass {
            constructor() {
                this.counter = 0;
                bus.addEventListener("change", () => this.counter++);
            }
        }

        const obj = reactive(new MyReactiveClass(), () => {
            expect.step(`counter: ${obj.counter}`);
        });

        obj.counter; // initial subscription to counter
        obj.counter++;
        expect(["counter: 1"]).toVerifySteps();
        bus.trigger("change");
        expect(obj.counter).toBe(2);
        expect([
            // The mutation in the event handler was missed by the reactivity, this is because
            // the `this` in the event handler is captured during construction and is not reactive
        ]).toVerifySteps();
    });

    test("callback registered in Reactive class constructor will notify", async () => {
        const bus = new EventBus();
        class MyReactiveClass extends Reactive {
            constructor() {
                super();
                this.counter = 0;
                bus.addEventListener("change", () => this.counter++);
            }
        }
        const obj = reactive(new MyReactiveClass(), () => {
            expect.step(`counter: ${obj.counter}`);
        });
        obj.counter; // initial subscription to counter
        obj.counter++;
        expect(["counter: 1"]).toVerifySteps();
        bus.trigger("change");
        expect(obj.counter).toBe(2);
        expect(["counter: 2"]).toVerifySteps();
    });
});

describe("effect", () => {
    test("effect runs once immediately", async () => {
        const state = reactive({ counter: 0 });
        expect([]).toVerifySteps();
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state]
        );
        expect(["counter: 0"]).toVerifySteps();
    });

    test("effect runs when reactive deps change", async () => {
        const state = reactive({ counter: 0 });
        expect([]).toVerifySteps();
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state]
        );
        expect(["counter: 0"]).toVerifySteps({
            message: "effect runs immediately",
        });

        state.counter++;
        expect(["counter: 1"]).toVerifySteps({
            message: "first mutation runs the effect",
        });

        state.counter++;
        expect(["counter: 2"]).toVerifySteps({
            message: "subsequent mutations run the effect",
        });
    });

    test("Original reactive callback is not subscribed to keys observed by effect", async () => {
        let reactiveCallCount = 0;
        const state = reactive(
            {
                counter: 0,
            },
            () => reactiveCallCount++
        );
        expect([]).toVerifySteps();
        expect(reactiveCallCount).toBe(0);
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state]
        );
        expect(["counter: 0"]).toVerifySteps();
        expect(reactiveCallCount).toBe(0, {
            message: "did not call the original reactive's callback",
        });
        state.counter = 1;
        expect(["counter: 1"]).toVerifySteps();
        expect(reactiveCallCount).toBe(0, {
            message: "did not call the original reactive's callback",
        });
        state.counter; // subscribe the original reactive
        state.counter = 2;
        expect(["counter: 2"]).toVerifySteps();
        expect(reactiveCallCount).toBe(1, {
            message: "the original callback was called because it is subscribed independently",
        });
    });

    test("mutating keys not observed by the effect doesn't cause it to run", async () => {
        const state = reactive({ counter: 0, unobserved: 0 });
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state]
        );

        expect(["counter: 0"]).toVerifySteps();
        state.counter = 1;
        expect(["counter: 1"]).toVerifySteps();
        state.unobserved = 1;
        expect([]).toVerifySteps();
    });
});

describe("withComputedProperties", () => {
    test("computed properties are set immediately", async () => {
        const source = reactive({ counter: 1 });
        const derived = withComputedProperties(reactive({}), [source], {
            doubleCounter(source) {
                return source.counter * 2;
            },
        });
        expect(derived.doubleCounter).toBe(2);
    });

    test("computed properties are recomputed when dependencies change", async () => {
        const source = reactive({ counter: 1 });
        const derived = withComputedProperties(reactive({}), [source], {
            doubleCounter(source) {
                return source.counter * 2;
            },
        });
        expect(derived.doubleCounter).toBe(2);
        source.counter++;
        expect(derived.doubleCounter).toBe(4);
    });

    test("can observe computed properties", async () => {
        const source = reactive({ counter: 1 });
        const derived = withComputedProperties(reactive({}), [source], {
            doubleCounter(source) {
                return source.counter * 2;
            },
        });
        const observed = reactive(derived, () => {
            expect.step(`doubleCounter: ${observed.doubleCounter}`);
        });
        observed.doubleCounter; // subscribe to doubleCounter
        expect([]).toVerifySteps();
        source.counter++;
        expect(["doubleCounter: 4"]).toVerifySteps();
    });

    test("computed properties can use nested objects", async () => {
        const source = reactive({ subObj: { counter: 1 } });
        const derived = withComputedProperties(reactive({}), [source], {
            doubleCounter(source) {
                return source.subObj.counter * 2;
            },
        });
        const observed = reactive(derived, () => {
            expect.step(`doubleCounter: ${observed.doubleCounter}`);
        });
        observed.doubleCounter; // subscribe to doubleCounter
        expect(derived.doubleCounter).toBe(2);
        expect([]).toVerifySteps();
        source.subObj.counter++;
        expect(derived.doubleCounter).toBe(4);
        expect(["doubleCounter: 4"]).toVerifySteps({
            message:
                "reactive gets notified even for computed properties dervied from nested objects",
        });
    });
});
