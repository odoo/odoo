import { reactive } from "@web/owl2/utils";
import { describe, expect, test } from "@odoo/hoot";
import { EventBus } from "@odoo/owl";
import { Reactive, effect } from "@web/core/utils/reactive";

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

describe("effect", () => {
    test("effect runs once immediately", async () => {
        const state = reactive({ counter: 0 });
        expect.verifySteps([]);
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state]
        );
        expect.verifySteps(["counter: 0"]);
    });

    test("effect runs when reactive deps change", async () => {
        const state = reactive({ counter: 0 });
        expect.verifySteps([]);
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state]
        );
        // effect runs immediately
        expect.verifySteps(["counter: 0"]);

        state.counter++;
        // first mutation runs the effect
        expect.verifySteps(["counter: 1"]);

        state.counter++;
        // subsequent mutations run the effect
        expect.verifySteps(["counter: 2"]);
    });

    test("Original reactive callback is not subscribed to keys observed by effect", async () => {
        let reactiveCallCount = 0;
        const state = reactive(
            {
                counter: 0,
            },
            () => reactiveCallCount++
        );
        expect.verifySteps([]);
        expect(reactiveCallCount).toBe(0);
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state]
        );
        expect.verifySteps(["counter: 0"]);
        expect(reactiveCallCount).toBe(0, {
            message: "did not call the original reactive's callback",
        });
        state.counter = 1;
        expect.verifySteps(["counter: 1"]);
        expect(reactiveCallCount).toBe(0, {
            message: "did not call the original reactive's callback",
        });
        state.counter; // subscribe the original reactive
        state.counter = 2;
        expect.verifySteps(["counter: 2"]);
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

        expect.verifySteps(["counter: 0"]);
        state.counter = 1;
        expect.verifySteps(["counter: 1"]);
        state.unobserved = 1;
        expect.verifySteps([]);
    });
});
