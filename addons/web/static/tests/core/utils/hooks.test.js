// @ts-check

import { describe, expect, getFixture, test } from "@odoo/hoot";
import { click, queryOne, queryValue } from "@odoo/hoot-dom";
import { animationFrame, Deferred, mockTouch } from "@odoo/hoot-mock";
import { Component, onMounted, reactive, useRef, useState, xml } from "@odoo/owl";
import {
    contains,
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import {
    useAutofocus,
    useBus,
    useChildRef,
    useForwardRefToParent,
    useService,
    useServiceProtectMethodHandling,
    useSpellCheck,
    useSyncedInputProperty,
} from "@web/core/utils/hooks";
import { CommandPalette } from "@web/ui/commands/command_palette";

describe("useAutofocus", () => {
    test.tags("desktop");
    test("simple usecase", async () => {
        const state = reactive({ text: "" });

        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="text" t-ref="autofocus" t-att-value="this.state.text" />
                </span>
            `;
            setup() {
                useAutofocus();

                this.state = useState(state);
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
        const state = reactive({ counter: 0 });

        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="number" t-ref="autofocus" t-att-value="this.state.counter" />
                </span>
            `;
            setup() {
                useAutofocus();

                this.state = useState(state);
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
        const state = reactive({ showInput: true });

        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input t-if="this.state.showInput" type="text" t-ref="autofocus" />
                </span>
            `;
            setup() {
                useAutofocus();

                this.state = useState(state);
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
                    <input type="text" t-ref="autofocus" />
                </span>
            `;
            static props = ["*"];
            setup() {
                const inputRef = useAutofocus();
                onMounted(() => {
                    expect(inputRef.el).toBeInstanceOf(HTMLInputElement);
                });
            }
        }

        await mountWithCleanup(MyComponent);
        expect("input").not.toBeFocused();
    });

    test("works when screen has touch and you provide mobile param", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="text" t-ref="autofocus" />
                </span>
            `;
            setup() {
                useAutofocus({ mobile: true });
            }
        }

        patchWithCleanup(browser, {
            matchMedia(media) {
                if (media === "(pointer:coarse)") {
                    return { matches: true };
                }
                return super.matchMedia(media);
            },
        });

        await mountWithCleanup(MyComponent);

        expect("input").toBeFocused();
    });

    test.tags("desktop");
    test("supports different ref names", async () => {
        const state = reactive({ showSecond: true });

        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="text" t-ref="first" />
                    <input t-if="this.state.showSecond" type="text" t-ref="second" />
                </span>
            `;
            setup() {
                useAutofocus({ refName: "second" });
                useAutofocus({ refName: "first" });

                this.state = useState(state);
            }
        }

        await mountWithCleanup(MyComponent);

        expect("input:first").toBeFocused();

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
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="text" value="input content" t-ref="autofocus" />
                </span>
            `;
            setup() {
                useAutofocus({ selectAll: true });
            }
        }

        await mountWithCleanup(MyComponent);

        expect("input").toBeFocused();
        expect("input").toHaveProperty("selectionStart", 0);
        expect("input").toHaveProperty("selectionEnd", 13);
    });

    test.tags("desktop");
    test("autofocus outside of active element doesn't work (CommandPalette)", async () => {
        const state = reactive({
            showPalette: true,
            text: "",
        });

        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                    <div>
                        <input type="text" t-ref="autofocus" t-att-value="this.state.text" />
                    </div>
                `;
            setup() {
                useAutofocus();

                this.state = useState(state);
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
        const state = reactive({ child: true });

        class MyComponent extends Component {
            static props = ["*"];
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
            static props = ["*"];
            static template = xml`<MyComponent t-if="this.state.child" />`;

            setup() {
                this.state = useState(state);
            }
        }

        const { bus } = await makeMockEnv();
        await mountWithCleanup(Parent);

        bus.trigger("test-event");
        expect.verifySteps(["callback"]);

        state.child = false;
        await animationFrame();

        bus.trigger("test-event");
        expect.verifySteps([]);
    });
});

