/** @odoo-module **/

import { uiService } from "@web/core/ui/ui_service";
import {
    useAutofocus,
    useBus,
    useEffect,
    useListener,
    useService,
    onDestroyed,
} from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "../../helpers/mock_env";
import { click, getFixture, nextTick } from "../../helpers/utils";
import { registerCleanup } from "../../helpers/cleanup";

const { Component, mount, useState, xml } = owl;
const serviceRegistry = registry.category("services");

QUnit.module("utils", () => {
    QUnit.module("Hooks", () => {
        QUnit.module("useAutofocus");

        QUnit.test("useAutofocus: simple usecase", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    useAutofocus();
                }
            }
            MyComponent.template = xml`
                <span>
                    <input type="text" autofocus="" />
                </span>
            `;

            registry.category("services").add("ui", uiService);

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, { env, target });
            await nextTick();

            assert.strictEqual(document.activeElement, comp.el.querySelector("input"));

            comp.render();
            await nextTick();
            assert.strictEqual(document.activeElement, comp.el.querySelector("input"));

            comp.destroy();
        });

        QUnit.test("useAutofocus: simple usecase when input type is number", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    useAutofocus();
                }
            }
            MyComponent.template = xml`
                <span>
                    <input type="number" autofocus="" />
                </span>
            `;

            registry.category("services").add("ui", uiService);

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, { env, target });

            assert.strictEqual(document.activeElement, comp.el.querySelector("input"));

            comp.render();
            await nextTick();
            assert.strictEqual(document.activeElement, comp.el.querySelector("input"));

            comp.destroy();
        });

        QUnit.test("useAutofocus: conditional autofocus", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    this.forceFocus = useAutofocus();
                    this.showInput = true;
                }
            }
            MyComponent.template = xml`
                <span>
                    <input t-if="showInput" type="text" autofocus="" />
                </span>
            `;

            registry.category("services").add("ui", uiService);

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, { env, target });
            await nextTick();

            assert.strictEqual(document.activeElement, comp.el.querySelector("input"));

            comp.showInput = false;
            comp.forceFocus();
            comp.render();
            await nextTick();
            assert.notStrictEqual(document.activeElement, comp.el.querySelector("input"));

            comp.showInput = true;
            comp.forceFocus();
            comp.render();
            await nextTick();
            assert.strictEqual(document.activeElement, comp.el.querySelector("input"));

            comp.destroy();
        });

        QUnit.module("useBus");

        QUnit.test("useBus hook: simple usecase", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    useBus(this.env.bus, "test-event", this.myCallback);
                }
                myCallback() {
                    assert.step("callback");
                }
            }
            MyComponent.template = xml`<div/>`;

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, { env, target });
            env.bus.trigger("test-event");
            await nextTick();
            assert.verifySteps(["callback"]);

            comp.unmount();
            env.bus.trigger("test-event");
            await nextTick();
            assert.verifySteps([]);

            comp.destroy();
        });

        QUnit.module("useEffect");

        QUnit.test(
            "useEffect: effect runs on mount, is reapplied on patch, and is cleaned up on unmount and before reapplying",
            async function (assert) {
                assert.expect(7);

                let cleanupRun = 0;
                class MyComponent extends Component {
                    setup() {
                        this.state = useState({
                            value: 0,
                        });
                        useEffect(() => {
                            assert.step(`value is ${this.state.value}`);
                            return () =>
                                assert.step(
                                    `cleaning up for value = ${
                                        this.state.value
                                    } (cleanup ${cleanupRun++})`
                                );
                        });
                    }
                }
                MyComponent.template = xml`<div/>`;

                const env = await makeTestEnv();
                const target = getFixture();
                const component = await mount(MyComponent, { env, target });

                assert.step("before state mutation");
                component.state.value++;
                // Wait for an owl render
                await new Promise((resolve) => requestAnimationFrame(resolve));
                assert.step("after state mutation");
                await component.unmount();

                assert.verifySteps([
                    "value is 0",
                    "before state mutation",
                    // While one might expect value to be 0 at cleanup, because the value is
                    // read during cleanup from the state rather than captured by a dependency
                    // it already has the new value. Having this in business code is a symptom
                    // of a missing dependency and can lead to bugs.
                    "cleaning up for value = 1 (cleanup 0)",
                    "value is 1",
                    "after state mutation",
                    "cleaning up for value = 1 (cleanup 1)",
                ]);
            }
        );

        QUnit.test(
            "useEffect: dependencies prevent effects from rerunning when unchanged",
            async function (assert) {
                assert.expect(21);

                class MyComponent extends Component {
                    setup() {
                        this.state = useState({
                            a: 0,
                            b: 0,
                        });
                        useEffect(
                            (a) => {
                                assert.step(`Effect a: ${a}`);
                                return () => assert.step(`cleaning up for a: ${a}`);
                            },
                            () => [this.state.a]
                        );
                        useEffect(
                            (b) => {
                                assert.step(`Effect b: ${b}`);
                                return () => assert.step(`cleaning up for b: ${b}`);
                            },
                            () => [this.state.b]
                        );
                        useEffect(
                            (a, b) => {
                                assert.step(`Effect ab: {a: ${a}, b: ${b}}`);
                                return () => assert.step(`cleaning up for ab: {a: ${a}, b: ${b}}`);
                            },
                            () => [this.state.a, this.state.b]
                        );
                    }
                }
                MyComponent.template = xml`<div/>`;

                const env = await makeTestEnv();
                const target = getFixture();
                assert.step("before mount");
                const component = await mount(MyComponent, { env, target });
                assert.step("after mount");

                assert.step("before state mutation: a");
                component.state.a++;
                // Wait for an owl render
                await new Promise((resolve) => requestAnimationFrame(resolve));
                assert.step("after state mutation: a");

                assert.step("before state mutation: b");
                component.state.b++;
                // Wait for an owl render
                await new Promise((resolve) => requestAnimationFrame(resolve));
                assert.step("after state mutation: b");
                await component.unmount();

                assert.verifySteps([
                    // All effects run on mount
                    "before mount",
                    "Effect a: 0",
                    "Effect b: 0",
                    "Effect ab: {a: 0, b: 0}",
                    "after mount",

                    "before state mutation: a",
                    // Cleanups run in reverse order
                    "cleaning up for ab: {a: 0, b: 0}",
                    // Cleanup for b is not run
                    "cleaning up for a: 0",

                    "Effect a: 1",
                    // Effect b is not run
                    "Effect ab: {a: 1, b: 0}",
                    "after state mutation: a",

                    "before state mutation: b",
                    "cleaning up for ab: {a: 1, b: 0}",
                    "cleaning up for b: 0",
                    // Cleanup for a is not run

                    // Effect a is not run
                    "Effect b: 1",
                    "Effect ab: {a: 1, b: 1}",
                    "after state mutation: b",

                    // All cleanups run on unmount
                    "cleaning up for ab: {a: 1, b: 1}",
                    "cleaning up for b: 1",
                    "cleaning up for a: 1",
                ]);
            }
        );

        QUnit.test(
            "useEffect: effect with empty dependency list never reruns",
            async function (assert) {
                assert.expect(6);

                class MyComponent extends Component {
                    setup() {
                        this.state = useState({
                            value: 0,
                        });
                        useEffect(
                            () => {
                                assert.step(`value is ${this.state.value}`);
                                return () => assert.step(`cleaning up for ${this.state.value}`);
                            },
                            () => []
                        );
                    }
                }
                MyComponent.template = xml`<div t-esc="state.value"/>`;

                const env = await makeTestEnv();
                const target = getFixture();
                const component = await mount(MyComponent, { env, target });

                assert.step("before state mutation");
                component.state.value++;
                // Wait for an owl render
                await new Promise((resolve) => requestAnimationFrame(resolve));
                assert.equal(
                    component.el.textContent,
                    1,
                    "Value was correctly changed inside the component"
                );
                assert.step("after state mutation");
                await component.unmount();

                assert.verifySteps([
                    "value is 0",
                    "before state mutation",
                    // no cleanup or effect caused by mutation
                    "after state mutation",
                    // Value being clean
                    "cleaning up for 1",
                ]);
            }
        );

        QUnit.module("useListener");

        QUnit.test("useListener: simple usecase", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    useListener("click", () => assert.step("click"));
                }
            }
            MyComponent.template = xml`<button>Click Me</button>`;

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, { env, target });
            registerCleanup(() => {
                comp.destroy();
            });

            await click(comp.el);
            assert.verifySteps(["click"]);
        });

        QUnit.test("useListener: event delegation", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    this.flag = true;
                    useListener("click", "button", () => assert.step("click"));
                }
            }
            MyComponent.template = xml`
                <div>
                    <button t-if="flag">Click Here</button>
                    <button t-else="">
                        <span>or Here</span>
                    </button>
                </div>`;

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, { env, target });
            registerCleanup(() => {
                comp.destroy();
            });

            await click(comp.el);
            assert.verifySteps([]);
            await click(comp.el.querySelector("button"));
            assert.verifySteps(["click"]);

            comp.flag = false;
            await comp.render();
            await click(comp.el.querySelector("button span"));
            assert.verifySteps(["click"]);
        });

        QUnit.test("useListener: event delegation with capture option", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    this.flag = false;
                    useListener("click", "button", () => assert.step("click"), { capture: true });
                }
            }
            MyComponent.template = xml`
                <div>
                    <button t-if="flag">Click Here</button>
                    <button t-else="">
                        <span>or Here</span>
                    </button>
                </div>`;

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, { env, target });
            registerCleanup(() => {
                comp.destroy();
            });

            await click(comp.el);
            assert.verifySteps([]);
            await click(comp.el.querySelector("button"));
            assert.verifySteps(["click"]);

            comp.flag = false;
            await comp.render();
            await click(comp.el.querySelector("button span"));
            assert.verifySteps(["click"]);
        });

        QUnit.module("useService");

        QUnit.test("useService: unavailable service", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    useService("toy_service");
                }
            }
            MyComponent.template = xml`<div/>`;

            const env = await makeTestEnv();
            const target = getFixture();
            try {
                await mount(MyComponent, { env, target });
            } catch (e) {
                assert.strictEqual(e.message, "Service toy_service is not available");
            }
        });

        QUnit.test("useService: service that returns null", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    this.toyService = useService("toy_service");
                }
            }
            MyComponent.template = xml`<div/>`;

            serviceRegistry.add("toy_service", {
                name: "toy_service",
                start: () => {
                    return null;
                },
            });

            const env = await makeTestEnv();
            const target = getFixture();

            const comp = await mount(MyComponent, { env, target });
            assert.strictEqual(comp.toyService, null);
            comp.unmount();
        });

        QUnit.module("onDestroyed");

        QUnit.test("onDestroyed is called", async (assert) => {
            assert.expect(3);
            class MyComponent extends Component {
                setup() {
                    onDestroyed(() => assert.step("onDestroyed"));
                }
            }
            MyComponent.template = xml`<div/>`;

            const target = getFixture();
            const component = await mount(MyComponent, { target });
            assert.verifySteps([]);
            component.destroy();
            assert.verifySteps(["onDestroyed"]);
        });
    });
});
