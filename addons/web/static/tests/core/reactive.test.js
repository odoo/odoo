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
        expect.verifySteps(["counter: 1"]);
        bus.trigger("change");
        expect(obj.counter).toBe(2);
        expect.verifySteps([
            // The mutation in the event handler was missed by the reactivity, this is because
            // the `this` in the event handler is captured during construction and is not reactive
        ]);
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
        expect.verifySteps(["counter: 1"]);
        bus.trigger("change");
        expect(obj.counter).toBe(2);
        expect.verifySteps(["counter: 2"]);
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
        expect.verifySteps([]);
        source.counter++;
        expect.verifySteps(["doubleCounter: 4"]);
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
        expect.verifySteps([]);
        source.subObj.counter++;
        expect(derived.doubleCounter).toBe(4);
        // reactive gets notified even for computed properties dervied from nested objects
        expect.verifySteps(["doubleCounter: 4"]);
    });
});