describe("useService", () => {
    test("unavailable service", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`<div/>`;
            setup() {
                useService(/** @type {any} */ ("toy_service"));
            }
        }

        await expect(mountWithCleanup(MyComponent)).rejects.toThrow(
            "Service toy_service is not available",
        );
    });

    test("service that returns null", async () => {
        let toyService;
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`<div/>`;
            setup() {
                toyService = useService(/** @type {any} */ ("toy_service"));
            }
        }

        registry.category("services").add("toy_service", {
            start: () => null,
        });

        await mountWithCleanup(MyComponent);

        expect(toyService).toBe(null);
    });

    test("an async: method of a class-shaped service writes to the service, not the view", async () => {
        class Counter {
            constructor() {
                this.nextId = 1;
            }
            async mint() {
                return this.nextId++;
            }
        }
        registry.category("services").add("toy_counter", {
            async: ["mint"],
            start: () => new Counter(),
        });

        const minted = [];
        class Child extends Component {
            static props = ["*"];
            static template = xml`<div/>`;
            setup() {
                const counter = useService(/** @type {any} */ ("toy_counter"));
                onMounted(async () => {
                    minted.push(await counter.mint());
                });
            }
        }
        class Parent extends Component {
            static props = ["*"];
            static components = { Child };
            static template = xml`<Child/><Child/>`;
        }
        await mountWithCleanup(Parent);
        await animationFrame();

        expect(minted).toEqual([1, 2]);
        expect(getService(/** @type {any} */ ("toy_counter")).nextId).toBe(3);
    });

    test("async service with protected methods", async () => {
        useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.original;
        const state = reactive({ child: true });
        let nbCalls = 0;
        let def = new Deferred();
        /** @type {any} */
        let objectService;
        /** @type {any} */
        let functionService;

        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`<div/>`;

            setup() {
                objectService = useService(/** @type {any} */ ("object_service"));
                functionService = useService(/** @type {any} */ ("function_service"));
            }
        }

        class Parent extends Component {
            static components = { MyComponent };
            static props = ["*"];
            static template = xml`<MyComponent t-if="this.state.child" />`;

            setup() {
                this.state = useState(state);
            }
        }

        registry.category("services").add("object_service", {
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

        registry.category("services").add("function_service", {
            async: true,
            start() {
                return async function asyncFunc() {
                    nbCalls++;
                    await def;
                    return this;
                };
            },
        });

        await mountWithCleanup(Parent);

        def.resolve();
        await expect(objectService.asyncMethod()).resolves.toBe(objectService);
        await expect(objectService.asyncMethod.call("boundThis")).resolves.toBe(
            "boundThis",
        );
        await expect(functionService()).resolves.toBe(undefined);
        await expect(functionService.call("boundThis")).resolves.toBe("boundThis");
        expect(nbCalls).toBe(4);

        def = new Deferred();
        objectService.asyncMethod().then(() => expect.step("resolved"));
        objectService.asyncMethod.call("boundThis").then(() => expect.step("resolved"));
        functionService().then(() => expect.step("resolved"));
        functionService.call("boundThis").then(() => expect.step("resolved"));
        expect(nbCalls).toBe(8);

        state.child = false;
        await animationFrame();
        def.resolve();
        expect.verifySteps([]);

        await expect(objectService.asyncMethod()).rejects.toThrow(
            "Component is destroyed",
        );
        await expect(objectService.asyncMethod.call("boundThis")).rejects.toThrow(
            "Component is destroyed",
        );
        await expect(functionService()).rejects.toThrow("Component is destroyed");
        await expect(functionService.call("boundThis")).rejects.toThrow(
            "Component is destroyed",
        );
        expect(nbCalls).toBe(8);
        useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.mocked;
    });

    test("a rejection after destroy is withheld, like a resolution", async () => {
        useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.original;
        const state = reactive({ child: true });
        const def = new Deferred();
        /** @type {import("services").ServiceFactories["failing_service"]} */
        let failing;

        class Child extends Component {
            static props = ["*"];
            static template = xml`<div/>`;
            setup() {
                failing = useService("failing_service");
            }
        }
        class Parent extends Component {
            static components = { Child };
            static props = ["*"];
            static template = xml`<Child t-if="this.state.child"/>`;
            setup() {
                this.state = useState(state);
            }
        }

        registry.category("services").add("failing_service", {
            async: ["boom"],
            start: () => ({
                async boom() {
                    await def;
                    throw new Error("network down");
                },
            }),
        });

        await mountWithCleanup(Parent);

        failing.boom().then(
            () => expect.step("resolved"),
            (error) => expect.step(`rejected:${error.message}`),
        );
        failing.boom();

        state.child = false;
        await animationFrame();
        def.resolve();
        await animationFrame();
        await animationFrame();

        expect.verifySteps([]);
        useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.mocked;
    });

    test("a rejection while the owner is alive still propagates", async () => {
        useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.original;
        const def = new Deferred();
        /** @type {import("services").ServiceFactories["failing_service"]} */
        let failing;

        class Child extends Component {
            static props = ["*"];
            static template = xml`<div/>`;
            setup() {
                failing = useService("live_failing_service");
            }
        }

        registry.category("services").add("live_failing_service", {
            async: ["boom"],
            start: () => ({
                async boom() {
                    await def;
                    throw new Error("still mounted");
                },
            }),
        });

        await mountWithCleanup(Child);
        failing.boom().catch((error) => expect.step(`rejected:${error.message}`));
        def.resolve();
        await animationFrame();
        await animationFrame();
        expect.verifySteps(["rejected:still mounted"]);
        useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.mocked;
    });

    test("a getter modifier's async methods stay destroy-guarded", async () => {
        useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.original;
        const state = reactive({ child: true });
        let def = new Deferred();
        /** @type {import("services").ServiceFactories["modifier_service"]} */
        let svc;

        class Child extends Component {
            static props = ["*"];
            static template = xml`<div/>`;
            setup() {
                svc = useService("modifier_service");
            }
        }
        class Parent extends Component {
            static components = { Child };
            static props = ["*"];
            static template = xml`<Child t-if="this.state.child"/>`;
            setup() {
                this.state = useState(state);
            }
        }

        registry.category("services").add("modifier_service", {
            async: ["asyncMethod"],
            start: () => ({
                _silent: false,
                get silent() {
                    return Object.assign(Object.create(this), { _silent: true });
                },
                async asyncMethod() {
                    await def;
                    return this._silent;
                },
            }),
        });

        await mountWithCleanup(Parent);

        def.resolve();
        await expect(svc.asyncMethod()).resolves.toBe(false);
        await expect(svc.silent.asyncMethod()).resolves.toBe(true);

        def = new Deferred();
        svc.asyncMethod().then(() => expect.step("resolved"));
        svc.silent.asyncMethod().then(() => expect.step("resolved"));
        state.child = false;
        await animationFrame();
        def.resolve();
        await animationFrame();
        expect.verifySteps([]);

        await expect(svc.silent.asyncMethod()).rejects.toThrow(
            "Component is destroyed",
        );
        useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.mocked;
    });
});

