/** @odoo-module **/

import { getFixture, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { clickDate, selectDateRange } from "@web/../tests/views/calendar/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";

let target;
let serverData;

QUnit.module("Views", ({ beforeEach }) => {
    beforeEach(() => {
        patchDate(2016, 11, 12, 8, 0, 0);

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });

        target = getFixture();
        setupViewRegistries();

        serverData = {
            models: {
                "project.task": {
                    fields: {
                        planned_date_begin: { string: "Date Start", type: "date" },
                        planned_date_start: { string: "Date Start", type: "date" },
                        date_deadline: { string: "Date End", type: "date" },
                    },
                    methods: {
                        has_access: function () {
                            return Promise.resolve(true);
                        },
                    },
                },
            },
            views: {
                "project.task,false,form": `
                <form>
                    <field name="planned_date_begin" invisible="1" />
                    <sheet string="Task">
                        <group>
                            <field name="date_deadline" widget="daterange" options="{'start_date_field': 'planned_date_begin'}"/>
                        </group>
                    </sheet>
                </form>
            `,
            },
        };
    });

    QUnit.module("CalendarView");

    QUnit.test(
        `Planned Date Begin Should Not Be Set When Selecting A Single Day`,
        async (assert) => {
            await makeView({
                type: "calendar",
                resModel: "project.task",
                serverData,
                arch: `
                <calendar date_start="planned_date_start"
                    date_stop="date_deadline"
                    mode="month"
                    js_class="project_enterprise_task_calendar"
                    event_open_popup="true"
                    quick_create="0"/>
            `,
            });

            await clickDate(target, "2016-12-13");
            assert.strictEqual(target.querySelector(".modal-title").textContent, "New Task");
            assert.containsOnce(
                target,
                "button.o_add_start_date",
                "the planned date begin should not be set when selecting a single day"
            );
        }
    );

    QUnit.test(`Planned Date Begin Should Be Set When Selecting Multiple Days`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "project.task",
            serverData,
            arch: `
                <calendar date_start="planned_date_start"
                    date_stop="date_deadline"
                    mode="month"
                    js_class="project_enterprise_task_calendar"
                    event_open_popup="true"
                    quick_create="0"/>
            `,
        });

        await selectDateRange(target, "2016-12-13", "2016-12-16");
        assert.strictEqual(target.querySelector(".modal-title").textContent, "New Task");
        assert.containsNone(
            target,
            "button.o_add_start_date",
            "the planned date begin should not be set when selecting a single day"
        );
    });
});
