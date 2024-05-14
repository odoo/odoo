import { describe, expect, test } from "@odoo/hoot";
import { contains, mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";
import { startServer } from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("cannot edit stage_id with different projects", async () => {
    const pyEnv = await startServer();
    const [projectId1, projectId2] = pyEnv["project.project"].create([
        { name: "Project 1" },
        { name: "Project 2" },
    ]);
    const [stageId1] = pyEnv['project.task.type'].create([
        { name: "New" },
        { name: "New 2" },
    ]);
    pyEnv["project.task"].create([
        { name: "Task 1", project_id: projectId1, stage_id: stageId1, priority: "0" },
        { name: "Task 2", project_id: projectId2, stage_id: stageId1, priority: "0" },
    ]);
    await mountView({
        type: "list",
        resModel: "project.task",
        arch: `
                <tree multi_edit="1" js_class="project_task_list">
                    <field name="project_id"/>
                    <field name="stage_id"/>
                </tree>`,
    });

    const [firstRow, secondRow] = document.querySelectorAll(".o_data_row");
    await contains(firstRow.querySelector(".o_list_record_selector input")).click();
    expect(".o_readonly_modifier").not.toBeDisplayed();

    await contains(secondRow.querySelector(".o_list_record_selector input")).click();
    expect(firstRow.querySelector(".o_readonly_modifier")).toBeDisplayed();
    expect(firstRow.querySelectorAll(".o_data_cell")[1]).toHaveClass("o_readonly_modifier");
    expect(secondRow.querySelector(".o_readonly_modifier")).toBeDisplayed();
    expect(secondRow.querySelectorAll(".o_data_cell")[1]).toHaveClass("o_readonly_modifier");
});
