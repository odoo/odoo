// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { drag, queryOne, queryRect, resize } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, reactive, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ResizablePanel } from "@web/components/resizable_panel/resizable_panel";

describe.current.tags("desktop");

test("Width cannot exceed viewport width", async () => {
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <ResizablePanel>
                <p>A</p>
                <p>Cool</p>
                <p>Paragraph</p>
            </ResizablePanel>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect(".o_resizable_panel").toHaveCount(1);
    expect(".o_resizable_panel_handle").toHaveCount(1);

    const vw = window.innerWidth;
    queryOne(".o_resizable_panel").style.width = `${vw + 100}px`;

    expect(queryRect(".o_resizable_panel").width).toBeWithin(vw * 0.95, vw);
});

test("handles right-to-left", async () => {
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div class="d-flex parent-el" style="direction: rtl;">
                <div style="width: 50px;" />
                <ResizablePanel minWidth="20" initialWidth="30">
                    <div style="width: 10px;" class="text-break">
                        A cool paragraph
                    </div>
                </ResizablePanel>
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect(".o_resizable_panel").toHaveRect({ width: 30 });
    await (
        await drag(".o_resizable_panel_handle")
    ).drop(".o_resizable_panel_handle", {
        position: {
            x: 10,
        },
    });

    expect(queryRect(".o_resizable_panel").width).toBeGreaterThan(
        queryOne(".parent-el").offsetWidth - 10 - 50,
    );
});

test("handles resize handle at start in fixed position", async () => {
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div class="d-flex parent-el">
                <ResizablePanel minWidth="20" initialWidth="30" handleSide="'start'" class="'position-fixed'">
                    <div style="width: 10px;" class="text-break">
                        A cool paragraph
                    </div>
                </ResizablePanel>
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    const resizablePanelEl = queryOne(".o_resizable_panel");
    resizablePanelEl.style.setProperty("right", "100px");
    expect(resizablePanelEl).toHaveRect({ width: 30 });

    await (
        await drag(".o_resizable_panel_handle")
    ).drop(".o_resizable_panel_handle", {
        position: {
            x: window.innerWidth - 200,
        },
    });
    const panelExpectedWidth = 100 + queryRect(".o_resizable_panel_handle").width / 2;
    expect(queryRect(resizablePanelEl).width).toBeWithin(
        panelExpectedWidth,
        panelExpectedWidth + 1,
    );
});

test("resizing the window adapts the panel", async () => {
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div style="width: 400px;" class="parent-el position-relative">
                <ResizablePanel>
                    <p>A</p>
                    <p>Cool</p>
                    <p>Paragraph</p>
                </ResizablePanel>
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    await (
        await drag(".o_resizable_panel_handle")
    ).drop(".o_resizable_panel_handle", {
        position: {
            x: 99999,
        },
    });

    expect(queryOne(".o_resizable_panel").offsetWidth).toBe(398);
    queryOne(".parent-el").style.width = "200px";
    await resize();
    expect(queryOne(".o_resizable_panel").offsetWidth).toBe(198);
});

test("minWidth props can be updated", async () => {
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div class="d-flex">
                <ResizablePanel minWidth="props.state.minWidth">
                    <div style="width: 10px;" class="text-break">
                        A cool paragraph
                    </div>
                </ResizablePanel>
            </div>
        `;
        static props = ["*"];
    }
    const state = reactive({ minWidth: 20 });
    await mountWithCleanup(Parent, {
        props: { state },
    });
    await (
        await drag(".o_resizable_panel_handle")
    ).drop(".o_resizable_panel_handle", {
        position: {
            x: 15,
        },
    });

    expect(".o_resizable_panel").toHaveRect({ width: 20 });
    state.minWidth = 40;
    await animationFrame();
    await (
        await drag(".o_resizable_panel_handle")
    ).drop(".o_resizable_panel_handle", {
        position: {
            x: 15,
        },
    });
    expect(".o_resizable_panel").toHaveRect({ width: 40 });
});

test("a window resize with a detached container does not throw", async () => {
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`<ResizablePanel><p>x</p></ResizablePanel>`;
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    queryOne(".o_resizable_panel").remove();
    await resize({ width: 500 });
    await animationFrame();
    expect(".o_resizable_panel").toHaveCount(0);
});

test("a raised minWidth widens the panel already in place", async () => {
    const state = reactive({ minWidth: 200 });
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div style="width: 1000px;">
                <ResizablePanel minWidth="state.minWidth" initialWidth="300">
                    <p>body</p>
                </ResizablePanel>
            </div>`;
        static props = ["*"];
        setup() {
            this.state = useState(state);
        }
    }
    await mountWithCleanup(Parent);
    await animationFrame();
    expect(queryOne(".o_resizable_panel").style.width).toBe("300px");

    state.minWidth = 600;
    await animationFrame();
    expect(queryOne(".o_resizable_panel").style.width).toBe("600px");
});

