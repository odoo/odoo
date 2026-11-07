/** @odoo-module */

import { EventBus, reactive } from "@odoo/owl";
import { Reactive, effect, withComputedProperties } from "@web/core/utils/reactive";

QUnit.module("Reactive utils", () => {
    QUnit.module("Reactive class", () => {
        QUnit.test(
            "callback registered without Reactive class constructor will not notify",
            (assert) => {
                // This test exists to showcase why we need the Reactive class
                const bus = new EventBus();
                class MyReactiveClass {
                    constructor() {
                        this.counter = 0;
                        bus.addEventListener("change", () => this.counter++);
                    }
                }
                const obj = reactive(new MyReactiveClass(), () => {
                    assert.step(`counter: ${obj.counter}`);
                });
                obj.counter; // initial subscription to counter
                obj.counter++;
                assert.verifySteps(["counter: 1"]);
                bus.trigger("change");
                assert.equal(obj.counter, 2);
                assert.verifySteps([
                    // The mutation in the event handler was missed by the reactivity, this is because
                    // the `this` in the event handler is captured during construction and is not reactive
                ]);
            }
        );

        QUnit.test("callback registered in Reactive class constructor will notify", (assert) => {
            const bus = new EventBus();
            class MyReactiveClass extends Reactive {
                constructor() {
                    super();
                    this.counter = 0;
                    bus.addEventListener("change", () => this.counter++);
                }
            }
            const obj = reactive(new MyReactiveClass(), () => {
                assert.step(`counter: ${obj.counter}`);
            });
            obj.counter; // initial subscription to counter
            obj.counter++;
            assert.verifySteps(["counter: 1"]);
            bus.trigger("change");
            assert.equal(obj.counter, 2);
            assert.verifySteps(["counter: 2"]);
        });
    });

    QUnit.module("effect", () => {
        QUnit.test("effect runs once immediately", (assert) => {
            const state = reactive({ counter: 0 });
            assert.verifySteps([]);
            effect(
                (state) => {
                    assert.step(`counter: ${state.counter}`);
                },
                [state]
            );
            assert.verifySteps(["counter: 0"]);
        });

        QUnit.test("effect runs when reactive deps change", (assert) => {
            const state = reactive({ counter: 0 });
            assert.verifySteps([]);
            effect(
                (state) => {
                    assert.step(`counter: ${state.counter}`);
                },
                [state]
            );
            assert.verifySteps(["counter: 0"], "effect runs immediately");
            state.counter++;
            assert.verifySteps(["counter: 1"], "first mutation runs the effect");
            state.counter++;
            assert.verifySteps(["counter: 2"], "subsequent mutations run the effect");
        });

        QUnit.test(
            "Original reactive callback is not subscribed to keys observed by effect",
            (assert) => {
                let reactiveCallCount = 0;
                const state = reactive(
                    {
                        counter: 0,
                    },
                    () => reactiveCallCount++
                );
                assert.verifySteps([]);
                assert.equal(reactiveCallCount, 0);
                effect(
                    (state) => {
                        assert.step(`counter: ${state.counter}`);
                    },
                    [state]
                );
                assert.verifySteps(["counter: 0"]);
                assert.equal(reactiveCallCount, 0, "did not call the original reactive's callback");
                state.counter = 1;
                assert.verifySteps(["counter: 1"]);
                assert.equal(reactiveCallCount, 0, "did not call the original reactive's callback");
                state.counter; // subscribe the original reactive
                state.counter = 2;
                assert.verifySteps(["counter: 2"]);
                assert.equal(
                    reactiveCallCount,
                    1,
                    "the original callback was called because it is subscribed independently"
                );
            }
        );

        QUnit.test("mutating keys not observed by the effect doesn't cause it to run", (assert) => {
            const state = reactive({ counter: 0, unobserved: 0 });
            effect(
                (state) => {
                    assert.step(`counter: ${state.counter}`);
                },
                [state]
            );
            assert.verifySteps(["counter: 0"]);
            state.counter = 1;
            assert.verifySteps(["counter: 1"]);
            state.unobserved = 1;
            assert.verifySteps([]);
        });
    });

    QUnit.module("withComputedProperties", () => {
        QUnit.test("computed properties are set immediately", (assert) => {
            const source = reactive({ counter: 1 });
            const derived = withComputedProperties(reactive({}), [source], {
                doubleCounter(source) {
                    return source.counter * 2;
                },
            });
            assert.equal(derived.doubleCounter, 2);
        });

        QUnit.test("computed properties are recomputed when dependencies change", (assert) => {
            const source = reactive({ counter: 1 });
            const derived = withComputedProperties(reactive({}), [source], {
                doubleCounter(source) {
                    return source.counter * 2;
                },
            });
            assert.equal(derived.doubleCounter, 2);
            source.counter++;
            assert.equal(derived.doubleCounter, 4);
        });

        QUnit.test("can observe computed properties", (assert) => {
            const source = reactive({ counter: 1 });
            const derived = withComputedProperties(reactive({}), [source], {
                doubleCounter(source) {
                    return source.counter * 2;
                },
            });
            const observed = reactive(derived, () => {
                assert.step(`doubleCounter: ${observed.doubleCounter}`);
            });
            observed.doubleCounter; // subscribe to doubleCounter
            assert.verifySteps([]);
            source.counter++;
            assert.verifySteps(["doubleCounter: 4"]);
        });

        QUnit.test("computed properties can use nested objects", (assert) => {
            const source = reactive({ subObj: { counter: 1 } });
            const derived = withComputedProperties(reactive({}), [source], {
                doubleCounter(source) {
                    return source.subObj.counter * 2;
                },
            });
            const observed = reactive(derived, () => {
                assert.step(`doubleCounter: ${observed.doubleCounter}`);
            });
            observed.doubleCounter; // subscribe to doubleCounter
            assert.equal(observed.doubleCounter, 2);
            assert.verifySteps([]);
            source.subObj.counter++;
            assert.equal(derived.doubleCounter, 4);
            assert.verifySteps(
                ["doubleCounter: 4"],
                "reactive gets notified even for computed properties dervied from nested objects"
            );
        });
    });
});
