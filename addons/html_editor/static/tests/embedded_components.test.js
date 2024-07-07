import {
    Counter,
    embedding,
    EmbeddedWrapper,
    EmbeddedWrapperMixin,
} from "@html_editor/../tests/_helpers/embedded_component";
import { getEditableDescendants } from "@html_editor/others/embedded_component_utils";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { parseHTML } from "@html_editor/utils/html";
import { describe, expect, getFixture, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import {
    App,
    Component,
    onMounted,
    onPatched,
    onWillDestroy,
    onWillStart,
    onWillUnmount,
    useRef,
    useState,
    xml,
} from "@odoo/owl";
import { EmbeddedComponentPlugin } from "../src/others/embedded_component_plugin";
import { setupEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { getContent, setSelection } from "./_helpers/selection";
import { deleteBackward, redo, undo } from "./_helpers/user_actions";
import { makeMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";

function getConfig(components) {
    return {
        Plugins: [...MAIN_PLUGINS, EmbeddedComponentPlugin],
        resources: {
            embeddedComponents: components,
        },
    };
}

describe("Mount and Destroy embedded components", () => {
    test("can mount a embedded component", async () => {
        const { el } = await setupEditor(`<div><span data-embedded="counter"></span></div>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        expect(getContent(el)).toBe(
            `<div><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></div>`
        );
        click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<div><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span></div>`
        );
    });

    test("can mount a embedded component from a step", async () => {
        const { el, editor } = await setupEditor(`<div>a[]b</div>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        expect(getContent(el)).toBe(`<div>a[]b</div>`);
        editor.shared.domInsert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.dispatch("ADD_STEP");
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"></span>[]b</div>`
        );
        await animationFrame();
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]b</div>`
        );
        click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span>[]b</div>`
        );
    });

    test("embedded component are mounted and destroyed", async () => {
        const steps = [];
        class Test extends Counter {
            setup() {
                onMounted(() => {
                    steps.push("mounted");
                    expect(this.ref.el.isConnected).toBe(true);
                });
                onWillUnmount(() => {
                    steps.push("willunmount");
                    expect(this.ref.el.isConnected).toBe(true);
                });
                onWillDestroy(() => steps.push("willdestroy"));
            }
        }
        const { el, editor } = await setupEditor(
            `<div><span data-embedded="counter"></span></div>`,
            {
                config: getConfig([embedding("counter", Test)]),
            }
        );
        expect(steps).toEqual(["mounted"]);

        editor.destroy();
        expect(steps).toEqual(["mounted", "willunmount", "willdestroy"]);
        expect(getContent(el)).toBe(
            `<div><span data-embedded="counter" data-oe-protected="true" contenteditable="false"></span></div>`
        );
    });

    test("embedded component are destroyed when deleted", async () => {
        const steps = [];
        class Test extends Counter {
            setup() {
                onMounted(() => {
                    steps.push("mounted");
                    expect(this.ref.el.isConnected).toBe(true);
                });
                onWillUnmount(() => {
                    steps.push("willunmount");
                    expect(this.ref.el?.isConnected).toBe(true);
                });
            }
        }
        const { el, editor } = await setupEditor(
            `<div>a<span data-embedded="counter"></span>[]</div>`,
            {
                config: getConfig([embedding("counter", Test)]),
            }
        );

        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</div>`
        );
        expect(steps).toEqual(["mounted"]);

        deleteBackward(editor);
        expect(steps).toEqual(["mounted", "willunmount"]);
        expect(getContent(el)).toBe(`<div>a[]</div>`);
    });

    test("undo and redo a component insertion", async () => {
        class Test extends Counter {
            setup() {
                onMounted(() => {
                    expect.step("mounted");
                    expect(this.ref.el.isConnected).toBe(true);
                });
                onWillUnmount(() => {
                    expect.step("willunmount");
                    expect(this.ref.el?.isConnected).toBe(true);
                });
            }
        }
        const { el, editor } = await setupEditor(`<div>a[]</div>`, {
            config: getConfig([embedding("counter", Test)]),
        });
        editor.shared.domInsert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.dispatch("ADD_STEP");
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</div>`
        );
        undo(editor);
        expect.verifySteps(["willunmount"]);
        expect(getContent(el)).toBe(`<div>a[]</div>`);
        redo(editor);
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</div>`
        );
        editor.destroy();
        expect.verifySteps(["willunmount"]);
    });

    test("undo and redo a component delete", async () => {
        class Test extends Counter {
            setup() {
                onMounted(() => {
                    expect.step("mounted");
                    expect(this.ref.el.isConnected).toBe(true);
                });
                onWillUnmount(() => {
                    expect.step("willunmount");
                    expect(this.ref.el?.isConnected).toBe(true);
                });
            }
        }
        const { el, editor } = await setupEditor(
            `<div>a<span data-embedded="counter"></span>[]</div>`,
            {
                config: getConfig([embedding("counter", Test)]),
            }
        );

        editor.dispatch("HISTORY_STAGE_SELECTION");

        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</div>`
        );
        expect.verifySteps(["mounted"]);

        deleteBackward(editor);
        expect.verifySteps(["willunmount"]);
        expect(getContent(el)).toBe(`<div>a[]</div>`);

        // now, we undo and check that component still works
        undo(editor);
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"></span>[]</div>`
        );
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</div>`
        );
        click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span>[]</div>`
        );
        redo(editor);
        expect.verifySteps(["willunmount"]);
        expect(getContent(el)).toBe(`<div>a[]</div>`);
    });

    test("mount and destroy components after a savepoint", async () => {
        class Test extends Counter {
            setup() {
                onMounted(() => {
                    expect.step("mounted");
                });
                onWillUnmount(() => {
                    expect.step("willunmount");
                });
            }
        }
        const { el, editor } = await setupEditor(
            `<div>a<span data-embedded="counter"></span>[]</div>`,
            {
                config: getConfig([embedding("counter", Test)]),
            }
        );
        editor.dispatch("HISTORY_STAGE_SELECTION");
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</div>`
        );
        expect.verifySteps(["mounted"]);
        const savepoint = editor.shared.makeSavePoint();
        deleteBackward(editor);
        expect.verifySteps(["willunmount"]);
        expect(getContent(el)).toBe(`<div>a[]</div>`);
        editor.shared.domInsert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.dispatch("ADD_STEP");
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</div>`
        );
        savepoint();
        expect.verifySteps(["willunmount"]);
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<div>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</div>`
        );
        editor.destroy();
        expect.verifySteps(["willunmount"]);
    });

    test("embedded component plugin does not try to destroy the same app twice", async () => {
        patchWithCleanup(EmbeddedComponentPlugin.prototype, {
            destroyComponent() {
                expect.step("destroy from plugin");
                super.destroyComponent(...arguments);
            },
        });
        class Test extends Counter {
            setup() {
                onWillDestroy(() => {
                    expect.step("willdestroy");
                });
            }
        }
        const { editor } = await setupEditor(
            `<div>a<span data-embedded="counter"></span>[]</div>`,
            {
                config: getConfig([embedding("counter", Test)]),
            }
        );
        deleteBackward(editor);
        expect.verifySteps(["destroy from plugin", "willdestroy"]);
        editor.destroy();
        expect.verifySteps([]);
    });

    test("Can mount and destroy recursive embedded components in any order", async () => {
        class RecursiveComponent extends Component {
            static template = xml`
                <div>
                    <div t-on-click="increment" t-att-class="'click count-' + props.index">Count:<t t-esc="state.value"/></div>
                    <div t-ref="innerEditable" t-att-class="'innerEditable-' + props.index"/>
                </div>
            `;
            static props = {
                innerValue: HTMLElement,
                index: Number,
            };
            setup() {
                this.innerEditableRef = useRef("innerEditable");
                this.state = useState({
                    value: this.props.index,
                });
                onMounted(() => {
                    this.props.innerValue.dataset.oeProtected = "false";
                    this.props.innerValue.setAttribute("contenteditable", "true");
                    this.innerEditableRef.el.append(this.props.innerValue);
                    expect.step(`mount ${this.props.index}`);
                });
                onWillDestroy(() => {
                    expect.step(`destroy ${this.props.index}`);
                });
            }
            increment() {
                this.state.value++;
            }
        }
        let index = 1;
        const { el, editor, plugins } = await setupEditor(`<div class="target">[]</div>`, {
            config: getConfig([
                embedding("recursiveComponent", RecursiveComponent, (host) => {
                    const result = {
                        index,
                        innerValue: host.querySelector("[data-prop-name='innerValue']"),
                    };
                    index++;
                    return result;
                }),
            ]),
        });
        editor.shared.domInsert(
            parseHTML(
                editor.document,
                unformat(`
                    <div data-embedded="recursiveComponent">
                        <div data-prop-name="innerValue" data-oe-protected="false">
                            <div data-embedded="recursiveComponent">
                                <div data-prop-name="innerValue" data-oe-protected="false">
                                    <div data-embedded="recursiveComponent">
                                        <div data-prop-name="innerValue" data-oe-protected="false">
                                            <p>HELL</p>
                                        </div>
                                    </div>    
                                </div>
                            </div>    
                        </div>
                    </div>        
                `)
            )
        );
        const indexOrder = [1, 0, 2];
        const orderedMountInfos = [];
        const embeddedComponentPlugin = plugins.get("embedded_components");
        embeddedComponentPlugin.forEachEmbeddedComponentHost(el, (host, embedding) => {
            orderedMountInfos.push([host, embedding]);
        });
        // Force mounting disorder.
        for (const index of indexOrder) {
            embeddedComponentPlugin.mountComponent(...orderedMountInfos[index]);
        }
        // Validate the step, but the mounting process already started.
        editor.dispatch("ADD_STEP");
        await animationFrame();
        expect.verifySteps(["mount 1", "mount 2", "mount 3"]);
        expect(getContent(el)).toBe(
            unformat(`
                <div class="target">
                    <div data-embedded="recursiveComponent" data-oe-protected="true" contenteditable="false">
                        <div>
                            <div class="click count-2">Count:2</div>
                            <div class="innerEditable-2">
                                <div data-prop-name="innerValue" data-oe-protected="false" contenteditable="true">
                                    <div data-embedded="recursiveComponent" data-oe-protected="true" contenteditable="false">
                                        <div>
                                            <div class="click count-1">Count:1</div>
                                            <div class="innerEditable-1">
                                                <div data-prop-name="innerValue" data-oe-protected="false" contenteditable="true">
                                                    <div data-embedded="recursiveComponent" data-oe-protected="true" contenteditable="false">
                                                        <div>
                                                            <div class="click count-3">Count:3</div>
                                                            <div class="innerEditable-3">
                                                                <div data-prop-name="innerValue" data-oe-protected="false" contenteditable="true">
                                                                    <p>HELL</p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                []</div>
            `)
        );
        for (const index of indexOrder) {
            const host = orderedMountInfos[index][0];
            click(host.querySelector(".click"));
        }
        await animationFrame();
        expect(el.querySelector(".count-1").textContent).toBe("Count:2");
        expect(el.querySelector(".count-2").textContent).toBe("Count:3");
        expect(el.querySelector(".count-3").textContent).toBe("Count:4");
        for (const index of indexOrder) {
            const host = orderedMountInfos[index][0];
            embeddedComponentPlugin.deepDestroyComponent({ host });
        }
        // Hierarchy is, referring to the index prop: 2 > 1 > 3
        // destroying order is, by index prop: 1, 2, 3
        // destroying 1 removes 3 from the dom, therefore 3 is destroyed in
        // the process of destroying 1, that is why it is done before 2.
        expect.verifySteps(["destroy 1", "destroy 3", "destroy 2"]);
        // OWL:App.destroy removes every node inside its host during destroy,
        // so after the full operation, nothing should be left except the
        // outermost host.
        expect(getContent(el)).toBe(
            unformat(`
                <div class="target">
                    <div data-embedded="recursiveComponent" data-oe-protected="true" contenteditable="false"></div>
                []</div>
            `)
        );
        // Verify that there is no potential host outside of the editable,
        // because removed hosts are put back in the DOM and destroyed next to
        // the editable element, before being removed again.
        const fixture = getFixture();
        expect(
            [...fixture.querySelectorAll("[data-embedded]")].filter((elem) => {
                return !elem.closest(".odoo-editor-editable");
            })
        ).toEqual([]);
    });

    test("Can destroy a component from a removed host", async () => {
        patchWithCleanup(EmbeddedComponentPlugin.prototype, {
            destroyComponent({ host }) {
                expect(this.editable.contains(host)).toBe(false);
                super.destroyComponent(...arguments);
                expect.step(`destroyed ${host.dataset.embedded}`);
            },
        });
        const { editor, el } = await setupEditor(
            `<div><span data-embedded="counter"></span>ALONE</div>`,
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        const host = el.querySelector("[data-embedded='counter']");
        host.remove();
        editor.dispatch("ADD_STEP");
        expect.verifySteps(["destroyed counter"]);
        // Verify that there is no potential host outside of the editable,
        // because removed hosts are put back in the DOM and destroyed next to
        // the editable element, before being removed again.
        const fixture = getFixture();
        expect(
            [...fixture.querySelectorAll("[data-embedded]")].filter((elem) => {
                return !elem.closest(".odoo-editor-editable");
            })
        ).toEqual([]);
    });

    test("Can destroy a component from a removed host's parent, and give the host back to the parent", async () => {
        let hostElement;
        patchWithCleanup(EmbeddedComponentPlugin.prototype, {
            destroyComponent({ host }) {
                hostElement = host;
                expect(this.editable.contains(host)).toBe(false);
                super.destroyComponent(...arguments);
                expect.step(`destroyed ${host.dataset.embedded}`);
            },
        });
        const { editor, el } = await setupEditor(
            `<div><div class="parent"><span data-embedded="counter"></span></div>ALONE</div>`,
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        const parent = el.querySelector(".parent");
        parent.remove();
        editor.dispatch("ADD_STEP");
        expect.verifySteps(["destroyed counter"]);
        // Verify that there is no potential host outside of the editable,
        // because removed hosts are put back in the DOM and destroyed next to
        // the editable element, before being removed again.
        const fixture = getFixture();
        expect(
            [...fixture.querySelectorAll("[data-embedded]")].filter((elem) => {
                return !elem.closest(".odoo-editor-editable");
            })
        ).toEqual([]);
        expect(editor.editable.contains(parent)).toBe(false);
        expect(parent.contains(hostElement)).toBe(true);
    });
});

describe("Selection after embedded component insertion", () => {
    test("inline in empty paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.domInsert(
            parseHTML(editor.document, `<span data-embedded="counter">a</span>`)
        );
        editor.dispatch("ADD_STEP");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
    });
    test("inline at the end of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>a[]</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.domInsert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.dispatch("ADD_STEP");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
    });
    test("inline at the start of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]a</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.domInsert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.dispatch("ADD_STEP");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]a</p>`
        );
    });
    test("inline in the middle of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>a[]b</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.domInsert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.dispatch("ADD_STEP");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]b</p>`
        );
    });
    test("block in empty paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.domInsert(parseHTML(editor.document, `<div data-embedded="counter"></div>`));
        editor.dispatch("ADD_STEP");
        await animationFrame();
        editor.dispatch("CLEAN", { root: editor.editable });
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></div>
                <p>[]<br></p>`)
        );
    });
    test("block at the end of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>a[]</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.domInsert(parseHTML(editor.document, `<div data-embedded="counter"></div>`));
        editor.dispatch("ADD_STEP");
        await animationFrame();
        editor.dispatch("CLEAN", { root: editor.editable });
        expect(getContent(el)).toBe(
            unformat(`
                <p>a</p>
                <div data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></div>
                <p>[]<br></p>`)
        );
    });
    test("block at the start of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]a</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.domInsert(parseHTML(editor.document, `<div data-embedded="counter"></div>`));
        editor.dispatch("ADD_STEP");
        await animationFrame();
        editor.dispatch("CLEAN", { root: editor.editable });
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></div>
                <p>[]a</p>`)
        );
    });
    test("block in the middle of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>a[]b</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.domInsert(parseHTML(editor.document, `<div data-embedded="counter"></div>`));
        editor.dispatch("ADD_STEP");
        await animationFrame();
        editor.dispatch("CLEAN", { root: editor.editable });
        expect(getContent(el)).toBe(
            unformat(`
                <p>a</p>
                <div data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></div>
                <p>[]b</p>`)
        );
    });
});

