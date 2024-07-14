/** @odoo-module */

import { getFixture, patchDate } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let makeViewParams, target;

QUnit.module("Component", (hooks) => {
    hooks.beforeEach(() => {
        patchDate(2024, 0, 3, 8, 0, 0);
        makeViewParams = {
            type: "kanban",
            resModel: "project.task",
            serverData: {
                models: {
                    "project.task": {
                        fields: {
                            id: {string: "Id", type: "integer"},
                            planned_date_begin: { string: "Date Start", type: "date" },
                            date_deadline: { string: "Date End", type: "date" },
                            stage_id: { string: "Stage", type: "many2one", relation: "stage" },
                        },
                        records: [
                            {
                                id: 1,
                                planned_date_begin: "2024-01-10 06:30:00",
                                date_deadline: "2024-01-10 11:30:00",
                                stage_id: 1,
                            },
                            {
                                id: 2,
                                planned_date_begin: "2024-01-01 06:00:00",
                                date_deadline: "2024-01-01 12:30:00",
                                stage_id: 1,
                            },
                        ],
                    },
                    "stage": {
                        fields: {
                            id: {string: "Id", type: "integer"},
                            name: {string: "name", type: "string"}
                        },
                        records: [
                            {
                                id: 1,
                                name: "In Progress",
                            }
                        ],
                    }
                },
            },
            arch: `
                <kanban>
                    <field name="id"/>
                    <field name="planned_date_begin"/>
                    <field name="date_deadline"/>
                    <field name="stage_id"/>
                    <template>
                        <t t-name="kanban-box">
                            <div>
                                <field name="planned_date_begin" widget="fsm_date"/>
                            </div>
                        </t>
                    </template>
                </kanban>`,
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.module("FsmDateWidget", (hooks) => {
        QUnit.test("Check that FsmDateWidget is displaying information in the correct format", async function (assert) {
            await makeView(makeViewParams);
            assert.containsOnce(target, '.o_kanban_record:first-child div[name="planned_date_begin"]:contains("06:30")', "The format of the planned_date_begin of the record should be HH:MM");
            assert.containsNone(target, '.o_kanban_record:first-child div[name="planned_date_begin"] .oe_kanban_text_red', "If the deadline of the record has not passed already the hour shouldn't be displayed in red");
            assert.containsOnce(target, '.o_kanban_record:nth-child(2) div[name="planned_date_begin"] .oe_kanban_text_red', "If the deadline of the record has already passed the hour should be displayed in red");
        });
    });
});
