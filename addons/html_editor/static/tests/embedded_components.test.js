import {
    Counter,
    embedding,
    EmbeddedWrapper,
    EmbeddedWrapperMixin,
    namedCounter,
    NamedCounter,
    OffsetCounter,
    offsetCounter,
    SavedCounter,
    savedCounter,
} from "@html_editor/../tests/_helpers/embedded_component";
import {
    getEditableDescendants,
    StateChangeManager,
} from "@html_editor/others/embedded_component_utils";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { parseHTML } from "@html_editor/utils/html";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
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
import { addStep, deleteBackward, deleteForward, redo, undo } from "./_helpers/user_actions";
import { makeMockEnv, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";
import { Plugin } from "@html_editor/plugin";
import { dispatchClean, dispatchCleanForSave } from "./_helpers/dispatch";
import { expectElementCount } from "./_helpers/ui_expectations";

function getConfig(components) {
    return {
        Plugins: [...MAIN_PLUGINS, EmbeddedComponentPlugin],
        resources: {
            embedded_components: components,
        },
    };
}

describe("Mount and Destroy embedded components", () => {
    test("can mount a embedded component", async () => {
        const { el } = await setupEditor(`<p><span data-embedded="counter"></span></p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span></p>`
        );
    });

    test("can mount a embedded component from a step", async () => {
        const { el, editor } = await setupEditor(`<p>a[]b</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        expect(getContent(el)).toBe(`<p>a[]b</p>`);
        editor.shared.dom.insert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"></span>[]b</p>`
        );
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]b</p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span>[]b</p>`
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
        const { el, editor } = await setupEditor(`<p><span data-embedded="counter"></span></p>`, {
            config: getConfig([embedding("counter", Test)]),
        });
        expect(steps).toEqual(["mounted"]);

        editor.destroy();
        expect(steps).toEqual(["mounted", "willunmount", "willdestroy"]);
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"></span></p>`
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
            `<p>a<span data-embedded="counter"></span>[]</p>`,
            {
                config: getConfig([embedding("counter", Test)]),
            }
        );

        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
        expect(steps).toEqual(["mounted"]);

        deleteBackward(editor);
        expect(steps).toEqual(["mounted", "willunmount"]);
        expect(getContent(el)).toBe(`<p>a[]</p>`);
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
        const { el, editor } = await setupEditor(`<p>a[]</p>`, {
            config: getConfig([embedding("counter", Test)]),
        });
        editor.shared.dom.insert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.shared.history.addStep();
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
        undo(editor);
        expect.verifySteps(["willunmount"]);
        expect(getContent(el)).toBe(`<p>a[]</p>`);
        redo(editor);
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
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
            `<p>a<span data-embedded="counter"></span>[]</p>`,
            {
                config: getConfig([embedding("counter", Test)]),
            }
        );

        editor.shared.history.stageSelection();

        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
        expect.verifySteps(["mounted"]);

        deleteBackward(editor);
        expect.verifySteps(["willunmount"]);
        expect(getContent(el)).toBe(`<p>a[]</p>`);

        // now, we undo and check that component still works
        undo(editor);
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"></span>[]</p>`
        );
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span>[]</p>`
        );
        redo(editor);
        expect.verifySteps(["willunmount"]);
        expect(getContent(el)).toBe(`<p>a[]</p>`);
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
            `<p>a<span data-embedded="counter"></span>[]</p>`,
            {
                config: getConfig([embedding("counter", Test)]),
            }
        );
        editor.shared.history.stageSelection();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
        expect.verifySteps(["mounted"]);
        const savepoint = editor.shared.history.makeSavePoint();
        deleteBackward(editor);
        expect.verifySteps(["willunmount"]);
        expect(getContent(el)).toBe(`<p>a[]</p>`);
        editor.shared.dom.insert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.shared.history.addStep();
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
        savepoint();
        expect.verifySteps(["willunmount"]);
        await animationFrame();
        expect.verifySteps(["mounted"]);
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
        editor.destroy();
        expect.verifySteps(["willunmount"]);
    });

    test("embedded component plugin does not try to destroy the same subroot twice", async () => {
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
        const { editor } = await setupEditor(`<p>a<span data-embedded="counter"></span>[]</p>`, {
            config: getConfig([embedding("counter", Test)]),
        });
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
        const { el, editor, plugins } = await setupEditor(`<p class="target">[]</p>`, {
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
        editor.shared.dom.insert(
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
        const embeddedComponentPlugin = plugins.get("embeddedComponents");
        embeddedComponentPlugin.forEachEmbeddedComponentHost(el, (host, embedding) => {
            orderedMountInfos.push([host, embedding]);
        });
        // Force mounting disorder.
        for (const index of indexOrder) {
            embeddedComponentPlugin.mountComponent(...orderedMountInfos[index]);
        }
        // Validate the step, but the mounting process already started.
        editor.shared.history.addStep();
        await animationFrame();
        expect.verifySteps(["mount 1", "mount 2", "mount 3"]);
        expect(getContent(el)).toBe(
            unformat(`
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
                <p class="target o-we-hint" placeholder='Type "/" for commands'>[]<br></p>
            `)
        );
        for (const index of indexOrder) {
            const host = orderedMountInfos[index][0];
            await click(host.querySelector(".click"));
        }
        await animationFrame();
        expect(el.querySelector(".count-1")).toHaveText("Count:2");
        expect(el.querySelector(".count-2")).toHaveText("Count:3");
        expect(el.querySelector(".count-3")).toHaveText("Count:4");
        for (const index of indexOrder) {
            const host = orderedMountInfos[index][0];
            embeddedComponentPlugin.deepDestroyComponent({ host });
        }
        // Hierarchy is, referring to the index prop: 2 > 1 > 3
        // destroying order is, by index prop: 1, 2, 3
        // destroying 1 removes 3 from the dom, therefore 3 is destroyed in
        // the process of destroying 1, that is why it is done before 2.
        expect.verifySteps(["destroy 1", "destroy 3", "destroy 2"]);
        // OWL:Root.destroy removes every node inside its host during destroy,
        // so after the full operation, nothing should be left except the
        // outermost host.
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="recursiveComponent" data-oe-protected="true" contenteditable="false"></div>
                <p class="target o-we-hint" placeholder='Type "/" for commands'>[]<br></p>
            `)
        );
        // Verify that there is no potential host outside of the editable,
        // because removed hosts are put back in the DOM and destroyed next to
        // the editable element, before being removed again.
        const fixture = getFixture();
        expect(
            [...fixture.querySelectorAll("[data-embedded]")].filter(
                (elem) => !elem.closest(".odoo-editor-editable")
            )
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
            `<p><span data-embedded="counter"></span>ALONE</p>`,
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        const host = el.querySelector("[data-embedded='counter']");
        host.remove();
        editor.shared.history.addStep();
        expect.verifySteps(["destroyed counter"]);
        // Verify that there is no potential host outside of the editable,
        // because removed hosts are put back in the DOM and destroyed next to
        // the editable element, before being removed again.
        const fixture = getFixture();
        expect(
            [...fixture.querySelectorAll("[data-embedded]")].filter(
                (elem) => !elem.closest(".odoo-editor-editable")
            )
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
            `<div><p class="parent"><span data-embedded="counter"></span></p>ALONE</div>`,
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        const parent = el.querySelector(".parent");
        parent.remove();
        editor.shared.history.addStep();
        expect.verifySteps(["destroyed counter"]);
        // Verify that there is no potential host outside of the editable,
        // because removed hosts are put back in the DOM and destroyed next to
        // the editable element, before being removed again.
        const fixture = getFixture();
        expect(
            [...fixture.querySelectorAll("[data-embedded]")].filter(
                (elem) => !elem.closest(".odoo-editor-editable")
            )
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
        editor.shared.dom.insert(
            parseHTML(editor.document, `<span data-embedded="counter">a</span>`)
        );
        editor.shared.history.addStep();
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
    });
    test("inline at the end of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>a[]</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.dom.insert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.shared.history.addStep();
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]</p>`
        );
    });
    test("inline at the start of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]a</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.dom.insert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.shared.history.addStep();
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]a</p>`
        );
    });
    test("inline in the middle of paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>a[]b</p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.dom.insert(
            parseHTML(editor.document, `<span data-embedded="counter"></span>`)
        );
        editor.shared.history.addStep();
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a<span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span>[]b</p>`
        );
    });
    test("block in empty paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        editor.shared.dom.insert(parseHTML(editor.document, `<div data-embedded="counter"></div>`));
        editor.shared.history.addStep();
        await animationFrame();
        dispatchClean(editor);
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
        editor.shared.dom.insert(parseHTML(editor.document, `<div data-embedded="counter"></div>`));
        editor.shared.history.addStep();
        await animationFrame();
        dispatchClean(editor);
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
        editor.shared.dom.insert(parseHTML(editor.document, `<div data-embedded="counter"></div>`));
        editor.shared.history.addStep();
        await animationFrame();
        dispatchClean(editor);
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
        editor.shared.dom.insert(parseHTML(editor.document, `<div data-embedded="counter"></div>`));
        editor.shared.history.addStep();
        await animationFrame();
        dispatchClean(editor);
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
        const { el } = await setupEditor(`<p><span data-embedded="counter"></span></p>`, {
            config: getConfig([embedding("counter", Test, () => ({ initialCount: 10 }))]),
        });

        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:10</span></span></p>`
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
            `<p><span data-embedded="counter" data-count="10"></span></p>`,
            {
                config: getConfig([
                    embedding("counter", Test, (host) => ({
                        initialCount: parseInt(host.dataset.count),
                    })),
                ]),
            }
        );

        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-count="10" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:10</span></span></p>`
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
            `<p><span data-embedded="counter" data-count="10"></span></p>`,
            {
                config: getConfig([embedding("counter", Test, (host) => ({ host }))]),
            }
        );

        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-count="10" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:10</span></span></p>`
        );

        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-count="11" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:11</span></span></p>`
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
        await setupEditor(`<p><span data-embedded="counter"></span></p>`, {
            config: getConfig([embedding("counter", Test)]),
            env: Object.assign(rootEnv, { somevalue: 1 }),
        });
        expect(env.somevalue).toBe(1);
    });

    test("Content within an embedded component host is removed when mounting", async () => {
        const { el } = await setupEditor(`<p><span data-embedded="counter">hello</span></p>`, {
            config: getConfig([embedding("counter", Counter)]),
        });
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></p>`
        );
    });

    test("Host child nodes are removed synchronously with the insertion of owl rendered nodes during mount", async () => {
        const asyncControl = new Deferred();
        asyncControl.then(() => {
            expect.step("minimal asynchronous time");
        });
        patchWithCleanup(App.prototype, {
            createRoot(Root, config) {
                if (Root.name !== "LabeledCounter") {
                    return super.createRoot(...arguments);
                }
                const root = super.createRoot(...arguments);
                const mount = root.mount;
                root.mount = (target, options) => {
                    const result = mount(target, options);
                    if (target.dataset.embedded === "labeledCounter") {
                        const fiber = root.node.fiber;
                        const fiberComplete = fiber.complete;
                        fiber.complete = function () {
                            expect.step("html prop suppression");
                            asyncControl.resolve();
                            fiberComplete.call(this);
                        };
                    }
                    return result;
                };
                return root;
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
            `<p><span data-embedded="labeledCounter">
                <span data-prop-name="label">Counter</span>
            </span>[]a</p>`,
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
                <p>
                    <span data-embedded="labeledCounter" data-oe-protected="true" contenteditable="false">
                        <span class="counter">
                            <span>
                                <span data-prop-name="label" data-oe-protected="false" contenteditable="true">Counter</span>
                            </span>
                            :0
                        </span>
                    </span>
                    []a
                </p>
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
    test("Mount a component with a plugin that modifies the Component's env", async () => {
        let setSelection;
        class SimplePlugin extends Plugin {
            static id = "simple";
            static dependencies = ["selection", "embeddedComponents", "dom", "history"];
            resources = {
                mount_component_handlers: this.setupNewComponent.bind(this),
            };

            setupNewComponent({ name, env }) {
                if (name === "embeddedCounter") {
                    Object.assign(env, {
                        ...this.dependencies.selection,
                    });
                }
            }

            insertElement(element) {
                const html = parseHTML(this.document, element);
                this.dependencies.dom.insert(html);
                this.dependencies.history.addStep();
            }
        }

        class EmbeddedCounter extends Counter {
            static template = xml`
                <span class="counter" t-on-click="increment">
                    <t t-esc="state.value"/>
                </span>
            `;
            setup() {
                super.setup();
                setSelection = this.env.setSelection;
            }
        }
        const config = getConfig([embedding("embeddedCounter", EmbeddedCounter)]);
        config.Plugins.push(SimplePlugin);
        const { plugins } = await setupEditor(`<p>[]a</p>`, { config });
        const simplePlugin = plugins.get("simple");
        simplePlugin.insertElement("<div data-embedded='embeddedCounter'/>");
        await animationFrame();
        expect(setSelection).toBe(simplePlugin.dependencies.selection.setSelection);
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
        await expectElementCount(".o-we-toolbar", 1);
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
        await expectElementCount(".o-we-toolbar", 0);
    });

    test("should remove embedded elements children during clean for save (on a clone)", async () => {
        const { el, editor } = await setupEditor(
            '<div><p>a</p></div><div data-embedded="counter"><p>a</p></div>',
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        const clone = el.cloneNode(true);
        dispatchCleanForSave(editor, { root: clone });
        expect(getContent(clone)).toBe(`<div><p>a</p></div><div data-embedded="counter"></div>`);
    });

    test("should not remove embedded elements children during clean (not a clone)", async () => {
        const { el, editor } = await setupEditor(
            '<div><p>a</p></div><div data-embedded="counter"><p>a</p></div>',
            {
                config: getConfig([embedding("counter", Counter)]),
            }
        );
        dispatchClean(editor);
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
        const node = historyPlugin._unserializeNode(historyPlugin.serializeNode(el))[0];
        expect(getContent(node, { sortAttrs: true })).toBe(
            `<div><p>a</p></div><div contenteditable="false" data-embedded="counter" data-oe-protected="true"></div>`
        );
    });

    test("Ignore unknown data-embedded types for cleanforsave", async () => {
        const { editor, el } = await setupEditor(
            `<div data-embedded="unknown"><p>UNKNOWN</p></div>`,
            { config: getConfig([]) }
        );
        dispatchCleanForSave(editor, { root: el });
        expect(getContent(el)).toBe(`<div data-embedded="unknown"><p>UNKNOWN</p></div>`);
    });

    test("Ignore unknown data-embedded types for serialization", async () => {
        const { el, plugins } = await setupEditor(
            `<div data-embedded="unknown"><p>UNKNOWN</p></div>`,
            { config: getConfig([]) }
        );
        const historyPlugin = plugins.get("history");
        const node = historyPlugin._unserializeNode(historyPlugin.serializeNode(el))[0];
        expect(getContent(node)).toBe(`<div data-embedded="unknown"><p>UNKNOWN</p></div>`);
    });

    test("Don't remove empty inline-block data-embedded elements during initElementForEdition, but wrap them in div instead", async () => {
        const { el } = await setupEditor(
            `<div data-embedded="counter" style="display:inline-block;"></div>`,
            { config: getConfig([embedding("counter", Counter)]) }
        );
        expect(getContent(el, { sortAttrs: true })).toBe(
            `<div><div contenteditable="false" data-embedded="counter" data-oe-protected="true" style="display:inline-block;"><span class="counter">Counter:0</span></div></div>`
        );
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
                    embedding("wrapper", EmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
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

    test("embedded components in editable descendants do not generate ghost mutations when they are destroyed", async () => {
        const SimpleEmbeddedWrapper = EmbeddedWrapperMixin("deep");
        const { el, editor, plugins } = await setupEditor(unformat(`<p>[]after</p>`), {
            config: getConfig([
                embedding("wrapper", SimpleEmbeddedWrapper, (host) => ({ host }), {
                    getEditableDescendants,
                }),
            ]),
        });
        editor.shared.dom.insert(
            parseHTML(
                editor.document,
                unformat(`
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <div data-embedded="wrapper">
                                <div data-embedded-editable="deep">
                                    <p>deep</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `)
            )
        );
        addStep(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            unformat(`
                <div data-embedded="wrapper" data-oe-protected="true" contenteditable="false">
                    <div class="deep">
                        <div data-embedded-editable="deep" data-oe-protected="false" contenteditable="true">
                            <div data-embedded="wrapper" data-oe-protected="true" contenteditable="false">
                                <div class="deep">
                                    <div data-embedded-editable="deep" data-oe-protected="false" contenteditable="true">
                                        <p>deep</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <p>[]after</p>
            `)
        );
        undo(editor);
        await animationFrame();
        expect(getContent(el)).toBe(`<p>[]after</p>`);
        expect(plugins.get("history").currentStep.mutations.length).toBe(0);
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
                    embedding("wrapper", EmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
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
        editor.shared.history.addStep();
        const historyPlugin = plugins.get("history");
        const historySteps = editor.shared.history.getHistorySteps();
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
                    embedding("wrapper", EmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
                ]),
            }
        );
        const clone = el.cloneNode(true);
        dispatchCleanForSave(editor, { root: clone });
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
                    embedding("wrapper", EmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
                ]),
            }
        );
        const historyPlugin = plugins.get("history");
        const node = historyPlugin._unserializeNode(historyPlugin.serializeNode(el))[0];
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
                    embedding("simpleWrapper", SimpleEmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
                    embedding("wrapper", EmbeddedWrapper, (host) => ({ host }), {
                        getEditableDescendants,
                    }),
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

describe("Embedded state", () => {
    beforeEach(() => {
        let id = 1;
        patchWithCleanup(StateChangeManager.prototype, {
            generateId: () => id++,
        });
    });

    test("Write on the embedded state should re-render the component, write on `data-embedded-state` and write on `data-embedded-props`", async () => {
        let counter;
        patchWithCleanup(OffsetCounter.prototype, {
            setup() {
                super.setup();
                counter = this;
            },
        });
        const { el } = await setupEditor(
            `<p><span data-embedded="counter" data-embedded-props='{"baseValue":0}'></span></p>`,
            { config: getConfig([offsetCounter]) }
        );
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"baseValue":0}' data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></p>`
        );

        counter.embeddedState.baseValue = 2;
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"baseValue":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{"baseValue":0},"next":{"baseValue":2}}'><span class="counter">Counter:2</span></span></p>`
        );

        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"baseValue":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{"baseValue":0},"next":{"baseValue":2}}'><span class="counter">Counter:3</span></span></p>`
        );
        expect(counter.embeddedState).toEqual({
            baseValue: 2,
        });
        expect(counter.state).toEqual({
            value: 1,
        });
    });

    test("Adding a new property in the embedded state should re-render and write on embedded attributes", async () => {
        let counter;
        patchWithCleanup(SavedCounter.prototype, {
            setup() {
                super.setup();
                counter = this;
            },
        });
        const { el, editor } = await setupEditor(`<p><span data-embedded="counter"></span></p>`, {
            config: getConfig([savedCounter]),
        });
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{},"next":{"value":1}}' data-embedded-props='{"value":1}'><span class="counter">Counter:1</span></span></p>`
        );
        expect(counter.embeddedState).toEqual({
            value: 1,
        });
        // `data-embedded-state` should be removed from editor.getElContent result
        expect(getContent(editor.getElContent())).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`
        );
    });

    test("Removing an existing property in the embedded state should re-render and write on embedded attributes", async () => {
        let counter;
        patchWithCleanup(SavedCounter.prototype, {
            setup() {
                super.setup();
                counter = this;
            },
        });
        const { el, editor } = await setupEditor(
            `<p><span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
            { config: getConfig([savedCounter]) }
        );
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span></p>`
        );
        delete counter.embeddedState.value;
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props="{}" data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{}}'><span class="counter">Counter:0</span></span></p>`
        );
        expect(counter.embeddedState).toEqual({});
        // `data-embedded-state` should be removed from editor.getElContent result
        expect(getContent(editor.getElContent())).toBe(
            `<p><span data-embedded="counter" data-embedded-props="{}"></span></p>`
        );
    });

    test("Removing a non-existing property in the embedded state should do nothing", async () => {
        let counter;
        patchWithCleanup(SavedCounter.prototype, {
            setup() {
                super.setup();
                counter = this;
            },
        });
        const { el } = await setupEditor(
            `<p><span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
            { config: getConfig([savedCounter]) }
        );
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span></p>`
        );
        delete counter.embeddedState.notValue;
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span></p>`
        );
        expect(counter.embeddedState).toEqual({
            value: 1,
        });
    });

    test("Write on `data-embedded-state` should write on the state, re-render the component and write on `data-embedded-props` and the embedded state", async () => {
        let counter;
        patchWithCleanup(OffsetCounter.prototype, {
            setup() {
                super.setup();
                counter = this;
            },
        });
        const { editor, el } = await setupEditor(
            `<p><span data-embedded="counter" data-embedded-props='{"baseValue":0}'></span></p>`,
            { config: getConfig([offsetCounter]) }
        );
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"baseValue":0}' data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></p>`
        );

        counter.props.host.dataset.embeddedState = JSON.stringify({
            stateChangeId: -1,
            previous: {
                baseValue: 1,
            },
            next: {
                baseValue: 5,
            },
        });
        editor.shared.history.addStep();
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"baseValue":4}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":-1,"previous":{"baseValue":1},"next":{"baseValue":5}}'><span class="counter">Counter:4</span></span></p>`
        );
        expect(counter.embeddedState).toEqual({
            baseValue: 4,
        });

        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-embedded-props='{"baseValue":4}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":-1,"previous":{"baseValue":1},"next":{"baseValue":5}}'><span class="counter">Counter:5</span></span></p>`
        );
        expect(counter.embeddedState).toEqual({
            baseValue: 4,
        });
        expect(counter.state).toEqual({
            value: 1,
        });
    });

    test("Re-write the same value on `data-embedded-state` does not update the embedded state", async () => {
        let counter;
        patchWithCleanup(SavedCounter.prototype, {
            setup() {
                super.setup();
                counter = this;
                onPatched(() => {
                    expect.step("patched");
                });
            },
        });
        const { el } = await setupEditor(`<p><span data-embedded="counter"></span></p>`, {
            config: getConfig([savedCounter]),
        });
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{},"next":{"value":1}}' data-embedded-props='{"value":1}'><span class="counter">Counter:1</span></span></p>`
        );
        expect.verifySteps(["patched"]);
        counter.props.host.dataset.embeddedState = JSON.stringify({
            stateChangeId: 1,
            previous: {},
            next: {
                value: 1,
            },
        });
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{},"next":{"value":1}}' data-embedded-props='{"value":1}'><span class="counter">Counter:1</span></span></p>`
        );
        expect.verifySteps([]);
    });

    test("Re-write the same value on the embedded state does not write on `data-embedded-state`", async () => {
        let counter;
        patchWithCleanup(SavedCounter.prototype, {
            setup() {
                super.setup();
                counter = this;
                onPatched(() => {
                    expect.step("patched");
                });
            },
        });
        const { el } = await setupEditor(`<p><span data-embedded="counter"></span></p>`, {
            config: getConfig([savedCounter]),
        });
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false"><span class="counter">Counter:0</span></span></p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{},"next":{"value":1}}' data-embedded-props='{"value":1}'><span class="counter">Counter:1</span></span></p>`
        );
        expect.verifySteps(["patched"]);
        counter.embeddedState.value = 1;
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p><span data-embedded="counter" data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{},"next":{"value":1}}' data-embedded-props='{"value":1}'><span class="counter">Counter:1</span></span></p>`
        );
        expect.verifySteps([]);
    });

    test("Embedded state evolves during undo and redo", async () => {
        const { el, editor } = await setupEditor(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
            { config: getConfig([savedCounter]) }
        );
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span></p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":2}}'><span class="counter">Counter:2</span></span></p>`
        );
        undo(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":2,"previous":{"value":2},"next":{"value":1}}'><span class="counter">Counter:1</span></span></p>`
        );
        redo(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":3,"previous":{"value":1},"next":{"value":2}}'><span class="counter">Counter:2</span></span></p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":3}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":4,"previous":{"value":2},"next":{"value":3}}'><span class="counter">Counter:3</span></span></p>`
        );
        undo(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":5,"previous":{"value":3},"next":{"value":2}}'><span class="counter">Counter:2</span></span></p>`
        );
        redo(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":3}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":6,"previous":{"value":2},"next":{"value":3}}'><span class="counter">Counter:3</span></span></p>`
        );
    });

    test("Embedded state evolves during the restoration of a savePoint after makeSavePoint, even if the component was destroyed", async () => {
        const { el, editor } = await setupEditor(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
            { config: getConfig([savedCounter]) }
        );
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span></p>`
        );
        const savepoint1 = editor.shared.history.makeSavePoint();
        await click(".counter");
        await animationFrame();
        const savepoint2 = editor.shared.history.makeSavePoint();
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":3}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":2,"previous":{"value":2},"next":{"value":3}}'><span class="counter">Counter:3</span></span></p>`
        );
        deleteForward(editor);
        expect(getContent(el)).toBe(`<p>a[]</p>`);
        savepoint2();
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":3,"previous":{"value":3},"next":{"value":2}}'><span class="counter">Counter:2</span></span></p>`
        );
        savepoint1();
        await animationFrame();
        // stateChangeId evolved from 3 to 6, since it reverted the last 3
        // state changes.
        // 2 -> 3, revert mutations created by savepoint2.
        // 3 -> 2, revert mutations of the second click.
        // 2 -> 1, revert mutations of the first click.
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":6,"previous":{"value":2},"next":{"value":1}}'><span class="counter">Counter:1</span></span></p>`
        );
    });

    test("Embedded state changes are discarded if the component is destroyed before they are applied", async () => {
        const { el, editor } = await setupEditor(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":1}'></span></p>`,
            { config: getConfig([savedCounter]) }
        );
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":1}' data-oe-protected="true" contenteditable="false"><span class="counter">Counter:1</span></span></p>`
        );
        await click(".counter");
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":2}}'><span class="counter">Counter:2</span></span></p>`
        );
        // Launch click sequence without awaiting it
        click(queryFirst(".counter"));
        deleteForward(editor);
        expect(getContent(el)).toBe(`<p>a[]</p>`);
        undo(editor);
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"value":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{"value":1},"next":{"value":2}}'><span class="counter">Counter:2</span></span></p>`
        );
    });

    test("Embedded state and embedded props can be different, if specified in the config of the stateChangeManager", async () => {
        let counter;
        patchWithCleanup(NamedCounter.prototype, {
            setup() {
                super.setup();
                counter = this;
            },
        });
        const { el, editor } = await setupEditor(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"name":"customName","value":1}'></span></p>`,
            { config: getConfig([namedCounter]) }
        );
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"name":"customName","value":1}' data-oe-protected="true" contenteditable="false"><span class="counter">customName:4</span></span></p>`
        );
        // Only consider props supposed to be extracted from `data-embedded-props`
        const props = {
            name: counter.props.name,
            value: counter.props.value,
        };
        expect(props).toEqual({
            name: "customName",
            value: 1,
        });
        expect(counter.embeddedState).toEqual({
            baseValue: 3, // defined in the embedding (namedCounter)
            value: 1, // recovered from the props
        });
        counter.embeddedState.baseValue = 5;
        counter.embeddedState.value = 2;
        await animationFrame();
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"name":"customName","value":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{"baseValue":3,"value":1},"next":{"baseValue":5,"value":2}}'><span class="counter">customName:7</span></span></p>`
        );
        deleteForward(editor);
        undo(editor);
        await animationFrame();
        // Check that the base value was correctly reset after the destruction
        expect(counter.embeddedState).toEqual({
            baseValue: 3, // defined in the embedding (namedCounter)
            value: 2, // recovered from the props
        });
        expect(getContent(el)).toBe(
            `<p>a[]<span data-embedded="counter" data-embedded-props='{"name":"customName","value":2}' data-oe-protected="true" contenteditable="false" data-embedded-state='{"stateChangeId":1,"previous":{"baseValue":3,"value":1},"next":{"baseValue":5,"value":2}}'><span class="counter">customName:5</span></span></p>`
        );
    });
});
