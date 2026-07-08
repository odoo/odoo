import {
    animationFrame,
    click,
    describe,
    expect,
    getFixture,
    mockTouch,
    mockUserAgent,
    queryOne,
    test,
} from "@odoo/hoot";
import {
    Component,
    onMounted,
    Plugin,
    props,
    providePlugins,
    proxy,
    signal,
    t,
    useConfig,
    usePlugin,
    xml,
} from "@odoo/owl";
import {
    contains,
    destroyApp,
    getMockEnv,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { CommandPalette } from "@web/core/commands/command_palette";
import { registry } from "@web/core/registry";
import {
    useAutofocus,
    useBackButton,
    useBus,
    useChildRef,
    useForwardRefToParent,
    useOwnedDialogs,
    useService,
    useSpellCheck,
} from "@web/core/utils/hooks";

describe("useAutofocus", () => {
    test.tags("desktop");
    test("simple usecase", async () => {
        const state = proxy({ text: "" });

        class MyComponent extends Component {
            static template = xml`
                <span>
                    <input type="text" t-ref="this.autofocusRef" t-att-value="this.state.text" />
                </span>
            `;
            autofocusRef = signal(null);
            setup() {
                useAutofocus({ ref: this.autofocusRef });

                this.state = proxy(state);
            }
        }

        await mountWithCleanup(MyComponent);

        expect("input").toBeFocused();

        state.text = "a";
        await animationFrame();

        expect("input").toBeFocused();
    });

    test.tags("desktop");
    test("simple usecase when input type is number", async () => {
        const state = proxy({ counter: 0 });

        class MyComponent extends Component {
            static template = xml`
                <span>
                    <input type="number" t-ref="this.autofocusRef" t-att-value="this.state.counter" />
                </span>
            `;
            autofocusRef = signal(null);
            setup() {
                useAutofocus({ ref: this.autofocusRef });

                this.state = proxy(state);
            }
        }

        await mountWithCleanup(MyComponent);

        expect("input").toBeFocused();

        state.counter++;
        await animationFrame();

        expect("input").toBeFocused();
    });

    test.tags("desktop");
    test("conditional autofocus", async () => {
        const state = proxy({ showInput: true });

        class MyComponent extends Component {
            static template = xml`
                <span>
                    <input t-if="this.state.showInput" type="text" t-ref="this.autofocusRef" />
                </span>
            `;
            autofocusRef = signal(null);
            setup() {
                useAutofocus({ ref: this.autofocusRef });

                this.state = proxy(state);
            }
        }

        await mountWithCleanup(MyComponent);

        expect("input").toBeFocused();

        state.showInput = false;
        await animationFrame();

        expect(document.body).toBeFocused();

        state.showInput = true;
        await animationFrame();

        expect("input").toBeFocused();
    });

    test("returns also a ref when screen has touch but it does not focus", async () => {
        expect.assertions(2);

        mockTouch(true);

        class MyComponent extends Component {
            static template = xml`
                <span>
                    <input type="text" t-ref="this.autofocusRef" />
                </span>
            `;
            autofocusRef = signal(null);
            setup() {
                const inputRef = useAutofocus({ ref: this.autofocusRef });
                onMounted(() => {
                    expect(inputRef()).toBeInstanceOf(HTMLInputElement);
                });
            }
        }

        await mountWithCleanup(MyComponent);
        expect("input").not.toBeFocused();
    });

    test("works when screen has touch and you provide mobile param", async () => {
        class MyComponent extends Component {
            static template = xml`
                <span>
                    <input type="text" t-ref="this.autofocusRef" />
                </span>
            `;
            autofocusRef = signal(null);
            setup() {
                useAutofocus({ ref: this.autofocusRef, mobile: true });
            }
        }

        patchWithCleanup(browser, {
            matchMedia: (media) => {
                if (media === "(pointer:coarse)") {
                    return { matches: true };
                }
                this._super();
            },
        });

        await mountWithCleanup(MyComponent);

        expect("input").toBeFocused();
    });

    test.tags("desktop");
    test("supports different ref names", async () => {
        const state = proxy({ showSecond: true });

        class MyComponent extends Component {
            static template = xml`
                <span>
                    <input type="text" t-ref="this.firstRef" />
                    <input t-if="this.state.showSecond" type="text" t-ref="this.secondRef" />
                </span>
            `;
            firstRef = signal(null);
            secondRef = signal(null);
            setup() {
                useAutofocus({ ref: this.secondRef });
                useAutofocus({ ref: this.firstRef }); // test requires this at second position

                this.state = proxy(state);
            }
        }

        await mountWithCleanup(MyComponent);

        // "first" is focused first since it has the last call to "useAutofocus"
        expect("input:first").toBeFocused();

        // We now remove and add again the second input, which triggers the useEffect of the hook and and apply focus
        state.showSecond = false;
        await animationFrame();

        expect("input:first").toBeFocused();

        state.showSecond = true;
        await animationFrame();

        expect("input:last").toBeFocused();
    });

    test.tags("desktop");
    test("can select its content", async () => {
        class MyComponent extends Component {
            static template = xml`
                <span>
                    <input type="text" value="input content" t-ref="this.autofocusRef" />
                </span>
            `;
            autofocusRef = signal(null);
            setup() {
                useAutofocus({ ref: this.autofocusRef, selectAll: true });
            }
        }

        await mountWithCleanup(MyComponent);

        expect("input").toBeFocused();
        expect("input").toHaveProperty("selectionStart", 0);
        expect("input").toHaveProperty("selectionEnd", 13);
    });

    test.tags("desktop");
    test("autofocus outside of active element doesn't work (CommandPalette)", async () => {
        const state = proxy({
            showPalette: true,
            text: "",
        });

        class MyComponent extends Component {
            static template = xml`
                    <div>
                        <input type="text" t-ref="this.autofocusRef" t-att-value="this.state.text" />
                    </div>
                `;
            autofocusRef = signal(null);
            setup() {
                useAutofocus({ ref: this.autofocusRef });

                this.state = proxy(state);
            }
        }

        await mountWithCleanup(MyComponent);

        expect("input:first").toBeFocused();

        getService("dialog").add(CommandPalette, {
            config: { providers: [] },
        });
        await animationFrame();

        expect(".o_command_palette").toHaveCount(1);
        expect("input:first").not.toBeFocused();

        state.text = "a";
        await animationFrame();

        expect("input:first").not.toBeFocused();
    });
});

describe("useBus", () => {
    test("simple usecase", async () => {
        const state = proxy({ child: true });

        class MyComponent extends Component {
            static template = xml`<div/>`;
            setup() {
                useBus(this.env.bus, "test-event", this.myCallback);
            }
            myCallback() {
                expect.step("callback");
            }
        }

        class Parent extends Component {
            static components = { MyComponent };
            static template = xml`<MyComponent t-if="this.state.child" />`;

            setup() {
                this.state = proxy(state);
            }
        }

        await mountWithCleanup(Parent);

        getMockEnv().bus.trigger("test-event");
        expect.verifySteps(["callback"]);

        state.child = false;
        await animationFrame();

        getMockEnv().bus.trigger("test-event");
        expect.verifySteps([]);
    });
});

describe("useService", () => {
    test("unavailable service", async () => {
        class MyComponent extends Component {
            static template = xml`<div/>`;
            setup() {
                useService("toy_service");
            }
        }

        await expect(mountWithCleanup(MyComponent)).rejects.toThrow(
            "Service toy_service is not available"
        );
    });

    test("service that returns null", async () => {
        let toyService;
        class MyComponent extends Component {
            static template = xml`<div/>`;
            setup() {
                toyService = useService("toy_service");
            }
        }

        registry.category("services").add("toy_service", {
            name: "toy_service",
            start: () => null,
        });

        await mountWithCleanup(MyComponent);

        expect(toyService).toBe(null);
    });

    test("async service with protected methods", async () => {
        const state = proxy({ child: true });
        let nbCalls = 0;
        let def = Promise.withResolvers();
        let objectService;
        let functionService;

        class MyComponent extends Component {
            static template = xml`<div/>`;

            setup() {
                objectService = useService("object_service");
                functionService = useService("function_service");
            }
        }

        class Parent extends Component {
            static components = { MyComponent };
            static template = xml`<MyComponent t-if="this.state.child" />`;

            setup() {
                this.state = proxy(state);
            }
        }

        registry.category("services").add("object_service", {
            name: "object_service",
            async: ["asyncMethod"],
            start() {
                return {
                    async asyncMethod() {
                        nbCalls++;
                        await def.promise;
                        return this;
                    },
                };
            },
        });

        registry.category("services").add("function_service", {
            name: "function_service",
            async: true,
            start() {
                return async function asyncFunc() {
                    nbCalls++;
                    await def.promise;
                    return this;
                };
            },
        });

        await mountWithCleanup(Parent);

        // Functions and methods have the correct this
        def.resolve();
        await expect(objectService.asyncMethod()).resolves.toBe(objectService);
        await expect(objectService.asyncMethod.call("boundThis")).resolves.toBe("boundThis");
        await expect(functionService()).resolves.toBe(undefined);
        await expect(functionService.call("boundThis")).resolves.toBe("boundThis");
        expect(nbCalls).toBe(4);

        // Functions that were called before the component is destroyed but resolved after never resolve
        def = Promise.withResolvers();
        objectService.asyncMethod().then(() => expect.step("resolved"));
        objectService.asyncMethod.call("boundThis").then(() => expect.step("resolved"));
        functionService().then(() => expect.step("resolved"));
        functionService.call("boundThis").then(() => expect.step("resolved"));
        expect(nbCalls).toBe(8);

        state.child = false;
        await animationFrame();
        def.resolve();
        expect.verifySteps([]);

        // Calling the functions after the destruction rejects the promise
        await expect(objectService.asyncMethod()).rejects.toThrow("Component is destroyed");
        await expect(objectService.asyncMethod.call("boundThis")).rejects.toThrow(
            "Component is destroyed"
        );
        await expect(functionService()).rejects.toThrow("Component is destroyed");
        await expect(functionService.call("boundThis")).rejects.toThrow("Component is destroyed");
        expect(nbCalls).toBe(8);
    });
});

describe("useSpellCheck", () => {
    test("ref is on the textarea", async () => {
        // To understand correctly the test, refer to the MDN documentation of spellcheck.
        class MyComponent extends Component {
            static template = xml`<div><textarea t-ref="this.spellcheckRef" class="textArea"/></div>`;
            spellcheckRef = signal(null);
            setup() {
                useSpellCheck({ ref: this.spellcheckRef });
            }
        }

        await mountWithCleanup(MyComponent);

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").not.toHaveAttribute("spellcheck");

        // Focus textarea
        await click(".textArea");
        expect(".textArea").toBeFocused();

        // Click out to trigger blur
        await click(getFixture());

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");

        // Focus textarea
        await click(".textArea");

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").toHaveAttribute("spellcheck", "true");
    });

    test("use a different refName", async () => {
        class MyComponent extends Component {
            static template = xml`<div><textarea t-ref="this.myReferenceRef" class="textArea"/></div>`;
            myReferenceRef = signal(null);
            setup() {
                useSpellCheck({ ref: this.myReferenceRef });
            }
        }

        await mountWithCleanup(MyComponent);

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").not.toHaveAttribute("spellcheck");

        await click(".textArea");

        expect(".textArea").toBeFocused();

        // Click out to trigger blur
        await click(getFixture());

        // Once these assertions pass, it means that the hook is working.
        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
    });

    test("ref is on the root element and two editable elements", async () => {
        class MyComponent extends Component {
            static template = xml`
                <div t-ref="this.spellcheckRef">
                    <textarea class="textArea"/>
                    <div contenteditable="true" class="editableDiv"/>
                </div>`;
            spellcheckRef = signal(null);
            setup() {
                useSpellCheck({ ref: this.spellcheckRef });
            }
        }

        await mountWithCleanup(MyComponent);

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".editableDiv").toHaveProperty("spellcheck", true);
        expect(".textArea").not.toHaveAttribute("spellcheck");
        expect(".editableDiv").not.toHaveAttribute("spellcheck");

        // Focus textarea
        await click(".textArea");
        expect(".textArea").toBeFocused();

        // Focus editable div
        await click(".editableDiv");
        expect(".editableDiv").toBeFocused();

        // Click out to trigger blur
        await click(getFixture());

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        // Focus textarea
        await click(".textArea");

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").toHaveAttribute("spellcheck", "true");
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        // Focus editable div
        await click(".editableDiv");

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
        expect(".editableDiv").toHaveProperty("spellcheck", true);
        expect(".editableDiv").toHaveAttribute("spellcheck", "true");
    });

    test("ref is on the root element and one element has disabled the spellcheck", async () => {
        class MyComponent extends Component {
            static template = xml`
                <div t-ref="this.spellcheckRef">
                    <textarea class="textArea"/>
                    <div contenteditable="true" spellcheck="false" class="editableDiv"/>
                </div>`;
            spellcheckRef = signal(null);
            setup() {
                useSpellCheck({ ref: this.spellcheckRef });
            }
        }

        await mountWithCleanup(MyComponent);

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".textArea").not.toHaveAttribute("spellcheck");
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        // Focus textarea
        await click(".textArea");
        expect(".textArea").toBeFocused();

        // Focus editable div
        await click(".editableDiv");
        expect(".editableDiv").toBeFocused();

        // Click out to trigger blur
        await click(getFixture());

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        // Focus textarea
        await click(".textArea");

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").toHaveAttribute("spellcheck", "true");
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        // Focus editable div
        await click(".editableDiv");

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");
    });

    test("ref is on an element with contenteditable attribute", async () => {
        class MyComponent extends Component {
            static template = xml`
                <div t-ref="this.spellcheckRef"  contenteditable="true" class="editableDiv" />`;
            spellcheckRef = signal(null);
            setup() {
                useSpellCheck({ ref: this.spellcheckRef });
            }
        }

        await mountWithCleanup(MyComponent);
        expect(".editableDiv").toHaveProperty("spellcheck", true);
        await contains(".editableDiv").click();
        expect(".editableDiv").toBeFocused();
        expect(".editableDiv").toHaveAttribute("spellcheck", "true");
        await click(getFixture());
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");
    });
});

