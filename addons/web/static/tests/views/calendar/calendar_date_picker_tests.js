/** @odoo-module **/

import { CalendarDatePicker } from "@web/views/calendar/date_picker/calendar_date_picker";
import { click, patchDate } from "../../helpers/utils";
import { makeEnv, makeFakeModel, mountComponent } from "./calendar_helpers";

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarDatePicker, env, {
        model,
        ...props,
    });
}

QUnit.module("CalendarDatePicker", (hooks) => {
    hooks.beforeEach(async () => {
        patchDate(2021, 7, 14, 8, 0, 0);
    });
});

QUnit.skipWOWL("Mount a CalendarDatePicker", async (assert) => {
    const datePicker = await start({ model: { scale: "day" } });
    assert.containsOnce(datePicker.el, ".o-calendar-date-picker.hasDatepicker");
    assert.strictEqual(datePicker.el.querySelector(".o-selected-range").textContent, "16");
    assert.containsOnce(datePicker.el, `[data-month="6"][data-year="2021"] .o-selected-range`);
    assert.strictEqual(datePicker.el.querySelector(".ui-datepicker-month").textContent, "Jul");
    assert.strictEqual(datePicker.el.querySelector(".ui-datepicker-year").textContent, "2021");
    assert.strictEqual(datePicker.el.querySelector("thead").textContent, "SMTWTFS");
});

QUnit.skipWOWL("Scale: init with day", async (assert) => {
    const datePicker = await start({ model: { scale: "day" } });
    assert.containsOnce(datePicker.el, ".o-selected-range");
    assert.containsOnce(datePicker.el, "a.o-selected-range");
    assert.strictEqual(datePicker.el.querySelector(".o-selected-range").textContent, "16");
});

QUnit.skipWOWL("Scale: init with week", async (assert) => {
    const datePicker = await start({ model: { scale: "week" } });
    assert.containsOnce(datePicker.el, ".o-selected-range");
    assert.containsOnce(datePicker.el, "tr.o-selected-range");
    assert.hasClass(datePicker.el.querySelector("tr.o-selected-range"), "o-color");
    assert.strictEqual(
        datePicker.el.querySelector(".o-selected-range").textContent,
        "11121314151617"
    );
});

QUnit.skipWOWL("Scale: init with month", async (assert) => {
    const datePicker = await start({ model: { scale: "month" } });
    assert.containsN(datePicker.el, "td.o-selected-range", 35);
});

QUnit.skipWOWL("Scale: init with year", async (assert) => {
    const datePicker = await start({ model: { scale: "year" } });
    assert.containsN(datePicker.el, "td.o-selected-range", 35);
});

QUnit.skipWOWL("Scale: update prop", async (assert) => {
    const datePicker = await start({ model: { scale: "day" } });

    assert.containsOnce(datePicker.el, "a.o-selected-range");
    assert.strictEqual(datePicker.el.querySelector(".o-selected-range").textContent, "16");

    await datePicker.updateProps((p) => (p.model.scale = "week"));
    assert.containsNone(datePicker.el, "a.o-selected-range");
    assert.containsOnce(datePicker.el, "tr.o-selected-range");
    assert.strictEqual(
        datePicker.el.querySelector(".o-selected-range").textContent,
        "11121314151617"
    );

    await datePicker.updateProps((p) => (p.model.scale = "month"));
    assert.containsNone(datePicker.el, "a.o-selected-range");
    assert.containsNone(datePicker.el, "tr.o-selected-range");
    assert.containsN(datePicker.el, "td.o-selected-range", 35);

    await datePicker.updateProps((p) => (p.model.scale = "year"));
    assert.containsNone(datePicker.el, "a.o-selected-range");
    assert.containsNone(datePicker.el, "tr.o-selected-range");
    assert.containsN(datePicker.el, "td.o-selected-range", 35);

    await datePicker.updateProps((p) => (p.model.scale = "day"));
    assert.containsOnce(datePicker.el, "a.o-selected-range");
    assert.strictEqual(datePicker.el.querySelector(".o-selected-range").textContent, "16");
});

QUnit.skipWOWL("Date: update prop", async (assert) => {
    const datePicker = await start({ model: { scale: "day" } });

    assert.containsOnce(datePicker.el, "a.o-selected-range");
    assert.strictEqual(datePicker.el.querySelector(".o-selected-range").textContent, "16");

    await datePicker.updateProps((p) => (p.model.date = p.model.date.plus({ days: 1 })));
    assert.containsOnce(datePicker.el, "a.o-selected-range");
    assert.strictEqual(datePicker.el.querySelector(".o-selected-range").textContent, "17");
});

QUnit.skipWOWL("First day: 0 = Sunday", async (assert) => {
    const datePicker = await start({ model: { scale: "day", firstDayOfWeek: 0 } });
    assert.strictEqual(datePicker.el.querySelector("thead").textContent, "SMTWTFS");
});

QUnit.skipWOWL("First day: 1 = Monday", async (assert) => {
    const datePicker = await start({ model: { scale: "day", firstDayOfWeek: 1 } });
    assert.strictEqual(datePicker.el.querySelector("thead").textContent, "MTWTFSS");
});

QUnit.skipWOWL("Click on a date should trigger a dom event", async (assert) => {
    assert.expect(2);

    const datePicker = await start({
        model: {
            scale: "day",
            load(params) {
                assert.strictEqual(params.scale, "year");
                assert.ok(params.date.equals(luxon.DateTime.utc(2021, 7, 16)));
            },
        },
    });

    await click(datePicker.el, ".o-selected-range");
});
