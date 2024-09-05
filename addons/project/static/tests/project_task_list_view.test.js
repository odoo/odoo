import { describe, expect, test } from "@odoo/hoot";
import { check, queryAll, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();

describe.current.tags("desktop");

test("project.task (list): cannot edit stage_id with different projects", async () => {
    ProjectTask._records = [
        {
            id: 1,
            project_id: 1,
            stage_id: 1,
        },
        {
            id: 2,
            project_id: 2,
            stage_id: 1,
        },
    ];

    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `
            <list multi_edit="1" js_class="project_task_list">
                <field name="project_id"/>
                <field name="stage_id"/>
            </list>
        `,
    });

    const [firstRow, secondRow] = queryAll(".o_data_row");
    await check(".o_list_record_selector input", { root: firstRow });
    await animationFrame();
    expect(queryAll("[name=stage_id]")).not.toHaveClass("o_readonly_modifier");

    await check(".o_list_record_selector input", { root: secondRow });
    await animationFrame();
    expect(queryOne("[name=stage_id]", { root: firstRow })).toHaveClass("o_readonly_modifier");
    expect(queryOne("[name=stage_id]", { root: secondRow })).toHaveClass("o_readonly_modifier");
});
