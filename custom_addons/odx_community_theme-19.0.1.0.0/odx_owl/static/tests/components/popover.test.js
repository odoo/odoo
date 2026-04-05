/** @odoo-module **/

import { expect, queryOne, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { click } from "@odoo/hoot-dom";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import {
    Popover,
    PopoverClose,
    PopoverContent,
    PopoverTrigger,
} from "@odx_owl/components/popover/popover";

test("popover trigger opens the panel and popover close dismisses it", async () => {
    class Parent extends Component {
        static components = {
            Popover,
            PopoverClose,
            PopoverContent,
            PopoverTrigger,
        };
        static template = xml`
            <Popover>
                <t t-set-slot="trigger">
                    <PopoverTrigger>
                        <button class="popover-test-trigger" type="button">Open</button>
                    </PopoverTrigger>
                </t>
                <t t-set-slot="content">
                    <PopoverContent>
                        <div class="popover-test-body">Panel</div>
                        <PopoverClose className="'popover-test-close'">Close</PopoverClose>
                    </PopoverContent>
                </t>
            </Popover>
        `;
    }

    await mountWithCleanup(Parent);

    expect(`.odx-popover__panel`).toHaveCount(0);

    await contains(`.popover-test-trigger`).click();
    await animationFrame();

    expect(document.body.querySelectorAll(`.odx-popover__panel`).length).toBe(1);
    expect(document.body.querySelector(`.odx-popover__panel`)?.textContent).toBe("PanelClose");

    await click(queryOne(`.popover-test-close`, { root: document.body }));
    await animationFrame();

    expect(document.body.querySelectorAll(`.odx-popover__panel`).length).toBe(0);
});
