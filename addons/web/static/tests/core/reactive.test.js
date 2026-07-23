import { after, animationFrame, describe, expect, microTick, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import { Component, EventBus, effect, props, proxy, types as t, useEffect, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Reactive } from "@web/core/utils/reactive";

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

        const obj = proxy(new MyReactiveClass());
        after(
            effect(() => {
                expect.step(`counter: ${obj.counter}`);
            })
        );
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
        const obj = proxy(new MyReactiveClass());
        after(
            effect(() => {
                expect.step(`counter: ${obj.counter}`);
            })
        );
        expect.verifySteps(["counter: 0"]);

        obj.counter++;
        await microTick();
        expect.verifySteps(["counter: 1"]);

        bus.trigger("change");
        await microTick();
        expect(obj.counter).toBe(2);
        expect.verifySteps(["counter: 2"]);
    });
});

describe("component props", () => {
    test("auto-alike arrow function prop should not retrigger renders and not retrigger useEffect if render", async () => {
        const testState = proxy({
            parentRender: 0,
            somethingElse: 0,
        });
        let childRenderCount = 0;
        let effectCount = 0;

        class Child extends Component {
            props = props({
                callback: t.function(),
                somethingElse: t.number(),
            });
            static template = xml`<span class="child" t-out="this.displayedValue"/>`;

            setup() {
                useEffect(() => this.props.callback());
            }

            get displayedValue() {
                childRenderCount++;
                return this.props.somethingElse;
            }
        }

        class Parent extends Component {
            static components = { Child };
            static template = xml`
                <div class="parent" t-att-data-parent-render="this.state.parentRender">
                    <Child
                        callback="() => this.onCallback()"
                        somethingElse="this.state.somethingElse"
                    />
                </div>
            `;

            state = testState;

            onCallback() {
                effectCount++;
            }
        }

        await mountWithCleanup(Parent);
        expect(queryFirst(".parent").dataset.parentRender).toBe("0");
        expect(queryFirst(".child")).toHaveText("0");
        expect(childRenderCount).toBe(1);
        expect(effectCount).toBe(1);

        // The arrow function is recreated, but its automatic alike behavior
        // skips the child render.
        testState.parentRender++;
        await animationFrame();
        expect(queryFirst(".parent").dataset.parentRender).toBe("1");
        expect(queryFirst(".child")).toHaveText("0");
        expect(childRenderCount).toBe(1);
        expect(effectCount).toBe(1);

        // Updating another prop could re-render the child but without
        // triggering the effect as the callback did not really change.
        testState.somethingElse++;
        await animationFrame();
        expect(queryFirst(".parent").dataset.parentRender).toBe("1");
        expect(queryFirst(".child")).toHaveText("1");
        expect(childRenderCount).toBe(2);
        expect(effectCount).toBe(1);
    });
});