describe("useSpellCheck", () => {
    test("ref is on the textarea", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`<div><textarea t-ref="spellcheck" class="textArea"/></div>`;
            setup() {
                useSpellCheck();
            }
        }

        await mountWithCleanup(MyComponent);

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").not.toHaveAttribute("spellcheck");

        await click(".textArea");
        expect(".textArea").toBeFocused();

        await click(getFixture());

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");

        await click(".textArea");

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").toHaveAttribute("spellcheck", "true");
    });

    test("use a different refName", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`<div><textarea t-ref="myreference" class="textArea"/></div>`;
            setup() {
                useSpellCheck({ refName: "myreference" });
            }
        }

        await mountWithCleanup(MyComponent);

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").not.toHaveAttribute("spellcheck");

        await click(".textArea");

        expect(".textArea").toBeFocused();

        await click(getFixture());

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
    });

    test("ref is on the root element and two editable elements", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <div t-ref="spellcheck">
                    <textarea class="textArea"/>
                    <div contenteditable="true" class="editableDiv"/>
                </div>`;
            setup() {
                useSpellCheck();
            }
        }

        await mountWithCleanup(MyComponent);

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".editableDiv").toHaveProperty("spellcheck", true);
        expect(".textArea").not.toHaveAttribute("spellcheck");
        expect(".editableDiv").not.toHaveAttribute("spellcheck");

        await click(".textArea");
        expect(".textArea").toBeFocused();

        await click(".editableDiv");
        expect(".editableDiv").toBeFocused();

        await click(getFixture());

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        await click(".textArea");

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").toHaveAttribute("spellcheck", "true");
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        await click(".editableDiv");

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
        expect(".editableDiv").toHaveProperty("spellcheck", true);
        expect(".editableDiv").toHaveAttribute("spellcheck", "true");
    });

    test("ref is on the root element and one element has disabled the spellcheck", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <div t-ref="spellcheck">
                    <textarea class="textArea"/>
                    <div contenteditable="true" spellcheck="false" class="editableDiv"/>
                </div>`;
            setup() {
                useSpellCheck();
            }
        }

        await mountWithCleanup(MyComponent);

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".textArea").not.toHaveAttribute("spellcheck");
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        await click(".textArea");
        expect(".textArea").toBeFocused();

        await click(".editableDiv");
        expect(".editableDiv").toBeFocused();

        await click(getFixture());

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        await click(".textArea");

        expect(".textArea").toHaveProperty("spellcheck", true);
        expect(".textArea").toHaveAttribute("spellcheck", "true");
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");

        await click(".editableDiv");

        expect(".textArea").toHaveProperty("spellcheck", false);
        expect(".textArea").toHaveAttribute("spellcheck", "false");
        expect(".editableDiv").toHaveProperty("spellcheck", false);
        expect(".editableDiv").toHaveAttribute("spellcheck", "false");
    });

    test("ref is on an element with contenteditable attribute", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <div t-ref="spellcheck"  contenteditable="true" class="editableDiv" />`;
            setup() {
                useSpellCheck();
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
        /** @type {import("@odoo/owl").Ref} */
        let childRef;
        /** @type {import("@web/core/utils/hooks").ForwardRef} */
        let parentRef;

        class Child extends Component {
            static props = ["*"];
            static template = xml`<span t-ref="someRef" class="my_span">Hello</span>`;
            setup() {
                childRef = useForwardRefToParent("someRef");
            }
        }

        class Parent extends Component {
            static props = ["*"];
            static template = xml`<div><Child someRef="this.someRef"/></div>`;
            static components = { Child };
            setup() {
                this.someRef = useChildRef();
                parentRef = this.someRef;
            }
        }

        await mountWithCleanup(Parent);
        expect(childRef.el).toBe(queryOne(".my_span"));
        expect(parentRef.el).toBe(queryOne(".my_span"));
    });

    test("in a conditional child", async () => {
        class Child extends Component {
            static props = ["*"];
            static template = xml`<span t-ref="someRef" class="my_span">Hello</span>`;
            setup() {
                useForwardRefToParent("someRef");
            }
        }

        class Parent extends Component {
            static props = ["*"];
            static template = xml`<div><Child t-if="this.state.hasChild" someRef="this.someRef"/></div>`;
            static components = { Child };
            setup() {
                this.someRef = useChildRef();
                this.state = useState({ hasChild: true });
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

describe("useSyncedInputProperty", () => {
    /** @param {any} initial */
    function makeHost(initial) {
        class Host extends Component {
            static props = {};
            static template = xml`<input t-ref="i" t-att-value="this.state.v"/>`;

            /** @type {{ v: any }} */
            state;

            /** @type {() => boolean} */
            sync;

            setup() {
                const state = useState({ v: initial });
                const ref = /** @type {import("@odoo/owl").Ref<HTMLInputElement>} */ (
                    useRef("i")
                );
                this.state = state;
                this.sync = useSyncedInputProperty(
                    () => ref.el,
                    () => state.v,
                );
            }
        }
        return Host;
    }

    test("a value the user typed over is written back on the next patch", async () => {
        const host = await mountWithCleanup(makeHost("a"));
        const input = /** @type {HTMLInputElement} */ (queryOne("input"));
        input.value = "typed over";

        host.state.v = "a";
        host.render();
        await animationFrame();

        expect(queryValue("input")).toBe("a");
    });

    test("undefined means the component is not the authority", async () => {
        class Host extends Component {
            static props = {};
            static template = xml`<input t-ref="i"/>`;

            /** @type {{ v: any }} */
            state;

            /** @type {() => boolean} */
            sync;

            setup() {
                const state = useState({ v: undefined });
                const ref = /** @type {import("@odoo/owl").Ref<HTMLInputElement>} */ (
                    useRef("i")
                );
                this.state = state;
                this.sync = useSyncedInputProperty(
                    () => ref.el,
                    () => state.v,
                );
            }
        }
        const host = await mountWithCleanup(Host);
        const input = /** @type {HTMLInputElement} */ (queryOne("input"));
        input.value = "user owns this";

        expect(host.sync()).toBe(false);
        host.render();
        await animationFrame();

        expect(queryValue("input")).toBe("user owns this");
    });

    test("the returned sync reports whether it had to write", async () => {
        const host = await mountWithCleanup(makeHost("a"));

        expect(host.sync()).toBe(false);
        const input = /** @type {HTMLInputElement} */ (queryOne("input"));
        input.value = "drifted";
        expect(host.sync()).toBe(true);
        expect(queryValue("input")).toBe("a");
        expect(host.sync()).toBe(false);
    });

    test("a boolean property is synced too", async () => {
        class Host extends Component {
            static props = {};
            static template = xml`<input type="checkbox" t-ref="i" t-att-checked="this.state.v"/>`;

            /** @type {{ v: any }} */
            state;

            /** @type {() => boolean} */
            sync;

            setup() {
                const state = useState({ v: true });
                const ref = /** @type {import("@odoo/owl").Ref<HTMLInputElement>} */ (
                    useRef("i")
                );
                this.state = state;
                this.sync = useSyncedInputProperty(
                    () => ref.el,
                    () => state.v,
                    { property: "checked" },
                );
            }
        }
        const host = await mountWithCleanup(Host);
        const input = /** @type {HTMLInputElement} */ (queryOne("input"));
        input.checked = false;

        expect(host.sync()).toBe(true);
        expect(input.checked).toBe(true);
    });
});
