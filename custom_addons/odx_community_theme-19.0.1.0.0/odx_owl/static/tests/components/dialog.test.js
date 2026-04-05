/** @odoo-module **/

import { expect, queryOne, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { click } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Dialog } from "@odx_owl/components/dialog/dialog";

test("dialog closes on escape by default", async () => {
    class Parent extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog
                defaultOpen="true"
                onOpenChange="onOpenChange"
                title="'Dialog title'"
            >
                Body
            </Dialog>
        `;

        onOpenChange(open) {
            expect.step(String(open));
        }
    }

    await mountWithCleanup(Parent);
    await animationFrame();

    expect(document.body.querySelectorAll(`.odx-dialog__portal`).length).toBe(1);

    await press("escape");
    await animationFrame();

    expect.verifySteps(["false"]);
    expect(document.body.querySelectorAll(`.odx-dialog__portal`).length).toBe(0);
});

test("dialog escape dismissal can be prevented", async () => {
    class Parent extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog
                defaultOpen="true"
                onEscapeKeyDown="onEscapeKeyDown"
                title="'Dialog title'"
            >
                Body
            </Dialog>
        `;

        onEscapeKeyDown(ev) {
            expect.step("escape");
            ev.preventDefault();
        }
    }

    await mountWithCleanup(Parent);
    await animationFrame();

    await press("escape");
    await animationFrame();

    expect.verifySteps(["escape"]);
    expect(document.body.querySelectorAll(`.odx-dialog__portal`).length).toBe(1);
});

test("dialog outside pointer dismissal can be prevented before overlay click closes", async () => {
    class Parent extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog
                defaultOpen="true"
                onPointerDownOutside="onPointerDownOutside"
                title="'Dialog title'"
            >
                Body
            </Dialog>
        `;

        onPointerDownOutside(ev) {
            expect.step("pointerdown-outside");
            ev.preventDefault();
        }
    }

    await mountWithCleanup(Parent);
    await animationFrame();

    await click(queryOne(`.odx-dialog__overlay`, { root: document.body }));
    await animationFrame();

    expect.verifySteps(["pointerdown-outside"]);
    expect(document.body.querySelectorAll(`.odx-dialog__portal`).length).toBe(1);
});
