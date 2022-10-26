/** @odoo-module **/

import { uiService } from "@web/core/ui/ui_service";
import { useAutofocus, useBus, useChildRef, useForwardRefToParent, useListener, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    click,
    destroy,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
} from "@web/../tests/helpers/utils";
import { LegacyComponent } from "@web/legacy/legacy_component";

const { Component, onMounted, useState, xml } = owl;
const serviceRegistry = registry.category("services");

QUnit.module("utils", () => {
    QUnit.module("Hooks", () => {
        QUnit.module("useAutofocus");

        QUnit.test("useAutofocus: simple usecase", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    this.inputRef = useAutofocus();
                }
            }
            MyComponent.template = xml`
                <span>
                    <input type="text" t-ref="autofocus" />
                </span>
            `;

            registry.category("services").add("ui", uiService);

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, target, { env });
            await nextTick();

            assert.strictEqual(document.activeElement, comp.inputRef.el);

            comp.render();
            await nextTick();
            assert.strictEqual(document.activeElement, comp.inputRef.el);
        });

        QUnit.test(
            "useAutofocus: simple usecase when input type is number",
            async function (assert) {
                class MyComponent extends Component {
                    setup() {
                        this.inputRef = useAutofocus();
                    }
                }
                MyComponent.template = xml`
                <span>
                    <input type="number" t-ref="autofocus" />
                </span>
            `;

                registry.category("services").add("ui", uiService);

                const env = await makeTestEnv();
                const target = getFixture();
                const comp = await mount(MyComponent, target, { env });

                assert.strictEqual(document.activeElement, comp.inputRef.el);

                comp.render();
                await nextTick();
                assert.strictEqual(document.activeElement, comp.inputRef.el);
            }
        );

        QUnit.test("useAutofocus: conditional autofocus", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    this.inputRef = useAutofocus();
                    this.showInput = true;
                }
            }
            MyComponent.template = xml`
                <span>
                    <input t-if="showInput" type="text" t-ref="autofocus" />
                </span>
            `;

            registry.category("services").add("ui", uiService);

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, target, { env });
            await nextTick();

            assert.strictEqual(document.activeElement, comp.inputRef.el);

            comp.showInput = false;
            comp.render();
            await nextTick();
            assert.notStrictEqual(document.activeElement, comp.inputRef.el);

            comp.showInput = true;
            comp.render();
            await nextTick();
            assert.strictEqual(document.activeElement, comp.inputRef.el);
        });

        QUnit.test("useAutofocus returns also a ref when isSmall is true", async function (assert) {
            assert.expect(2);
            class MyComponent extends Component {
                setup() {
                    this.inputRef = useAutofocus();
                    assert.ok(this.env.isSmall);
                    onMounted(() => {
                        assert.ok(this.inputRef.el);
                    });
                }
            }
            MyComponent.template = xml`
                <span>
                    <input type="text" t-ref="autofocus" />
                </span>
            `;

            const fakeUIService = {
                start(env) {
                    const ui = {};
                    Object.defineProperty(env, "isSmall", {
                        get() {
                            return true;
                        },
                    });

                    return ui;
                },
            };

            registry.category("services").add("ui", fakeUIService);

            const env = await makeTestEnv();
            const target = getFixture();
            await mount(MyComponent, target, { env });
        });

        QUnit.test("supports different ref names", async (assert) => {
            class MyComponent extends Component {
                setup() {
                    this.secondRef = useAutofocus({ refName: "second" });
                    this.firstRef = useAutofocus({ refName: "first" });

                    this.state = useState({ showSecond: true });
                }
            }
            MyComponent.template = xml`
                <span>
                    <input type="text" t-ref="first" />
                    <input t-if="state.showSecond" type="text" t-ref="second" />
                </span>
            `;

            registry.category("services").add("ui", uiService);

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, target, { env });
            await nextTick();

            // "first" is focused first since it has the last call to "useAutofocus"
            assert.strictEqual(document.activeElement, comp.firstRef.el);

            comp.state.showSecond = false;
            await nextTick();
            comp.state.showSecond = true;
            await nextTick();

            assert.strictEqual(document.activeElement, comp.secondRef.el);
        });

        QUnit.test("can select an entire text", async (assert) => {
            class MyComponent extends Component {
                setup() {
                    this.inputRef = useAutofocus({ selectAll: true });
                }
            }
            MyComponent.template = xml`
                <span>
                    <input type="text" value="abcdefghij" t-ref="autofocus" />
                </span>
            `;

            registry.category("services").add("ui", uiService);

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, target, { env });
            await nextTick();

            assert.strictEqual(document.activeElement, comp.inputRef.el);
            assert.strictEqual(comp.inputRef.el.selectionStart, 0);
            assert.strictEqual(comp.inputRef.el.selectionEnd, 10);
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
            const comp = await mount(MyComponent, target, { env });
            env.bus.trigger("test-event");
            await nextTick();
            assert.verifySteps(["callback"]);

            destroy(comp);
            env.bus.trigger("test-event");
            await nextTick();
            assert.verifySteps([]);
        });

        QUnit.module("useListener");

        QUnit.test("useListener: simple usecase", async function (assert) {
            class MyComponent extends LegacyComponent {
                setup() {
                    useListener("click", () => assert.step("click"));
                }
            }
            MyComponent.template = xml`<button class="root">Click Me</button>`;

            const env = await makeTestEnv();
            const target = getFixture();
            await mount(MyComponent, target, { env });

            await click(target.querySelector(".root"));
            assert.verifySteps(["click"]);
        });

        QUnit.test("useListener: event delegation", async function (assert) {
            class MyComponent extends LegacyComponent {
                setup() {
                    this.flag = true;
                    useListener("click", "button", () => assert.step("click"));
                }
            }
            MyComponent.template = xml`
                <div class="root">
                    <button t-if="flag">Click Here</button>
                    <button t-else="">
                        <span>or Here</span>
                    </button>
                </div>`;

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, target, { env });

            await click(target.querySelector(".root"));
            assert.verifySteps([]);
            await click(target.querySelector("button"));
            assert.verifySteps(["click"]);

            comp.flag = false;
            comp.render();
            await nextTick();
            await click(target.querySelector("button span"));
            assert.verifySteps(["click"]);
        });

        QUnit.test("useListener: event delegation with capture option", async function (assert) {
            class MyComponent extends LegacyComponent {
                setup() {
                    this.flag = false;
                    useListener("click", "button", () => assert.step("click"), { capture: true });
                }
            }
            MyComponent.template = xml`
                <div class="root">
                    <button t-if="flag">Click Here</button>
                    <button t-else="">
                        <span>or Here</span>
                    </button>
                </div>`;

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, target, { env });

            await click(target.querySelector(".root"));
            assert.verifySteps([]);
            await click(target.querySelector("button"));
            assert.verifySteps(["click"]);

            comp.flag = false;
            await comp.render();
            await click(target.querySelector("button span"));
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
                await mount(MyComponent, target, { env });
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

            const comp = await mount(MyComponent, target, { env });
            assert.strictEqual(comp.toyService, null);
        });

        QUnit.test("useService: async service with protected methods", async function (assert) {
            let nbCalls = 0;
            let def = makeDeferred();
            class MyComponent extends Component {
                setup() {
                    this.objectService = useService("object_service");
                    this.functionService = useService("function_service");
                }
            }
            MyComponent.template = xml`<div/>`;

            serviceRegistry.add("object_service", {
                name: "object_service",
                async: ["asyncMethod"],
                start() {
                    return {
                        async asyncMethod() {
                            nbCalls++;
                            await def;
                            return this;
                        },
                    };
                },
            });

            serviceRegistry.add("function_service", {
                name: "function_service",
                async: true,
                start() {
                    return async function asyncFunc() {
                        nbCalls++;
                        await def;
                        return this;
                    };
                },
            });

            const env = await makeTestEnv();
            const target = getFixture();

            const comp = await mount(MyComponent, target, { env });
            // Functions and methods have the correct this
            def.resolve();
            assert.deepEqual(await comp.objectService.asyncMethod(), comp.objectService);
            assert.deepEqual(await comp.objectService.asyncMethod.call("boundThis"), "boundThis");
            assert.deepEqual(await comp.functionService(), comp);
            assert.deepEqual(await comp.functionService.call("boundThis"), "boundThis");
            assert.strictEqual(nbCalls, 4);
            // Functions that were called before the component is destroyed but resolved after never resolve
            let nbResolvedProms = 0;
            def = makeDeferred();
            comp.objectService.asyncMethod().then(() => nbResolvedProms++);
            comp.objectService.asyncMethod.call("boundThis").then(() => nbResolvedProms++);
            comp.functionService().then(() => nbResolvedProms++);
            comp.functionService.call("boundThis").then(() => nbResolvedProms++);
            assert.strictEqual(nbCalls, 8);
            comp.__owl__.app.destroy();
            def.resolve();
            await nextTick();
            assert.strictEqual(
                nbResolvedProms,
                0,
                "The promises returned by the calls should never resolve"
            );
            // Calling the functions after the destruction rejects the promise
            assert.rejects(comp.objectService.asyncMethod(), "Component is destroyed");
            assert.rejects(
                comp.objectService.asyncMethod.call("boundThis"),
                "Component is destroyed"
            );
            assert.rejects(comp.functionService(), "Component is destroyed");
            assert.rejects(comp.functionService.call("boundThis"), "Component is destroyed");
            assert.strictEqual(nbCalls, 8);
        });

        QUnit.module("useChildRef / useForwardRefToParent");

        QUnit.test("simple usecase", async function (assert) {
            let childRef;
            let parentRef;
            class Child extends Component {
                setup() {
                    childRef = useForwardRefToParent("someRef");
                }
            }
            Child.template = xml`<span t-ref="someRef" class="my_span">Hello</span>`;
            class Parent extends Component {
                setup() {
                    this.someRef = useChildRef();
                    parentRef = this.someRef;
                }
            }
            Parent.template = xml`<div><Child someRef="someRef"/></div>`;
            Parent.components = { Child };

            const env = await makeTestEnv();
            const target = getFixture();

            await mount(Parent, target, { env });
            assert.strictEqual(childRef.el, target.querySelector(".my_span"));
            assert.strictEqual(parentRef.el, target.querySelector(".my_span"));
        });

        QUnit.test("useForwardRefToParent in a conditional child", async function (assert) {
            class Child extends Component {
                setup() {
                    useForwardRefToParent("someRef");
                }
            }
            Child.template = xml`<span t-ref="someRef" class="my_span">Hello</span>`;
            class Parent extends Component {
                setup() {
                    this.someRef = useChildRef();
                    this.state = useState({ hasChild: true });
                }
            }
            Parent.template = xml`<div><Child t-if="state.hasChild" someRef="someRef"/></div>`;
            Parent.components = { Child };

            const env = await makeTestEnv();
            const target = getFixture();

            const parent = await mount(Parent, target, { env });
            assert.containsOnce(target, ".my_span");
            assert.strictEqual(parent.someRef.el, target.querySelector(".my_span"));

            parent.state.hasChild = false;
            await nextTick();

            assert.containsNone(target, ".my_span");
            assert.strictEqual(parent.someRef.el, null);

            parent.state.hasChild = true;
            await nextTick();
            assert.containsOnce(target, ".my_span");
            assert.strictEqual(parent.someRef.el, target.querySelector(".my_span"));
        });
    });
});