describe("Mount processing", () => {
    test("embedded component get proper props", async () => {
        class Test extends Counter {
            static props = ["initialCount"];
            setup() {
                expect(this.props.initialCount).toBe(10);
                this.state.value = this.props.initialCount;
            }
        }
        const { el } = await setupEditor(`<div><span data-embedded="counter"></span></div>`, {
            config: getConfig([embedding("counter", Test, () => ({ initialCount: 10 }))]),
        });

        expect(getContent(el)).toBe(
            `<div><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:10</span></span></div>`
        );
    });

    test("embedded component can compute props from element", async () => {
        class Test extends Counter {
            static props = ["initialCount"];
            setup() {
                expect(this.props.initialCount).toBe(10);
                this.state.value = this.props.initialCount;
            }
        }
        const { el } = await setupEditor(
            `<div><span data-embedded="counter" data-count="10"></span></div>`,
            {
                config: getConfig([
                    embedding("counter", Test, (host) => ({
                        initialCount: parseInt(host.dataset.count),
                    })),
                ]),
            }
        );

        expect(getContent(el)).toBe(
            `<div><span data-embedded="counter" data-count="10" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:10</span></span></div>`
        );
    });

    test("embedded component can set attributes on host element", async () => {
        class Test extends Counter {
            static props = ["host"];
            setup() {
                const initialCount = parseInt(this.props.host.dataset.count);
                this.state.value = initialCount;
            }
            increment() {
                super.increment();
                this.props.host.dataset.count = this.state.value;
            }
        }
        const { el } = await setupEditor(
            `<div><span data-embedded="counter" data-count="10"></span></div>`,
            {
                config: getConfig([embedding("counter", Test, (host) => ({ host }))]),
            }
        );

        expect(getContent(el)).toBe(
            `<div><span data-embedded="counter" data-count="10" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:10</span></span></div>`
        );

        click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<div><span data-embedded="counter" data-count="11" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:11</span></span></div>`
        );
    });

    test("embedded component get proper env", async () => {
        /** @type { any } */
        let env;
        class Test extends Counter {
            setup() {
                env = this.env;
            }
        }

        const rootEnv = await makeMockEnv();
        await setupEditor(`<div><span data-embedded="counter"></span></div>`, {
            config: getConfig([embedding("counter", Test)]),
            env: Object.assign(rootEnv, { somevalue: 1 }),
        });
        expect(env.somevalue).toBe(1);
    });

    test("Content within an embedded component host is removed when mounting", async () => {
        const { el } = await setupEditor(`<div><span data-embedded="counter">hello</span></div>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        expect(getContent(el)).toBe(
            `<div><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></div>`
        );
    });

    test("Host child nodes are removed synchronously with the insertion of owl rendered nodes during mount", async () => {
        const asyncControl = new Deferred();
        asyncControl.then(() => {
            expect.step("minimal asynchronous time");
        });
        patchWithCleanup(App.prototype, {
            mount(elem) {
                const result = super.mount(...arguments);
                if (elem.dataset.embedded === "labeledCounter") {
                    const fiber = Array.from(this.scheduler.tasks)[0];
                    const fiberComplete = fiber.complete;
                    fiber.complete = function () {
                        expect.step("html prop suppression");
                        asyncControl.resolve();
                        fiberComplete.call(this);
                    };
                }
                return result;
            },
        });
        const delayedWillStart = new Deferred();
        class LabeledCounter extends Counter {
            static template = xml`
                <span t-ref="root" class="counter" t-on-click="increment">
                    <span t-ref="label"/>:<t t-esc="state.value"/>
                </span>
            `;
            static props = {
                label: HTMLElement,
            };
            labelRef = useRef("label");
            setup() {
                onWillStart(async () => {
                    expect.step("willstart");
                    await delayedWillStart;
                });
                onMounted(() => {
                    this.props.label.dataset.oeProtected = "false";
                    this.props.label.setAttribute("contenteditable", "true");
                    this.labelRef.el.append(this.props.label);
                    expect.step("html prop insertion");
                });
            }
        }
        const { el } = await setupEditor(
            `<div><span data-embedded="labeledCounter">
                <span data-prop-name="label">Counter</span>
            </span>[]a</div>`,
            {
                config: getConfig([
                    embedding("labeledCounter", LabeledCounter, (host) => ({
                        label: host.querySelector("[data-prop-name='label']"),
                    })),
                ]),
            }
        );
        expect.verifySteps(["willstart"]);
        delayedWillStart.resolve();
        await animationFrame();
        expect(getContent(el)).toBe(
            unformat(`
                <div>
                    <span data-embedded="labeledCounter" data-oe-protected="true" contenteditable="false">
                        <span class="counter">
                            <span>
                                <span data-prop-name="label" data-oe-protected="false" contenteditable="true">Counter</span>
                            </span>
                            :0
                        </span>
                    </span>
                    []a
                </div>
            `)
        );
        expect.verifySteps([
            "html prop suppression",
            "html prop insertion",
            "minimal asynchronous time",
        ]);
    });

    test("Ignore unknown data-embedded types for mounting", async () => {
        patchWithCleanup(EmbeddedComponentPlugin.prototype, {
            handleComponents() {
                const getEmbedding = this.getEmbedding;
                this.getEmbedding = (host) => {
                    expect.step(`${host.dataset.embedded} handled`);
                    return getEmbedding.call(this, host);
                };
                super.handleComponents(...arguments);
                this.getEmbedding = getEmbedding;
            },
            mountComponent(host) {
                super.mountComponent(...arguments);
                expect.step(`${host.dataset.embedded} mounted`);
            },
        });
        const { el } = await setupEditor(`<div data-embedded="unknown"><p>UNKNOWN</p></div>`, {
            config: getConfig([]),
        });
        // "unknown" data-embedded should be considered once during the first
        // mounting wave.
        expect.verifySteps(["unknown handled"]);
        expect(getContent(el)).toBe(`<div data-embedded="unknown"><p>UNKNOWN</p></div>`);
    });
});

