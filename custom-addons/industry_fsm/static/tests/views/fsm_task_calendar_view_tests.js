/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { getFixture, patchDate, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { clickDate } from "@web/../tests/views/calendar/helpers";

let makeViewParams, target;

QUnit.module("Views > TaskCalendarView", (hooks) => {
    hooks.beforeEach(() => {
        patchDate(2024, 0, 3, 8, 0, 0);
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
        makeViewParams = {
            type: "calendar",
            resModel: "project.task",
            serverData: {
                views: {
                "project.task,false,form": `
                <form>
                    <field name='id'/>
                    <field name='name'/>
                    <field name='date_deadline'/>
                    <field name='planned_date_begin'/>
                </form>`,
                },
                models: {
                    "project.task": {
                        fields: {
                            planned_date_start: { string: "Date Start", type: "date" },
                            date_deadline: { string: "Date End", type: "date" },
                            planned_date_begin: { string: "Date Begin", type: "date" },
                        },
                        records: [
                            {
                                id: 1,
                                planned_date_start: "2024-01-05",
                                date_deadline: "2024-01-06",
                            }, {
                                id: 2,
                                planned_date_start: "2024-01-01",
                                date_deadline: "2024-01-03",
                            },
                        ],
                        methods: {
                            check_access_rights: function () {
                                return Promise.resolve(true);
                            },
                        },
                    },
                },
            },
            arch: `<calendar date_start="planned_date_start" date_stop="date_deadline" event_open_popup="1" mode="month" js_class="fsm_task_calendar" quick_create="0"/>`,
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.test("fsm task calendar view", async function (assert) {
        await makeView(makeViewParams);
        assert.containsOnce(target, ".o_calendar_view");

        await clickDate(target, "2024-01-09");
        await nextTick();

        const input = target.querySelector("div[name='planned_date_begin'] input");
        assert.strictEqual(input.value, "01/09/2024","The planned_date_begin field should hold the planned_date_start value in the record thanks to the fsmCalendarModel makeContextDefault inheritance");
    });
});
