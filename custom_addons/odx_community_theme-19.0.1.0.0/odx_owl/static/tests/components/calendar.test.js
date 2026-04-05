/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Calendar } from "@odx_owl/components/calendar/calendar";

test("rtl calendar reverses left and right arrow day navigation", async () => {
    class Parent extends Component {
        static components = { Calendar };
        static template = xml`
            <Calendar
                autoFocus="true"
                defaultMonth="referenceDate"
                defaultValue="referenceDate"
                dir="'rtl'"
            />
        `;

        get referenceDate() {
            return new Date(2026, 2, 15);
        }
    }

    await mountWithCleanup(Parent);
    await animationFrame();

    expect(`.odx-calendar__day[tabindex="0"]`).toHaveText("15");

    await contains(`.odx-calendar__day[tabindex="0"]`).press("ArrowLeft");
    await animationFrame();

    expect(`.odx-calendar__day[tabindex="0"]`).toHaveText("16");
});