describe("In-editor manipulations", () => {
    test("select content of a component shouldn't open the toolbar", async () => {
        const { el } = await setupEditor(
            `<div><p>[a]</p><span data-embedded="counter"></span></div>`,
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        await animationFrame();
        expect(".o-we-toolbar").toHaveCount(1);
        expect(getContent(el)).toBe(
            `<div><p>[a]</p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></div>`
        );

        const node = queryFirst(".counter", {}).firstChild;
        setSelection({ anchorNode: node, anchorOffset: 1, focusNode: node, focusOffset: 3 });
        await tick();
        await animationFrame();
        expect(getContent(el)).toBe(
            `<div><p>a</p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">C[ou]nter:0</span></span></div>`
        );
        expect(".o-we-toolbar").toHaveCount(0);
    });

    test("should remove embedded elements children during clean for save (on a clone)", async () => {
        const { el, editor } = await setupEditor(
            '<div><p>a</p></div><div data-embedded="counter"><p>a</p></div>',
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        const clone = el.cloneNode(true);
        editor.dispatch("CLEAN_FOR_SAVE", { root: clone });
        expect(getContent(clone)).toBe(`<div><p>a</p></div><div data-embedded="counter"></div>`);
    });

    test("should not remove embedded elements children during clean (not a clone)", async () => {
        const { el, editor } = await setupEditor(
            '<div><p>a</p></div><div data-embedded="counter"><p>a</p></div>',
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        editor.dispatch("CLEAN", { root: el });
        expect(getContent(el)).toBe(
            `<div><p>a</p></div><div data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></div>`
        );
    });

    test("should ignore embedded elements children during serialization", async () => {
        const { el, plugins } = await setupEditor(
            `<div><p>a</p></div><div data-embedded="counter"><p>a</p></div>`,
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        const historyPlugin = plugins.get("history");
        const node = historyPlugin.unserializeNode(historyPlugin.serializeNode(el));
        expect(getContent(node, { sortAttrs: true })).toBe(
            `<div><p>a</p></div><div contenteditable="false" data-embedded="counter" data-oe-protected="true"></div>`
        );
    });

    test("Ignore unknown data-embedded types for cleanforsave", async () => {
        const { editor, el } = await setupEditor(
            `<div data-embedded="unknown"><p>UNKNOWN</p></div>`,
            { config: getConfig([]) }
        );
        editor.dispatch("CLEAN_FOR_SAVE", { root: el });
        expect(getContent(el)).toBe(`<div data-embedded="unknown"><p>UNKNOWN</p></div>`);
    });

    test("Ignore unknown data-embedded types for serialization", async () => {
        const { el, plugins } = await setupEditor(
            `<div data-embedded="unknown"><p>UNKNOWN</p></div>`,
            { config: getConfig([]) }
        );
        const historyPlugin = plugins.get("history");
        const node = historyPlugin.unserializeNode(historyPlugin.serializeNode(el));
        expect(getContent(node)).toBe(`<div data-embedded="unknown"><p>UNKNOWN</p></div>`);
    });
});

describe("editable descendants", () => {
    test("editable descendants are extracted and put back in place during mount", async () => {
        const { el } = await setupEditor(
            unformat(`
                <div data-embedded="wrapper">
                    <div data-embedded-editable="shallow">
                        <p>shallow</p>
                    </div>
                    <div data-embedded-editable="deep">
                        <p>deep</p>
                    </div>
                </div>
            `),
            {
                config: getConfig([
                    embedding(
                        "wrapper",
                        EmbeddedWrapper,
                        (host) => ({ host }),
                        getEditableDescendants
                    ),
                ]),
            }
        );
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="wrapper" data-oe-protected="true" contenteditable="false">
                    <div class="shallow">
                        <div data-embedded-editable="shallow" data-oe-protected="false" contenteditable="true">
                            <p>shallow</p>
                        </div>
                    </div>
                    <div>
                        <div class="deep">
                            <div data-embedded-editable="deep" data-oe-protected="false" contenteditable="true">
                                <p>deep</p>
                            </div>
                        </div>
                    </div>
                </div>
            `)
        );
    });

    test("editable descendants are extracted and put back in place when a patch is changing the template shape", async () => {
        let wrapper;
        patchWithCleanup(EmbeddedWrapper.prototype, {
            setup() {
                super.setup();
                wrapper = this;
                onPatched(() => {
                    expect.step("patched");
                });
            },
        });
        const { editor, el, plugins } = await setupEditor(
            unformat(`
                <div data-embedded="wrapper">
                    <div data-embedded-editable="shallow">
                        <p>shallow</p>
                    </div>
                    <div data-embedded-editable="deep">
                        <p>deep</p>
                    </div>
                </div>
            `),
            {
                config: getConfig([
                    embedding(
                        "wrapper",
                        EmbeddedWrapper,
                        (host) => ({ host }),
                        getEditableDescendants
                    ),
                ]),
            }
        );
        wrapper.state.switch = true;
        await animationFrame();
        expect.verifySteps(["patched"]);
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="wrapper" data-oe-protected="true" contenteditable="false">
                    <div class="shallow">
                        <div data-embedded-editable="shallow" data-oe-protected="false" contenteditable="true">
                            <p>shallow</p>
                        </div>
                    </div>
                    <div>
                        <div class="switched">
                            <div class="deep">
                                <div data-embedded-editable="deep" data-oe-protected="false" contenteditable="true">
                                    <p>deep</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `)
        );
        // No mutation should be added to the next step
        editor.dispatch("ADD_STEP");
        const historyPlugin = plugins.get("history");
        const historySteps = editor.shared.getHistorySteps();
        expect(historySteps.length).toBe(1);
        expect(historyPlugin.currentStep.mutations).toEqual([]);
    });

    test("editable descendants are extracted and put back in place during cleanforsave", async () => {
        const { el, editor } = await setupEditor(
            unformat(`
                <div data-embedded="wrapper">
                    <div data-embedded-editable="shallow">
                        <p>shallow</p>
                    </div>
                    <div data-embedded-editable="deep">
                        <p>deep</p>
                    </div>
                </div>
            `),
            {
                config: getConfig([
                    embedding(
                        "wrapper",
                        EmbeddedWrapper,
                        (host) => ({ host }),
                        getEditableDescendants
                    ),
                ]),
            }
        );
        const clone = el.cloneNode(true);
        editor.dispatch("CLEAN_FOR_SAVE", { root: clone });
        expect(getContent(clone)).toBe(
            unformat(`
                <div data-embedded="wrapper">
                    <div data-embedded-editable="shallow">
                        <p>shallow</p>
                    </div>
                    <div data-embedded-editable="deep">
                        <p>deep</p>
                    </div>
                </div>
            `)
        );
    });

    test("editable descendants are extracted and put back in place during serialization", async () => {
        const { el, plugins } = await setupEditor(
            unformat(`
                <div data-embedded="wrapper">
                    <div data-embedded-editable="shallow">
                        <p>shallow</p>
                    </div>
                    <div data-embedded-editable="deep">
                        <p>deep</p>
                    </div>
                </div>
            `),
            {
                config: getConfig([
                    embedding(
                        "wrapper",
                        EmbeddedWrapper,
                        (host) => ({ host }),
                        getEditableDescendants
                    ),
                ]),
            }
        );
        const historyPlugin = plugins.get("history");
        const node = historyPlugin.unserializeNode(historyPlugin.serializeNode(el));
        expect(getContent(node, { sortAttrs: true })).toBe(
            unformat(`
                <div contenteditable="false" data-embedded="wrapper" data-oe-protected="true">
                    <div contenteditable="true" data-embedded-editable="shallow" data-oe-protected="false">
                        <p>shallow</p>
                    </div>
                    <div contenteditable="true" data-embedded-editable="deep" data-oe-protected="false">
                        <p>deep</p>
                    </div>
                </div>
            `)
        );
    });

    test("can discriminate own editable descendants from editable descendants of a descendant", async () => {
        const SimpleEmbeddedWrapper = EmbeddedWrapperMixin("deep");
        const { el } = await setupEditor(
            unformat(`
                <div data-embedded="wrapper">
                    <div data-embedded-editable="shallow">
                        <div data-embedded="simpleWrapper">
                            <div data-embedded-editable="deep">
                                <p>simple-deep</p>
                            </div>
                        </div>
                    </div>
                    <div data-embedded-editable="deep">
                        <p>wrapper-deep</p>
                    </div>
                </div>
            `),
            {
                config: getConfig([
                    embedding(
                        "simpleWrapper",
                        SimpleEmbeddedWrapper,
                        (host) => ({ host }),
                        getEditableDescendants
                    ),
                    embedding(
                        "wrapper",
                        EmbeddedWrapper,
                        (host) => ({ host }),
                        getEditableDescendants
                    ),
                ]),
            }
        );
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="wrapper" data-oe-protected="true" contenteditable="false">
                    <div class="shallow">
                        <div data-embedded-editable="shallow" data-oe-protected="false" contenteditable="true">
                            <div data-embedded="simpleWrapper" data-oe-protected="true" contenteditable="false">
                                <div class="deep">
                                    <div data-embedded-editable="deep" data-oe-protected="false" contenteditable="true">
                                        <p>simple-deep</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div>
                        <div class="deep">
                            <div data-embedded-editable="deep" data-oe-protected="false" contenteditable="true">
                                <p>wrapper-deep</p>
                            </div>
                        </div>
                    </div>
                </div>
            `)
        );
        const wrapper = el.querySelector(`[data-embedded="wrapper"]`);
        const simple = el.querySelector(`[data-embedded="simpleWrapper"]`);
        const editableDescendants = el.querySelectorAll(`[data-embedded-editable="deep"]`);
        expect(getEditableDescendants(simple).deep).toBe(editableDescendants[0]);
        expect(getEditableDescendants(wrapper).deep).toBe(editableDescendants[1]);
    });
});
