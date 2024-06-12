/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { uiService } from "@web/core/ui/ui_service";
import {
    useAutofocus,
    useBus,
    useChildRef,
    useForwardRefToParent,
    useService,
    useSpellCheck,
} from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    destroy,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";

import { Component, onMounted, useState, xml } from "@odoo/owl";
import { dialogService } from "@web/core/dialog/dialog_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { CommandPalette } from "@web/core/commands/command_palette";
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

        QUnit.test(
            "useAutofocus returns also a ref when screen has touch",
            async function (assert) {
                assert.expect(1);
                class MyComponent extends Component {
                    setup() {
                        this.inputRef = useAutofocus();
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

                registry.category("services").add("ui", uiService);

                // patch matchMedia to alter hasTouch value
                patchWithCleanup(browser, {
                    matchMedia: (media) => {
                        if (media === "(pointer:coarse)") {
                            return { matches: true };
                        }
                        this._super();
                    },
                });

                const env = await makeTestEnv();
                const target = getFixture();
                await mount(MyComponent, target, { env });
            }
        );

        QUnit.test(
            "useAutofocus works when screen has touch and you provide mobile param",
            async function (assert) {
                class MyComponent extends Component {
                    setup() {
                        this.inputRef = useAutofocus({ mobile: true });
                    }
                }
                MyComponent.template = xml`
                <span>
                    <input type="text" t-ref="autofocus" />
                </span>
            `;

                registry.category("services").add("ui", uiService);

                // patch matchMedia to alter hasTouch value
                patchWithCleanup(browser, {
                    matchMedia: (media) => {
                        if (media === "(pointer:coarse)") {
                            return { matches: true };
                        }
                        this._super();
                    },
                });

                const env = await makeTestEnv();
                const target = getFixture();
                const comp = await mount(MyComponent, target, { env });
                assert.strictEqual(document.activeElement, comp.inputRef.el);
            }
        );

        QUnit.test("useAutofocus does not focus when screen has touch", async function (assert) {
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

            // patch matchMedia to alter hasTouch value
            patchWithCleanup(browser, {
                matchMedia: (media) => {
                    if (media === "(pointer:coarse)") {
                        return { matches: true };
                    }
                    this._super();
                },
            });

            const env = await makeTestEnv();
            const target = getFixture();
            const comp = await mount(MyComponent, target, { env });
            assert.notEqual(document.activeElement, comp.inputRef.el);
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

        QUnit.test(
            "useAutofocus: autofocus outside of active element doesn't work (CommandPalette)",
            async function (assert) {
                class MyComponent extends Component {
                    setup() {
                        this.inputRef = useAutofocus();
                    }
                    get OverlayContainer() {
                        return registry.category("main_components").get("OverlayContainer");
                    }
                }
                MyComponent.template = xml`
                <div>
                    <input type="text" t-ref="autofocus" />
                    <div class="o_dialog_container"/>
                    <t t-component="OverlayContainer.Component" t-props="OverlayContainer.props" />
                </div>
            `;

                registry.category("services").add("ui", uiService);
                registry.category("services").add("dialog", dialogService);
                registry.category("services").add("hotkey", hotkeyService);

                const config = { providers: [] };
                const env = await makeTestEnv();
                const target = getFixture();
                const comp = await mount(MyComponent, target, { env });
                await nextTick();

                assert.strictEqual(document.activeElement, comp.inputRef.el);

                env.services.dialog.add(CommandPalette, { config });
                await nextTick();
                assert.containsOnce(target, ".o_command_palette");
                assert.notStrictEqual(document.activeElement, comp.inputRef.el);

                comp.render();
                await nextTick();
                assert.notStrictEqual(document.activeElement, comp.inputRef.el);
            }
        );

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

        QUnit.module("useSpellCheck");

        QUnit.test("useSpellCheck: ref is on the textarea", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    useSpellCheck();
                }
            }
            MyComponent.template = xml`<div><textarea t-ref="spellcheck" class="textArea"/></div>`;

            const env = await makeTestEnv();
            const target = getFixture();
            await mount(MyComponent, target, { env });
            const textArea = target.querySelector(".textArea");
            assert.strictEqual(textArea.spellcheck, true, "by default, spellcheck is enabled");
            textArea.focus();
            textArea.blur();
            assert.strictEqual(
                textArea.spellcheck,
                false,
                "spellcheck is disabled once the element has lost its focus"
            );
            textArea.focus();
            assert.strictEqual(
                textArea.spellcheck,
                true,
                "spellcheck is re-enabled once the element is focused"
            );
        });

        QUnit.test("useSpellCheck: use a different refName", async function (assert) {
            class MyComponent extends Component {
                setup() {
                    useSpellCheck({ refName: "myreference" });
                }
            }
            MyComponent.template = xml`<div><textarea t-ref="myreference" class="textArea"/></div>`;

            const env = await makeTestEnv();
            const target = getFixture();
            await mount(MyComponent, target, { env });
            const textArea = target.querySelector(".textArea");
            assert.strictEqual(textArea.spellcheck, true, "by default, spellcheck is enabled");
            textArea.focus();
            textArea.blur();
            assert.strictEqual(
                textArea.spellcheck,
                false,
                "spellcheck is disabled once the element has lost its focus"
            );
            textArea.focus();
            assert.strictEqual(
                textArea.spellcheck,
                true,
                "spellcheck is re-enabled once the element is focused"
            );
        });

        QUnit.test(
            "useSpellCheck: ref is on the root element and two editable elements",
            async function (assert) {
                class MyComponent extends Component {
                    setup() {
                        useSpellCheck();
                    }
                }
                MyComponent.template = xml`
                <div t-ref="spellcheck">
                    <textarea class="textArea"/>
                    <div contenteditable="true" class="editableDiv"/>
                </div>`;

                const env = await makeTestEnv();
                const target = getFixture();
                await mount(MyComponent, target, { env });
                const textArea = target.querySelector(".textArea");
                const editableDiv = target.querySelector(".editableDiv");
                assert.strictEqual(
                    textArea.spellcheck,
                    true,
                    "by default, spellcheck is enabled on the textarea"
                );
                assert.strictEqual(
                    editableDiv.spellcheck,
                    true,
                    "by default, spellcheck is enabled on the editable div"
                );
                textArea.focus();
                textArea.blur();
                editableDiv.focus();
                assert.strictEqual(
                    textArea.spellcheck,
                    false,
                    "spellcheck is disabled once the element has lost its focus"
                );
                editableDiv.blur();
                assert.strictEqual(
                    editableDiv.spellcheck,
                    false,
                    "spellcheck is disabled once the element has lost its focus"
                );
                textArea.focus();
                assert.strictEqual(
                    textArea.spellcheck,
                    true,
                    "spellcheck is re-enabled once the element is focused"
                );
                assert.strictEqual(
                    editableDiv.spellcheck,
                    false,
                    "spellcheck is still disabled as it is not focused"
                );
                editableDiv.focus();
                assert.strictEqual(
                    editableDiv.spellcheck,
                    true,
                    "spellcheck is re-enabled once the element is focused"
                );
            }
        );

        QUnit.test(
            "useSpellCheck: ref is on the root element and one element has disabled the spellcheck",
            async function (assert) {
                class MyComponent extends Component {
                    setup() {
                        useSpellCheck();
                    }
                }
                MyComponent.template = xml`
                <div t-ref="spellcheck">
                    <textarea class="textArea"/>
                    <div contenteditable="true" spellcheck="false" class="editableDiv"/>
                </div>`;

                const env = await makeTestEnv();
                const target = getFixture();
                await mount(MyComponent, target, { env });
                const textArea = target.querySelector(".textArea");
                const editableDiv = target.querySelector(".editableDiv");
                assert.strictEqual(
                    textArea.spellcheck,
                    true,
                    "by default, spellcheck is enabled on the textarea"
                );
                assert.strictEqual(
                    editableDiv.spellcheck,
                    false,
                    "by default, spellcheck is disabled on the editable div"
                );
                textArea.focus();
                textArea.blur();
                editableDiv.focus();
                assert.strictEqual(
                    textArea.spellcheck,
                    false,
                    "spellcheck is disabled once the element has lost its focus"
                );
                assert.strictEqual(
                    editableDiv.spellcheck,
                    false,
                    "spellcheck has not been enabled since it was disabled on purpose"
                );
                editableDiv.blur();
                assert.strictEqual(
                    editableDiv.spellcheck,
                    false,
                    "spellcheck stays disabled once the element has lost its focus"
                );
                textArea.focus();
                assert.strictEqual(
                    textArea.spellcheck,
                    true,
                    "spellcheck is re-enabled once the element is focused"
                );
            }
        );

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
