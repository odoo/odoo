// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, EventBus, reactive, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { effect, SignalStore } from "@web/core/utils/reactive";

describe.current.tags("headless");

test("SignalStore returns a reactive proxy of itself", () => {
    class Store extends SignalStore {
        n = 1;
    }
    const store = new Store();
    expect(store).toBeInstanceOf(Store);
    /** @type {any[]} */
    const seen = [];
    const tracked = reactive(store, () => seen.push(tracked.n));
    tracked.n;
    store.n = 2;
    expect(seen).toEqual([2]);
});

test("effect fires once eagerly, then on every dependency write", () => {
    const state = reactive({ n: 0 });
    /** @type {any[]} */
    const seen = [];
    effect((s) => seen.push(s.n), [state]);
    expect(seen).toEqual([0]);
    state.n = 1;
    state.n = 2;
    expect(seen).toEqual([0, 1, 2]);
});

test("the effect disposer stops further firing", () => {
    const state = reactive({ n: 0 });
    /** @type {any[]} */
    const seen = [];
    const dispose = effect((s) => seen.push(s.n), [state]);
    state.n = 1;
    dispose();
    state.n = 2;
    expect(seen).toEqual([0, 1]);
});

test("a subscription belongs to the proxy the read went through", async () => {
    const store = new (class extends SignalStore {
        first = "Ada";
        last = "Lovelace";
    })();
    const fullName = () => `${store.first} ${store.last}`;

    class Name extends Component {
        static template = xml`<span t-out="this.fullName()"/>`;
        static props = {};
        setup() {
            useState(store);
            this.fullName = fullName;
        }
    }

    await mountWithCleanup(Name);
    expect("span").toHaveText("Ada Lovelace");

    store.last = "Byron";
    await animationFrame();
    expect("span").toHaveText("Ada Lovelace", {
        message: "useState subscribes the component, but this read bypassed that proxy",
    });
    expect(fullName()).toBe("Ada Byron", {
        message: "the value is current; only the subscription is absent",
    });
});

test("reading the same state through the component's own proxy does subscribe", async () => {
    const store = new (class extends SignalStore {
        first = "Ada";
        last = "Lovelace";
    })();

    class Name extends Component {
        static template = xml`<span t-out="this.fullName"/>`;
        static props = {};
        /** @type {typeof store} */
        state;
        setup() {
            this.state = useState(store);
        }
        get fullName() {
            return `${this.state.first} ${this.state.last}`;
        }
    }

    await mountWithCleanup(Name);
    expect("span").toHaveText("Ada Lovelace");

    store.last = "Byron";
    await animationFrame();
    expect("span").toHaveText("Ada Byron");
});

describe("class", () => {
    test("callback registered without SignalStore class constructor will not notify", async () => {
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

        obj.counter;
        obj.counter++;
        expect.verifySteps(["counter: 1"]);
        bus.trigger("change");
        expect(obj.counter).toBe(2);
        expect.verifySteps([]);
    });

    test("callback registered in SignalStore class constructor will notify", async () => {
        const bus = new EventBus();
        class MyReactiveClass extends SignalStore {
            constructor() {
                super();
                this.counter = 0;
                bus.addEventListener("change", () => this.counter++);
            }
        }
        const obj = reactive(new MyReactiveClass(), () => {
            expect.step(`counter: ${obj.counter}`);
        });
        obj.counter;
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
            [state],
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
            [state],
        );
        expect.verifySteps(["counter: 0"]);

        state.counter++;
        expect.verifySteps(["counter: 1"]);

        state.counter++;
        expect.verifySteps(["counter: 2"]);
    });

    test("Original reactive callback is not subscribed to keys observed by effect", async () => {
        let reactiveCallCount = 0;
        const state = reactive(
            {
                counter: 0,
            },
            () => reactiveCallCount++,
        );
        expect.verifySteps([]);
        expect(reactiveCallCount).toBe(0);
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state],
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
        state.counter;
        state.counter = 2;
        expect.verifySteps(["counter: 2"]);
        expect(reactiveCallCount).toBe(1, {
            message:
                "the original callback was called because it is subscribed independently",
        });
    });

    test("mutating keys not observed by the effect doesn't cause it to run", async () => {
        const state = reactive({ counter: 0, unobserved: 0 });
        effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state],
        );

        expect.verifySteps(["counter: 0"]);
        state.counter = 1;
        expect.verifySteps(["counter: 1"]);
        state.unobserved = 1;
        expect.verifySteps([]);
    });

    test("effect returns a disposer that stops future notifications", async () => {
        const state = reactive({ counter: 0 });
        const dispose = effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state],
        );
        expect(dispose).toBeInstanceOf(Function);
        expect.verifySteps(["counter: 0"]);

        state.counter++;
        expect.verifySteps(["counter: 1"]);

        dispose();
        state.counter++;
        expect.verifySteps([]);
    });

    test("effect still runs, notifies and disposes", async () => {
        const state = reactive({ counter: 0 });
        const dispose = effect(
            (state) => {
                expect.step(`counter: ${state.counter}`);
            },
            [state],
        );
        expect.verifySteps(["counter: 0"]);

        state.counter++;
        expect.verifySteps(["counter: 1"]);

        dispose();
        state.counter++;
        expect.verifySteps([]);
    });
});
