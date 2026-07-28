/** @odoo-module **/

import { Component, reactive, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    getFixture,
    patchWithCleanup,
    mount,
    nextTick,
    triggerEvents,
} from "@web/../tests/helpers/utils";

QUnit.module("Resizable Panel", ({ beforeEach }) => {
    let env;
    let target;

    beforeEach(async () => {
        env = await makeTestEnv();
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => Promise.resolve().then(fn),
        });
    });

    QUnit.test("Width cannot exceed viewport width", async (assert) => {
        class Parent extends Component {
            static components = { ResizablePanel };
            static template = xml`
                <ResizablePanel>
                    <p>A</p>
                    <p>Cool</p>
                    <p>Paragraph</p>
                </ResizablePanel>
            `;
        }

        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_resizable_panel");
        assert.containsOnce(target, ".o_resizable_panel_handle");

        const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
        const sidepanel = target.querySelector(".o_resizable_panel");
        sidepanel.style.width = `${vw + 100}px`;

        const sidepanelWidth = sidepanel.getBoundingClientRect().width;
        assert.ok(
            sidepanelWidth <= vw && sidepanelWidth > vw * 0.95,
            "The sidepanel should be smaller or equal to the view width"
        );
    });

    QUnit.test("handles right-to-left", async (assert) => {
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
        }
        await mount(Parent, target, { env });
        const parentEl = target.querySelector(".parent-el");
        const resizablePanelEl = target.querySelector(".o_resizable_panel");
        let resizablePabelRect = resizablePanelEl.getBoundingClientRect();
        assert.strictEqual(resizablePabelRect.width, 30);

        const handle = resizablePanelEl.querySelector(".o_resizable_panel_handle");
        await triggerEvents(handle, null, ["mousedown", ["mousemove", { clientX: 10 }], "mouseup"]);
        resizablePabelRect = resizablePanelEl.getBoundingClientRect();
        assert.ok(resizablePabelRect.width > parentEl.offsetWidth - 10 - 50);
    });

    QUnit.test("handles resize handle at start in fixed position", async (assert) => {
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
        }
        await mount(Parent, target, { env });
        const resizablePanelEl = target.querySelector(".o_resizable_panel");
        resizablePanelEl.style.setProperty("right", "100px");
        let resizablePabelRect = resizablePanelEl.getBoundingClientRect();
        assert.strictEqual(resizablePabelRect.width, 30);

        const handle = resizablePanelEl.querySelector(".o_resizable_panel_handle");
        await triggerEvents(handle, null, [
            "mousedown",
            ["mousemove", { clientX: window.innerWidth - 200 }],
            "mouseup",
        ]);
        resizablePabelRect = resizablePanelEl.getBoundingClientRect();
        assert.strictEqual(resizablePabelRect.width, 100 + handle.offsetWidth / 2);
    });

    QUnit.test("resizing the window adapts the panel", async (assert) => {
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
        }
        await mount(Parent, target, { env });
        const resizablePanelEl = target.querySelector(".o_resizable_panel");
        const handle = resizablePanelEl.querySelector(".o_resizable_panel_handle");
        await triggerEvents(handle, null, [
            "mousedown",
            ["mousemove", { clientX: 99999 }],
            "mouseup",
        ]);
        assert.strictEqual(resizablePanelEl.offsetWidth, 398);
        target.querySelector(".parent-el").style.setProperty("width", "200px");
        window.dispatchEvent(new Event("resize"));
        await nextTick();
        assert.strictEqual(resizablePanelEl.offsetWidth, 198);
    });

    QUnit.test("minWidth props can be updated", async (assert) => {
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
        }
        const state = reactive({ minWidth: 20 });
        await mount(Parent, target, { env, props: { state } });
        const resizablePanelEl = target.querySelector(".o_resizable_panel");
        const handle = resizablePanelEl.querySelector(".o_resizable_panel_handle");
        await triggerEvents(handle, null, ["mousedown", ["mousemove", { clientX: 15 }], "mouseup"]);

        assert.strictEqual(resizablePanelEl.getBoundingClientRect().width, 20);
        state.minWidth = 40;
        await nextTick();
        await triggerEvents(handle, null, ["mousedown", ["mousemove", { clientX: 15 }], "mouseup"]);
        assert.strictEqual(resizablePanelEl.getBoundingClientRect().width, 40);
    });
});
