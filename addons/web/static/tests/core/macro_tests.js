/** @odoo-module **/

import { MacroEngine } from "@web/core/macro";
import { getFixture, mockTimeout } from "../helpers/utils";

const { Component, xml, useState, mount } = owl;

let target, engine, mock;

QUnit.module(
    "macros",
    {
        beforeEach() {
            target = getFixture();
            engine = new MacroEngine(target);
            mock = mockTimeout();
        },
        afterEach() {
            if (engine.macros.size !== 0) {
                throw new Error("Some macro is still running after a test");
            }
        },
    },
    () => {
        class TestComponent extends Component {
            setup() {
                this.state = useState({ value: 0 });
            }
        }
        TestComponent.template = xml`
        <div class="counter">
             <button class="inc" t-on-click="() => this.state.value++">increment</button>
             <button class="dec" t-on-click="() => this.state.value--">decrement</button>
             <button class="double" t-on-click="() => this.state.value = 2*this.state.value">double</button>
             <span class="value"><t t-esc="state.value"/></span>
             <input />
        </div>`;

        QUnit.test("simple use", async function (assert) {
            await mount(TestComponent, target);

            const span = target.querySelector("span.value");
            assert.strictEqual(span.textContent, "0");

            engine.activate({
                name: "test",
                steps: [
                    {
                        trigger: "button.inc",
                        action: "click",
                    },
                ],
            });
            // default interval is 500
            await mock.advanceTime(300);
            assert.strictEqual(span.textContent, "0");
            await mock.advanceTime(300);
            assert.strictEqual(span.textContent, "1");
        });

        QUnit.test("multiple steps", async function (assert) {
            await mount(TestComponent, target);

            const span = target.querySelector("span.value");
            assert.strictEqual(span.textContent, "0");

            engine.activate({
                name: "test",
                steps: [
                    {
                        trigger: "button.inc",
                        action: "click",
                    },
                    {
                        trigger: () => {
                            return span.textContent === "1" ? span : null;
                        },
                    },
                    {
                        trigger: "button.inc",
                        action: "click",
                    },
                ],
            });
            await mock.advanceTime(500);
            assert.strictEqual(span.textContent, "1");
            await mock.advanceTime(500);
            assert.strictEqual(span.textContent, "2");
            await mock.advanceTime(500);
            assert.strictEqual(span.textContent, "2");
        });

        QUnit.test("can use a function as action", async function (assert) {
            await mount(TestComponent, target);
            let flag = false;
            engine.activate({
                name: "test",
                steps: [
                    {
                        trigger: "button.inc",
                        action: () => (flag = true),
                    },
                ],
            });
            assert.strictEqual(flag, false);
            await mock.advanceTime(600);
            assert.strictEqual(flag, true);
        });

        QUnit.test("can input values", async function (assert) {
            await mount(TestComponent, target);
            const input = target.querySelector("input");

            engine.activate({
                name: "test",
                steps: [
                    {
                        trigger: "div.counter input",
                        action: "text",
                        value: "aaron",
                    },
                ],
            });
            assert.strictEqual(input.value, "");
            await mock.advanceTime(600);
            assert.strictEqual(input.value, "aaron");
        });

        QUnit.test("a step can have no trigger", async function (assert) {
            await mount(TestComponent, target);
            const input = target.querySelector("input");

            engine.activate({
                name: "test",
                steps: [
                    { action: () => assert.step("1") },
                    { action: () => assert.step("2") },
                    {
                        trigger: "div.counter input",
                        action: "text",
                        value: "aaron",
                    },
                    { action: () => assert.step("3") },
                ],
            });
            assert.strictEqual(input.value, "");
            await mock.advanceTime(600);
            assert.strictEqual(input.value, "aaron");
            assert.verifySteps(["1", "2", "3"]);
        });

        QUnit.test("onStep function is called at each step", async function (assert) {
            await mount(TestComponent, target);

            const span = target.querySelector("span.value");
            assert.strictEqual(span.textContent, "0");

            engine.activate({
                name: "test",
                onStep: (el, step) => {
                    assert.step(step.info);
                },
                steps: [
                    { info: "1" },
                    {
                        info: "2",
                        trigger: "button.inc",
                        action: "click",
                    },
                ],
            });
            // default interval is 500
            await mock.advanceTime(600);
            assert.strictEqual(span.textContent, "1");
            assert.verifySteps(["1", "2"]);
        });

        QUnit.test("trigger can be a function returning an htmlelement", async function (assert) {
            await mount(TestComponent, target);

            const span = target.querySelector("span.value");
            assert.strictEqual(span.textContent, "0");

            engine.activate({
                name: "test",
                steps: [
                    {
                        trigger: () => target.querySelector("button.inc"),
                        action: "click",
                    },
                ],
            });
            // default interval is 500
            await mock.advanceTime(300);
            assert.strictEqual(span.textContent, "0");
            await mock.advanceTime(300);
            assert.strictEqual(span.textContent, "1");
        });

        QUnit.test("macro does not click on invisible element", async function (assert) {
            await mount(TestComponent, target);

            const span = target.querySelector("span.value");
            const button = target.querySelector("button.inc");
            assert.strictEqual(span.textContent, "0");

            engine.activate({
                name: "test",
                steps: [
                    {
                        trigger: "button.inc",
                        action: "click",
                    },
                ],
            });
            button.classList.add("d-none");

            await mock.advanceTime(500);
            assert.strictEqual(span.textContent, "0");
            await mock.advanceTime(500);
            assert.strictEqual(span.textContent, "0");
            button.classList.remove("d-none");
            await mock.advanceTime(500);

            assert.strictEqual(span.textContent, "1");
        });
    }
);
