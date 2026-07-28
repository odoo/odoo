/** @odoo-module **/

import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
let serverData;
QUnit.module("Project Task Calendar View", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                "project.task": {
                    fields: {
                        start: { string: "Date Start", type: "date" },
                        stop: { string: "Date End", type: "date" },
                    },
                    records: [
                        {
                            id: 1,
                            start: "2017-01-25",
                            stop: "2017-01-26",
                        }, {
                            id: 2,
                            start: "2017-01-02",
                            stop: "2017-01-03",
                        },
                    ],
                    methods: {
                        check_access_rights: function () {
                            return Promise.resolve(true);
                        }
                    }
                },
            },
        }
    });
    QUnit.test("breadcrumb contains 'Tasks by deadline'", async function (assert) {
        serverData.views = {
            "project.task,1,calendar": `<calendar date_start="start" date_stop="stop" mode="day" js_class="project_task_calendar"/>`,
            "project.task,false,search": `<search />`,
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_model: "project.task",
                type: "ir.actions.act_window",
                views: [[1, "calendar"]],
                context: {},
            },
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        assert.equal(document.querySelector(".o_last_breadcrumb_item span").textContent, 'test - Tasks by Deadline');
    });
});
