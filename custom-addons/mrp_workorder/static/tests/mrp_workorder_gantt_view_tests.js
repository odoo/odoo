/** @odoo-module **/

import { getFixture, patchDate } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { hoverGridCell, SELECTORS } from "@web_gantt/../tests/helpers";

let target;
let serverData;
QUnit.module("Views > MRP Workorder Gantt", {
    beforeEach() {
        patchDate(2023, 2, 21, 8, 0, 0);
        setupViewRegistries();
        target = getFixture();
        serverData = {
            models: {
                workorder: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        planned_start: { string: "Start Date", type: "datetime" },
                        planned_stop: { string: "Start Date", type: "datetime" },
                        workcenter_id: {
                            string: "Work Center",
                            type: "many2one",
                            relation: "workcenter",
                        },
                        active: { string: "active", type: "boolean", default: true },
                    },
                    records: [
                        {
                            id: 1,
                            name: "Blop",
                            planned_start: "2023-02-24 08:00:00",
                            planned_stop: "2023-03-20 08:00:00",
                            workcenter_id: 1,
                        },
                        {
                            id: 2,
                            name: "Yop",
                            planned_start: "2023-02-22 08:00:00",
                            planned_stop: "2023-03-27 08:00:00",
                            workcenter_id: 2,
                        },
                    ],
                },
                workcenter: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "Assembly Line 1" },
                        { id: 2, name: "Assembly Line 2" },
                    ],
                },
            },
        };
    },
});

QUnit.test("progress bar has the correct unit", async (assert) => {
    assert.expect(13);
    await makeView({
        type: "gantt",
        arch: `
            <gantt js_class="mrp_workorder_gantt"
                date_start="planned_start"
                date_stop="planned_stop"
                progress_bar="workcenter_id"
            />
        `,
        resModel: "workorder",
        serverData,
        groupBy: ["workcenter_id"],
        async mockRPC(_, { args, method, model }) {
            if (method === "gantt_progress_bar") {
                assert.strictEqual(model, "workorder");
                assert.deepEqual(args[0], ["workcenter_id"]);
                assert.deepEqual(args[1], { workcenter_id: [1, 2] });
                return {
                    workcenter_id: {
                        1: { value: 465, max_value: 744 },
                        2: { value: 651, max_value: 744 },
                    },
                };
            }
        },
    });
    assert.containsN(target, SELECTORS.progressBar, 2);
    assert.containsN(target, SELECTORS.progressBarBackground, 2);
    assert.deepEqual(
        [...target.querySelectorAll(SELECTORS.progressBarBackground)].map((el) => el.style.width),
        ["62.5%", "87.5%"]
    );

    assert.containsNone(target, SELECTORS.progressBarForeground);

    await hoverGridCell(1, 1);
    assert.containsOnce(target, SELECTORS.progressBarForeground);
    assert.deepEqual(
        target.querySelector(SELECTORS.progressBarForeground).textContent,
        "465h / 744h"
    );
    assert.deepEqual(
        target.querySelector(SELECTORS.progressBar + " > span > .o_gantt_group_hours_ratio").textContent,
        "(62.5%)"
    );

    await hoverGridCell(2, 1);
    assert.containsOnce(target, SELECTORS.progressBarForeground);
    assert.deepEqual(
        target.querySelector(SELECTORS.progressBarForeground).textContent,
        "651h / 744h"
    );
    assert.deepEqual(
        target.querySelector(SELECTORS.progressBar + " > span > .o_gantt_group_hours_ratio").textContent,
        "(87.5%)"
    );
});
