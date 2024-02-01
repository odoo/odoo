import { expect, describe, test, getFixture } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { queryOne, dispatch } from "@odoo/hoot-dom";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";

import { Component, xml, useState, onMounted } from "@odoo/owl";
import {
    useAutofocus,
    useBus,
    useService,
    useSpellCheck,
    useChildRef,
    useForwardRefToParent,
} from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { CommandPalette } from "@web/core/commands/command_palette";

describe("useAutofocus", () => {
    test.tags("desktop")("simple usecase", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="text" t-ref="autofocus" />
                </span>
            `;
            setup() {
                this.inputRef = useAutofocus();
            }
        }

        const component = await mountWithCleanup(MyComponent);
        expect(document.activeElement).toBe(component.inputRef.el);

        component.render();
        await animationFrame();
        expect(document.activeElement).toBe(component.inputRef.el);
    });

    test.tags("desktop")("simple usecase when input type is number", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="number" t-ref="autofocus" />
                </span>
            `;
            setup() {
                this.inputRef = useAutofocus();
            }
        }

        const component = await mountWithCleanup(MyComponent);
        expect(document.activeElement).toBe(component.inputRef.el);

        component.render();
        await animationFrame();
        expect(document.activeElement).toBe(component.inputRef.el);
    });

    test.tags("desktop")("conditional autofocus", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input t-if="showInput" type="text" t-ref="autofocus" />
                </span>
            `;
            setup() {
                this.inputRef = useAutofocus();
                this.showInput = true;
            }
        }

        const component = await mountWithCleanup(MyComponent);
        expect(document.activeElement).toBe(component.inputRef.el);

        component.showInput = false;
        component.render();
        await animationFrame();
        expect(document.activeElement).toBe(document.body);

        component.showInput = true;
        component.render();
        await animationFrame();
        expect(document.activeElement).toBe(component.inputRef.el);
    });

    test("returns also a ref when screen has touch but it does not focus", async () => {
        expect(1);
        class MyComponent extends Component {
            static template = xml`
                <span>
                    <input type="text" t-ref="autofocus" />
                </span>
            `;
            static props = ["*"];
            setup() {
                this.inputRef = useAutofocus();
                onMounted(() => {
                    expect(this.inputRef.el).toBeTruthy();
                });
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
        expect(document.activeElement).toBe(document.body);
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
                this.inputRef = useAutofocus({ mobile: true });
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

        const component = await mountWithCleanup(MyComponent);
        expect(document.activeElement).toBe(component.inputRef.el);
    });

    test.tags("desktop")("supports different ref names", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="text" t-ref="first" />
                    <input t-if="state.showSecond" type="text" t-ref="second" />
                </span>
            `;
            setup() {
                this.secondRef = useAutofocus({ refName: "second" });
                this.firstRef = useAutofocus({ refName: "first" }); // test requires this at second position
                this.state = useState({ showSecond: true });
            }
        }

        const component = await mountWithCleanup(MyComponent);

        // "first" is focused first since it has the last call to "useAutofocus"
        expect(document.activeElement).toBe(component.firstRef.el);

        // We now remove and add again the second input, which triggers the useEffect of the hook and and apply focus
        component.state.showSecond = false;
        await animationFrame();
        component.state.showSecond = true;
        await animationFrame();
        expect(document.activeElement).toBe(component.secondRef.el);
    });

    test.tags("desktop")("can select its content", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <span>
                    <input type="text" value="input content" t-ref="autofocus" />
                </span>
            `;
            setup() {
                this.inputRef = useAutofocus({ selectAll: true });
            }
        }

        const component = await mountWithCleanup(MyComponent);
        expect(document.activeElement).toBe(component.inputRef.el);
        expect(component.inputRef.el.selectionStart).toBe(0);
        expect(component.inputRef.el.selectionEnd).toBe(13);
    });

    test.tags("desktop")(
        "autofocus outside of active element doesn't work (CommandPalette)",
        async () => {
            class MyComponent extends Component {
                static props = ["*"];
                static template = xml`
                <div>
                    <input type="text" t-ref="autofocus" />
                </div>
            `;
                setup() {
                    this.inputRef = useAutofocus();
                }
            }

            const component = await mountWithCleanup(MyComponent);
            expect(document.activeElement).toBe(component.inputRef.el);

            const config = { providers: [] };
            component.env.services.dialog.add(CommandPalette, { config });
            await animationFrame();

            expect(".o_command_palette").toHaveCount(1);
            expect(document.activeElement).not.toBe(component.inputRef.el);

            component.render();
            await animationFrame();
            expect(document.activeElement).not.toBe(component.inputRef.el);
        }
    );
});

describe("useBus", () => {
    test("simple usecase", async () => {
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

        const component = await mountWithCleanup(MyComponent);
        const env = getMockEnv();

        env.bus.trigger("test-event");
        expect(["callback"]).toVerifySteps();

        component.__owl__.app.destroy();

        env.bus.trigger("test-event");
        expect([]).toVerifySteps();
    });
});

describe("useService", () => {
    test("unavailable service", async () => {
        class MyComponent extends Component {
            static props = ["*"];
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
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`<div/>`;
            setup() {
                this.toyService = useService("toy_service");
            }
        }

        registry.category("services").add("toy_service", {
            name: "toy_service",
            start: () => {
                return null;
            },
        });

        const component = await mountWithCleanup(MyComponent);
        expect(component.toyService).toBe(null);
    });

    test("async service with protected methods", async () => {
        let nbCalls = 0;
        let def = new Deferred();
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`<div/>`;
            setup() {
                this.objectService = useService("object_service");
                this.functionService = useService("function_service");
            }
        }

        registry.category("services").add("object_service", {
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

        registry.category("services").add("function_service", {
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

        const component = await mountWithCleanup(MyComponent);

        // Functions and methods have the correct this
        def.resolve();
        expect(await component.objectService.asyncMethod()).toBe(component.objectService);
        expect(await component.objectService.asyncMethod.call("boundThis")).toBe("boundThis");
        expect(await component.functionService()).toBe(component);
        expect(await component.functionService.call("boundThis")).toBe("boundThis");
        expect(nbCalls).toBe(4);

        // Functions that were called before the component is destroyed but resolved after never resolve
        def = new Deferred();
        component.objectService.asyncMethod().then(() => expect.step("resolved"));
        component.objectService.asyncMethod.call("boundThis").then(() => expect.step("resolved"));
        component.functionService().then(() => expect.step("resolved"));
        component.functionService.call("boundThis").then(() => expect.step("resolved"));
        expect(nbCalls).toBe(8);
        component.__owl__.app.destroy();
        def.resolve();
        expect([]).toVerifySteps();

        // Calling the functions after the destruction rejects the promise
        expect(component.objectService.asyncMethod()).rejects.toThrow("Component is destroyed");
        expect(component.objectService.asyncMethod.call("boundThis")).rejects.toThrow(
            "Component is destroyed"
        );
        expect(component.functionService()).rejects.toThrow("Component is destroyed");
        expect(component.functionService.call("boundThis")).rejects.toThrow(
            "Component is destroyed"
        );
        expect(nbCalls).toBe(8);
    });
});

describe("useSpellCheck", () => {
    test("ref is on the textarea", async () => {
        // To understand correctly the test, refer to the MDN documentation of spellcheck.
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`<div><textarea t-ref="spellcheck" class="textArea"/></div>`;
            setup() {
                useSpellCheck();
            }
        }

        await mountWithCleanup(MyComponent);

        const fixture = getFixture();
        const textArea = fixture.querySelector(".textArea");

        expect(textArea.spellcheck).toBe(true);
        expect(textArea).not.toHaveAttribute("spellcheck");

        await dispatch(textArea, "blur");
        expect(textArea.spellcheck).toBe(false);
        expect(textArea).toHaveAttribute("spellcheck", "false");

        await contains(textArea).focus();
        expect(textArea.spellcheck).toBe(true);
        expect(textArea).toHaveAttribute("spellcheck", "true");
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

        const fixture = getFixture();
        const textArea = fixture.querySelector(".textArea");

        expect(textArea.spellcheck).toBe(true);
        expect(textArea).not.toHaveAttribute("spellcheck");
        await dispatch(textArea, "blur");

        // Once these assertions pass, it means that the hook is working.
        expect(textArea.spellcheck).toBe(false);
        expect(textArea).toHaveAttribute("spellcheck", "false");
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

        const fixture = getFixture();
        const textArea = fixture.querySelector(".textArea");
        const editableDiv = fixture.querySelector(".editableDiv");

        expect(textArea.spellcheck).toBe(true);
        expect(editableDiv.spellcheck).toBe(true);
        expect(textArea).not.toHaveAttribute("spellcheck");
        expect(editableDiv).not.toHaveAttribute("spellcheck");

        await dispatch(textArea, "blur");
        await dispatch(editableDiv, "blur");
        expect(textArea.spellcheck).toBe(false);
        expect(editableDiv.spellcheck).toBe(false);
        expect(textArea).toHaveAttribute("spellcheck", "false");
        expect(editableDiv).toHaveAttribute("spellcheck", "false");

        await contains(textArea).focus();
        expect(textArea.spellcheck).toBe(true);
        expect(textArea).toHaveAttribute("spellcheck", "true");
        expect(editableDiv.spellcheck).toBe(false);
        expect(editableDiv).toHaveAttribute("spellcheck", "false");

        await contains(editableDiv).focus();
        expect(textArea.spellcheck).toBe(false);
        expect(textArea).toHaveAttribute("spellcheck", "false");
        expect(editableDiv.spellcheck).toBe(true);
        expect(editableDiv).toHaveAttribute("spellcheck", "true");
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

        const fixture = getFixture();
        const textArea = fixture.querySelector(".textArea");
        const editableDiv = fixture.querySelector(".editableDiv");

        expect(textArea.spellcheck).toBe(true);
        expect(editableDiv.spellcheck).toBe(false);
        expect(textArea).not.toHaveAttribute("spellcheck");
        expect(editableDiv).toHaveAttribute("spellcheck", "false");

        await dispatch(textArea, "blur");
        await dispatch(editableDiv, "blur");
        expect(textArea.spellcheck).toBe(false);
        expect(textArea).toHaveAttribute("spellcheck", "false");
        expect(editableDiv.spellcheck).toBe(false);
        expect(editableDiv).toHaveAttribute("spellcheck", "false");

        await contains(textArea).focus();
        expect(textArea.spellcheck).toBe(true);
        expect(textArea).toHaveAttribute("spellcheck", "true");
        expect(editableDiv.spellcheck).toBe(false);
        expect(editableDiv).toHaveAttribute("spellcheck", "false");

        await contains(editableDiv).focus();
        expect(textArea.spellcheck).toBe(false);
        expect(textArea).toHaveAttribute("spellcheck", "false");
        expect(editableDiv.spellcheck).toBe(false);
        expect(editableDiv).toHaveAttribute("spellcheck", "false");
    });
});

describe("useChildRef and useForwardRefToParent", () => {
    test("simple usecase", async () => {
        let childRef;
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
            static template = xml`<div><Child someRef="someRef"/></div>`;
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
            static template = xml`<div><Child t-if="state.hasChild" someRef="someRef"/></div>`;
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
