/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Calendar } from "@odx_owl/components/calendar/calendar";

test("range calendar emits ordered hidden inputs and middle-day state", async () => {
    class Parent extends Component {
        static components = { Calendar };
        static template = xml`
            <Calendar
                defaultMonth="referenceDate"
                id="'range-calendar'"
                mode="'range'"
                name="'travel'"
            />
        `;

        get referenceDate() {
            return new Date(2026, 2, 1);
        }
    }

    await mountWithCleanup(Parent);

    await contains(`#range-calendar-day-2026-03-14`).click();
    await contains(`#range-calendar-day-2026-03-10`).click();

    expect(document.querySelector(`input[type="hidden"][name="travel[from]"]`)?.value).toBe("2026-03-10");
    expect(document.querySelector(`input[type="hidden"][name="travel[to]"]`)?.value).toBe("2026-03-14");
    expect(`#range-calendar-day-2026-03-10`).toHaveClass("odx-calendar__day--range-start");
    expect(`#range-calendar-day-2026-03-12`).toHaveClass("odx-calendar__day--range-middle");
    expect(`#range-calendar-day-2026-03-14`).toHaveClass("odx-calendar__day--range-end");
});
