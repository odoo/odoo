/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("Project Task List View", (hooks) => {
    QUnit.test("cannot edit stage_id with different projects", async function (assert) {
        const target = getFixture();
        setupViewRegistries();
        await makeView({
            type: "list",
            resModel: "project.task",
            arch: `
                <list multi_edit="1" js_class="project_task_list">
                    <field name="project_id"/>
                    <field name="stage_id"/>
                </list>
            `,
            serverData: {
                models: {
                    "project.task": {
                        fields: {
                            project_id: {
                                string: "Project",
                                type: "many2one",
                                relation: "project.project",
                            },
                            stage_id: {
                                string: "Stage",
                                type: "many2one",
                                relation: "project.task.type",
                            }
                        },
                        records: [
                            {
                                id: 1,
                                project_id: 1,
                                stage_id: 1,
                            }, {
                                id: 2,
                                project_id: 2,
                                stage_id: 1,
                            },
                        ],
                    },
                    "project.project": {
                        records: [
                            {
                                id: 1,
                            }, {
                                id: 2,
                            },
                        ],
                    },
                    "project.task.type": {
                        records: [
                            {
                                id: 1,
                            }, {
                                id: 2,
                            },
                        ],
                    },
                },
            }
        });

        const [firstRow, secondRow] = target.querySelectorAll(".o_data_row");
        await click(firstRow.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsNone(firstRow, ".o_readonly_modifier", "None of the fields should be readonly");
        assert.containsNone(secondRow, ".o_readonly_modifier", "None of the fields should be readonly");

        await click(secondRow.querySelector(".o_data_row .o_list_record_selector input"));
        assert.containsOnce(firstRow, ".o_readonly_modifier");
        assert.hasClass(firstRow.querySelectorAll(".o_data_cell")[1], "o_readonly_modifier", "The stage_id should be readonly");
        assert.containsOnce(secondRow, ".o_readonly_modifier");
        assert.hasClass(secondRow.querySelectorAll(".o_data_cell")[1], "o_readonly_modifier", "The stage_id should be readonly");
    });
});
