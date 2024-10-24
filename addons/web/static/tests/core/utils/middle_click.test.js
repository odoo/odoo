import { expect, test } from "@odoo/hoot";
import { keyDown } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { useMiddleClick } from "@web/core/utils/middle_click";

test("ctrl+click behavior on specified element", async () => {
    class MiddleClick extends Component {
        static props = ["*"];
        static template = xml`
            <div class="root">
                <h2>Wonderful Component</h2>
                <button t-ref="recordRef" class="btn btn-primary" t-on-click="onClick">Click me!</button>
            </div>
        `;

        setup() {
            useMiddleClick({
                clickParams: {
                    onCtrlClick: () => {
                        expect.step("ctrl+click");
                    },
                },
                refName: "recordRef",
            });
        }

        onClick() {
            expect.step("click");
        }
    }

    await mountWithCleanup(MiddleClick);

    expect.verifySteps([]);
    await contains(".btn").click();
    expect.verifySteps(["click"]);
    await keyDown("Control");
    expect(document.body).toHaveClass("ctrl_key_pressed");
    await contains(".btn").click();
    expect.verifySteps(["ctrl+click"]);
});
