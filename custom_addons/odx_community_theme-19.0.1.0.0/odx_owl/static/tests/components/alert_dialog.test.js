/** @odoo-module **/

import { expect, queryOne, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { click } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { AlertDialog } from "@odx_owl/components/alert_dialog/alert_dialog";

test("alert dialog ignores overlay clicks", async () => {
    class Parent extends Component {
        static components = { AlertDialog };
        static template = xml`
            <AlertDialog defaultOpen="true" title="'Delete record'">
                Body
            </AlertDialog>
        `;
    }

    await mountWithCleanup(Parent);
    await animationFrame();

    await click(queryOne(`.odx-alert-dialog__overlay`, { root: document.body }));
    await animationFrame();

    expect(document.body.querySelectorAll(`.odx-dialog__portal`).length).toBe(1);
});

test("alert dialog confirm can block close by returning false", async () => {
    class Parent extends Component {
        static components = { AlertDialog };
        static template = xml`
            <AlertDialog
                defaultOpen="true"
                onConfirm="onConfirm"
                title="'Delete record'"
            >
                Body
            </AlertDialog>
        `;

        onConfirm() {
            expect.step("confirm");
            return false;
        }
    }

    await mountWithCleanup(Parent);
    await animationFrame();

    await click(queryOne(`.odx-button--destructive`, { root: document.body }));
    await animationFrame();

    expect.verifySteps(["confirm"]);
    expect(document.body.querySelectorAll(`.odx-dialog__portal`).length).toBe(1);
});