test("a changed initialWidth is applied after mount", async () => {
    const state = reactive({ width: 400 });
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div style="width: 1000px;">
                <ResizablePanel minWidth="60" initialWidth="state.width">
                    <p>body</p>
                </ResizablePanel>
            </div>`;
        static props = ["*"];
        setup() {
            this.state = useState(state);
        }
    }
    await mountWithCleanup(Parent);
    await animationFrame();
    expect(queryOne(".o_resizable_panel").style.width).toBe("400px");

    state.width = 68;
    await animationFrame();
    expect(queryOne(".o_resizable_panel").style.width).toBe("68px");
});

test("a props update that changes no size does not notify onResize", async () => {
    const state = reactive({ label: "a" });
    let resizeCalls = 0;
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div style="width: 1000px;">
                <ResizablePanel minWidth="60" initialWidth="300" onResize="onResize">
                    <p t-esc="state.label"/>
                </ResizablePanel>
            </div>`;
        static props = ["*"];
        setup() {
            this.state = useState(state);
            this.onResize = () => resizeCalls++;
        }
    }
    await mountWithCleanup(Parent);
    await animationFrame();
    const afterMount = resizeCalls;

    state.label = "b";
    await animationFrame();
    state.label = "c";
    await animationFrame();
    expect(resizeCalls).toBe(afterMount);
});

test("the available width wins when it is below minWidth", async () => {
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div style="width: 200px;" class="parent-el position-relative">
                <ResizablePanel minWidth="400" initialWidth="500">
                    <div style="width: 10px;" class="text-break">A cool paragraph</div>
                </ResizablePanel>
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Parent);
    expect(queryOne(".o_resizable_panel").offsetWidth).toBe(198);
});

test("a replaced onResize prop is the one notified", async () => {
    const state = reactive({ target: "first" });
    /** @type {string[]} */
    const calls = [];
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div style="width: 1000px;">
                <ResizablePanel minWidth="60" initialWidth="300" onResize="onResize">
                    <p>body</p>
                </ResizablePanel>
            </div>`;
        static props = ["*"];
        setup() {
            this.state = useState(state);
        }
        get onResize() {
            const target = this.state.target;
            return () => calls.push(target);
        }
    }
    await mountWithCleanup(Parent);
    await animationFrame();
    state.target = "second";
    await animationFrame();
    calls.length = 0;

    await (
        await drag(".o_resizable_panel_handle")
    ).drop(".o_resizable_panel_handle", { position: { x: 40 } });
    await animationFrame();
    expect(calls.length).toBeGreaterThan(0);
    expect(calls.every((target) => target === "second")).toBe(true);
});

test("a drag measures the panel once, at pointerdown, and only writes on each move", async () => {
    class Parent extends Component {
        static components = { ResizablePanel };
        static template = xml`
            <div style="width: 1000px;">
                <ResizablePanel minWidth="60" initialWidth="300">
                    <p>body</p>
                </ResizablePanel>
            </div>`;
        static props = ["*"];
    }
    await mountWithCleanup(Parent);
    await animationFrame();
    const panel = queryOne(".o_resizable_panel");
    let rectReads = 0;
    const { getBoundingClientRect } = panel;
    patchWithCleanup(panel, {
        getBoundingClientRect() {
            rectReads++;
            return getBoundingClientRect.call(this);
        },
    });
    const dragHelper = await drag(".o_resizable_panel_handle");
    const readsAtStart = rectReads;
    expect(readsAtStart).toBeGreaterThan(0);
    for (const x of [320, 340, 360, 380, 400]) {
        await dragHelper.moveTo(".o_resizable_panel_handle", { position: { x } });
    }
    expect(rectReads).toBe(readsAtStart);
    await dragHelper.drop();
    expect(panel.style.width).not.toBe("300px");
});

test("resizing ignores secondary buttons and unrelated pointers", async () => {
    await mountWithCleanup(ResizablePanel, {
        props: { minWidth: 20, initialWidth: 100, slots: {} },
    });
    const panel = queryOne(".o_resizable_panel");
    const handle = queryOne(".o_resizable_panel_handle");
    handle.dispatchEvent(new PointerEvent("pointerdown", { button: 2, pointerId: 7 }));
    expect(document.body).not.toHaveClass("pe-none");
    document.dispatchEvent(new PointerEvent("pointerup", { pointerId: 7 }));
    handle.dispatchEvent(new PointerEvent("pointerdown", { pointerId: 7 }));
    document.dispatchEvent(
        new PointerEvent("pointermove", { pointerId: 8, clientX: 250 }),
    );
    expect(panel.style.width).toBe("100px");
    document.dispatchEvent(new PointerEvent("pointerup", { pointerId: 8 }));
    expect(document.body).toHaveClass("pe-none");
    document.dispatchEvent(new PointerEvent("pointercancel", { pointerId: 7 }));
    expect(document.body).not.toHaveClass("pe-none");
});
