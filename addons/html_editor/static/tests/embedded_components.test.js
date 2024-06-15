import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { parseHTML } from "@html_editor/utils/html";
import { describe, expect, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import {
    App,
    Component,
    onMounted,
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
import { deleteBackward, undo } from "./_helpers/user_actions";
import { makeMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";

class Counter extends Component {
    static props = [];
    static template = xml`
        <span t-ref="root" class="counter" t-on-click="increment">Counter: <t t-esc="state.value"/></span>`;

    state = useState({ value: 0 });
    ref = useRef("root");

    increment() {
        this.state.value++;
    }
}

function getConfig(name, Comp, getProps) {
    const embedding = {
        name,
        Component: Comp,
    };
    if (getProps) {
        embedding.getProps = getProps;
    }

    return {
        Plugins: [...MAIN_PLUGINS, EmbeddedComponentPlugin],
        resources: {
            embeddedComponents: [embedding],
        },
    };
}

test("can mount a embedded component", async () => {
    const { el } = await setupEditor(`<div><span data-embedded="counter"></span></div>`, {
        config: getConfig("counter", Counter),
    });
    expect(getContent(el)).toBe(
        `<div><span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 0</span></span></div>`
    );
    click(".counter");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<div><span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 1</span></span></div>`
    );
});

test("can mount a embedded component from a step", async () => {
    const { el, editor } = await setupEditor(`<div>a[]b</div>`, {
        config: getConfig("counter", Counter),
    });
    expect(getContent(el)).toBe(`<div>a[]b</div>`);
    editor.shared.domInsert(parseHTML(editor.document, `<span data-embedded="counter"></span>`));
    editor.dispatch("ADD_STEP");
    expect(getContent(el)).toBe(
        `<div>a<span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"></span>[]b</div>`
    );
    await animationFrame();
    expect(getContent(el)).toBe(
        `<div>a<span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 0</span></span>[]b</div>`
    );
    click(".counter");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<div>a<span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 1</span></span>[]b</div>`
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
    const { el, editor } = await setupEditor(`<div><span data-embedded="counter"></span></div>`, {
        config: getConfig("counter", Test),
    });
    expect(steps).toEqual(["mounted"]);

    editor.destroy();
    expect(steps).toEqual(["mounted", "willunmount", "willdestroy"]);
    expect(getContent(el)).toBe(
        `<div><span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true"></span></div>`
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
        config: getConfig("counter", Test),
        env: Object.assign(rootEnv, { somevalue: 1 }),
    });
    expect(env.somevalue).toBe(1);
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
            config: getConfig("counter", Test),
        }
    );

    expect(getContent(el)).toBe(
        `<div>a<span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 0</span></span>[]</div>`
    );
    expect(steps).toEqual(["mounted"]);

    deleteBackward(editor);
    expect(steps).toEqual(["mounted", "willunmount"]);
    expect(getContent(el)).toBe(`<div>a[]</div>`);
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
    const { editor } = await setupEditor(`<div>a<span data-embedded="counter"></span>[]</div>`, {
        config: getConfig("counter", Test),
    });
    deleteBackward(editor);
    expect.verifySteps(["destroy from plugin", "willdestroy"]);
    editor.destroy();
    expect.verifySteps([]);
});

test("select content of a component shouldn't open the toolbar", async () => {
    const { el } = await setupEditor(`<div><p>[a]</p><span data-embedded="counter"></span></div>`, {
        config: getConfig("counter", Counter),
    });
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(1);
    expect(getContent(el)).toBe(
        `<div><p>[a]</p><span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 0</span></span></div>`
    );

    const node = queryFirst(".counter", {}).firstChild;
    setSelection({ anchorNode: node, anchorOffset: 1, focusNode: node, focusOffset: 3 });
    await tick();
    await animationFrame();
    expect(getContent(el)).toBe(
        `<div><p>a</p><span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">C[ou]nter: 0</span></span></div>`
    );
    expect(".o-we-toolbar").toHaveCount(0);
});

test("components delete can be undone", async () => {
    let steps = [];
    class Test extends Counter {
        setup() {
            onMounted(() => {
                steps.push("mounted");
                expect(this.ref.el.isConnected).toBe(true);
            });
            onWillUnmount(() => {
                console.trace();
                steps.push("willunmount");
                expect(this.ref.el?.isConnected).toBe(true);
            });
        }
    }
    const { el, editor } = await setupEditor(
        `<div>a<span data-embedded="counter"></span>[]</div>`,
        {
            config: getConfig("counter", Test),
        }
    );

    editor.dispatch("HISTORY_STAGE_SELECTION");

    expect(getContent(el)).toBe(
        `<div>a<span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 0</span></span>[]</div>`
    );
    expect(steps).toEqual(["mounted"]);

    deleteBackward(editor);
    expect(steps).toEqual(["mounted", "willunmount"]);
    expect(getContent(el)).toBe(`<div>a[]</div>`);

    // now, we undo and check that component still works
    steps = [];
    undo(editor);
    expect(getContent(el)).toBe(
        `<div>a<span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"></span>[]</div>`
    );
    await animationFrame();
    expect(steps).toEqual(["mounted"]);
    expect(getContent(el)).toBe(
        `<div>a<span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 0</span></span>[]</div>`
    );
    click(".counter");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<div>a<span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 1</span></span>[]</div>`
    );
});

test("element with data-embedded content is removed when component is mounting", async () => {
    const { el } = await setupEditor(`<div><span data-embedded="counter">hello</span></div>`, {
        config: getConfig("counter", Counter),
    });
    expect(getContent(el)).toBe(
        `<div><span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 0</span></span></div>`
    );
});

test("embedded component get proper props", async () => {
    class Test extends Counter {
        static props = ["initialCount"];
        setup() {
            expect(this.props.initialCount).toBe(10);
            this.state.value = this.props.initialCount;
        }
    }
    const { el } = await setupEditor(`<div><span data-embedded="counter"></span></div>`, {
        config: getConfig("counter", Test, () => ({ initialCount: 10 })),
    });

    expect(getContent(el)).toBe(
        `<div><span data-embedded="counter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 10</span></span></div>`
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
            config: getConfig("counter", Test, (host) => ({
                initialCount: parseInt(host.dataset.count),
            })),
        }
    );

    expect(getContent(el)).toBe(
        `<div><span data-embedded="counter" data-count="10" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 10</span></span></div>`
    );
});

test("embedded component can set attributes on element", async () => {
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
            config: getConfig("counter", Test, (host) => ({ host })),
        }
    );

    expect(getContent(el)).toBe(
        `<div><span data-embedded="counter" data-count="10" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 10</span></span></div>`
    );

    click(".counter");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<div><span data-embedded="counter" data-count="11" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false"><span class="counter">Counter: 11</span></span></div>`
    );
});

describe("embedded component Owl lifecycle editor integration", () => {
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
                config: getConfig("labeledCounter", LabeledCounter, (host) => ({
                    label: host.querySelector("[data-prop-name='label']"),
                })),
            }
        );
        expect.verifySteps(["willstart"]);
        delayedWillStart.resolve();
        await animationFrame();
        expect(getContent(el)).toBe(
            unformat(`
                <div>
                    <span data-embedded="labeledCounter" data-oe-protected="true" data-oe-transient-content="true" data-oe-has-removable-handler="true" contenteditable="false">
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
});
