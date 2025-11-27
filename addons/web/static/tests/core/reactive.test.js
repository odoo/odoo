import { describe, expect, microTick, test } from "@odoo/hoot";
import { effect, EventBus, reactive } from "@odoo/owl";
import { Reactive } from "@web/core/utils/reactive";

describe.current.tags("headless");

test("callback registered without Reactive class constructor will not notify", async () => {
    // This test exists to showcase why we need the Reactive class
    const bus = new EventBus();
    class MyReactiveClass {
        constructor() {
            this.counter = 0;
            bus.addEventListener("change", () => this.counter++);
        }
    }

    const obj = reactive(new MyReactiveClass());
    effect(() => {
        expect.step(`counter: ${obj.counter}`);
    });
    expect.verifySteps(["counter: 0"]);

    obj.counter++;
    await microTick();
    expect.verifySteps(["counter: 1"]);

    bus.trigger("change");
    await microTick();
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

    const obj = reactive(new MyReactiveClass());
    effect(() => {
        expect.step(`counter: ${obj.counter}`);
    });
    expect.verifySteps(["counter: 0"]);

    obj.counter++;
    await microTick();
    expect.verifySteps(["counter: 1"]);

    bus.trigger("change");
    await microTick();
    expect(obj.counter).toBe(2);
    expect.verifySteps(["counter: 2"]);
});
