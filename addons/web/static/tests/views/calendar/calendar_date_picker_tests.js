/** @odoo-module **/

import { CalendarDatePicker } from "@web/views/calendar/date_picker/calendar_date_picker";
import { click, getFixture, patchDate } from "../../helpers/utils";
import { makeEnv, makeFakeModel, mountComponent } from "./helpers";

let target;

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarDatePicker, env, {
        model,
        ...props,
    });
}

QUnit.module("CalendarView - DatePicker", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
        patchDate(2021, 7, 14, 8, 0, 0);
    });

    QUnit.test("Mount a CalendarDatePicker", async (assert) => {
        await start({ model: { scale: "day" } });
        assert.containsOnce(target, ".o_calendar_mini.hasDatepicker");
        assert.strictEqual(target.querySelector(".o_selected_range").textContent, "16");
        assert.containsOnce(target, `[data-month="6"][data-year="2021"] .o_selected_range`);
        assert.strictEqual(target.querySelector(".ui-datepicker-month").textContent, "Jul");
        assert.strictEqual(target.querySelector(".ui-datepicker-year").textContent, "2021");
        assert.strictEqual(target.querySelector("thead").textContent, "SMTWTFS");
    });

    QUnit.test("Scale: init with day", async (assert) => {
        await start({ model: { scale: "day" } });
        assert.containsOnce(target, ".o_selected_range");
        assert.containsOnce(target, "a.o_selected_range");
        assert.strictEqual(target.querySelector(".o_selected_range").textContent, "16");
    });

    QUnit.test("Scale: init with week", async (assert) => {
        await start({ model: { scale: "week" } });
        assert.containsOnce(target, ".o_selected_range");
        assert.containsOnce(target, "tr.o_selected_range");
        assert.hasClass(target.querySelector("tr.o_selected_range"), "o_color");
        assert.strictEqual(target.querySelector(".o_selected_range").textContent, "11121314151617");
    });

    QUnit.test("Scale: init with month", async (assert) => {
        await start({ model: { scale: "month" } });
        assert.containsN(target, "td.o_selected_range", 35);
    });

    QUnit.test("Scale: init with year", async (assert) => {
        await start({ model: { scale: "year" } });
        assert.containsN(target, "td.o_selected_range", 35);
    });

    QUnit.test("First day: 0 = Sunday", async (assert) => {
        await start({ model: { scale: "day", firstDayOfWeek: 0 } });
        assert.strictEqual(target.querySelector("thead").textContent, "SMTWTFS");
    });

    QUnit.test("First day: 1 = Monday", async (assert) => {
        await start({ model: { scale: "day", firstDayOfWeek: 1 } });
        assert.strictEqual(target.querySelector("thead").textContent, "MTWTFSS");
    });

    QUnit.test("Click on active day should change scale : day -> month", async (assert) => {
        assert.expect(2);

        await start({
            model: {
                scale: "day",
                load(params) {
                    assert.strictEqual(params.scale, "month");
                    assert.ok(params.date.equals(luxon.DateTime.local(2021, 7, 16)));
                },
            },
        });

        await click(target, ".ui-state-active");
    });

    QUnit.test("Click on active day should change scale : month -> week", async (assert) => {
        assert.expect(2);

        await start({
            model: {
                scale: "month",
                load(params) {
                    assert.strictEqual(params.scale, "week");
                    assert.ok(params.date.equals(luxon.DateTime.local(2021, 7, 16)));
                },
            },
        });

        await click(target, ".ui-state-active");
    });

    QUnit.test("Click on active day should change scale : week -> day", async (assert) => {
        assert.expect(2);

        await start({
            model: {
                scale: "week",
                load(params) {
                    assert.strictEqual(params.scale, "day");
                    assert.ok(params.date.equals(luxon.DateTime.local(2021, 7, 16)));
                },
            },
        });

        await click(target, ".ui-state-active");
    });

    QUnit.test("Scale: today is correctly highlighted", async (assert) => {
        patchDate(2021, 6, 4, 8, 0, 0);
        await start({ model: { scale: "month" } });
        assert.containsOnce(target, ".ui-datepicker-today");
        assert.strictEqual(target.querySelector(".ui-datepicker-today").textContent, "4");
    });
});