describe("useChildRef and useForwardRefToParent", () => {
    test("simple usecase", async () => {
        let childRef;
        let parentRef;

        class Child extends Component {
            static template = xml`<span t-ref="this.someRef" class="my_span">Hello</span>`;
            someRef = signal(null);
            setup() {
                childRef = useForwardRefToParent(this.someRef, "someRef");
            }
        }

        class Parent extends Component {
            static template = xml`<div><Child someRef="this.someRef"/></div>`;
            static components = { Child };
            setup() {
                this.someRef = useChildRef();
                parentRef = this.someRef;
            }
        }

        await mountWithCleanup(Parent);
        expect(childRef()).toBe(queryOne(".my_span"));
        expect(parentRef.el).toBe(queryOne(".my_span"));
    });

    test("in a conditional child", async () => {
        class Child extends Component {
            static template = xml`<span t-ref="this.someRef" class="my_span">Hello</span>`;
            someRef = signal(null);
            setup() {
                useForwardRefToParent(this.someRef, "someRef");
            }
        }

        class Parent extends Component {
            static template = xml`<div><Child t-if="this.state.hasChild" someRef="this.someRef"/></div>`;
            static components = { Child };
            setup() {
                this.someRef = useChildRef();
                this.state = proxy({ hasChild: true });
            }
        }

        const parentComponent = await mountWithCleanup(Parent);

        expect(".my_span").toHaveCount(1);
        expect(parentComponent.someRef.el).toBe(queryOne(".my_span"));

        parentComponent.state.hasChild = false;
        await animationFrame();

        expect(".my_span").toHaveCount(0);
        expect(parentComponent.someRef.el).toBe(null);

        parentComponent.state.hasChild = true;
        await animationFrame();

        expect(".my_span").toHaveCount(1);
        expect(parentComponent.someRef.el).toBe(queryOne(".my_span"));
    });
});

