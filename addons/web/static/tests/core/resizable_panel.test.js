import { describe, expect, test } from "@odoo/hoot";
import { drag, queryOne, queryRect, resize } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, reactive, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";

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
        queryOne(".parent-el").offsetWidth - 10 - 50
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
    expect(resizablePanelEl).toHaveRect({
        width: 100 + queryRect(".o_resizable_panel_handle").width / 2,
    });
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