describe("useBackButton", () => {
    test.tags("mobile");
    test("simple usecase ", async () => {
        mockUserAgent("android");
        class DummyComponent extends Component {
            static template = xml`<div/>`;
            setup() {
                useBackButton(() => expect.step("callback"));
            }
        }

        history.pushState({ sentinel: 1 }, "", "/");
        history.pushState({ sentinel: 2 }, "", "/other");
        await mountWithCleanup(DummyComponent);
        expect(history.state.trapState).toBe(true);
        history.back();
        expect.verifySteps(["callback"]);
        destroyApp();
        await animationFrame();
        expect(history.state.sentinel).toBe(2);
    });

    test.tags("mobile");
    test("`shouldEnable` callback function pushes/clears trap history entry", async () => {
        mockUserAgent("android");

        class DummyComponent extends Component {
            static template = xml`<div t-out="this.backBtnAvailable()" />`;

            backBtnAvailable = signal(false);

            setup() {
                useBackButton(() => null, this.backBtnAvailable);
            }
        }

        history.pushState({ sentinel: 1 }, "", "/");
        history.pushState({ sentinel: 2 }, "", "/other");

        const dummy = await mountWithCleanup(DummyComponent);

        expect(history.state.sentinel).toBe(2);

        dummy.backBtnAvailable.set(true);
        await animationFrame();

        expect(history.state.trapState).toBe(true);

        dummy.backBtnAvailable.set(false);
        await animationFrame();

        expect(history.state.sentinel).toBe(2);
    });

    test.tags("mobile");
    test("multiple components' callbacks should be executed in a LIFO manner", async () => {
        mockUserAgent("android");
        class DummyComponent extends Component {
            static template = xml`<div t-out="this.props.name" />`;

            props = props({ name: t.string() });

            setup() {
                useBackButton(this.onBack.bind(this));
            }

            onBack() {
                expect.step(`${this.props.name} callback`);
                dummies().delete(this.props.name);
            }
        }

        class Parent extends Component {
            static components = { DummyComponent };
            static template = xml`
                <t t-foreach="this.dummies()" t-as="name" t-key="name">
                    <DummyComponent name="name" />
                </t>
            `;

            dummies = dummies;
        }

        history.pushState({ sentinel: 1 }, "", "/");
        history.pushState({ sentinel: 2 }, "", "/other");

        const dummies = signal.Set(new Set());

        await mountWithCleanup(Parent);
        // Need to be added 1 by 1 because Owl mounts siblings from last to first
        dummies().add("dummy1");
        await animationFrame();
        dummies().add("dummy2");
        await animationFrame();
        dummies().add("dummy3");
        await animationFrame();

        expect(history.state.trapState).toBe(true);

        history.back();
        await animationFrame();
        history.back();
        await animationFrame();
        history.back();
        await animationFrame();

        expect.verifySteps(["dummy3 callback", "dummy2 callback", "dummy1 callback"]);
        expect(history.state.sentinel).toBe(2);
    });
});

describe("useOwnedDialogs", () => {
    test("propagate scope to dialog", async () => {
        class MyPlugin extends Plugin {
            text = useConfig("text");
        }

        class Dialog extends Component {
            static template = xml`<div class="dialog" t-out="this.p.text"/>`;
            setup() {
                this.p = usePlugin(MyPlugin);
            }
        }

        class Parent extends Component {
            static template = xml``;

            setup() {
                providePlugins([MyPlugin], { text: "abc" });
                const addDialog = useOwnedDialogs({ withScope: true });
                onMounted(() => {
                    addDialog(Dialog, {});
                });
            }
        }

        await mountWithCleanup(Parent);
        await animationFrame();
        expect(".dialog").toHaveText("abc");
    });
});
