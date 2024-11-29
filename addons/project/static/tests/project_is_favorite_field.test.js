import { beforeEach, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { mountView, onRpc } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectProject } from "./project_models";

defineProjectModels();
beforeEach(() => {
    ProjectProject._records = [
        {
            id: 1,
            name: "Project A",
        },
    ];
    ProjectProject._views = {
        "kanban,false": `
            <kanban class="o_kanban_test" edit="0">
                <template>
                    <t t-name="card">
                        <field name="is_favorite" widget="project_is_favorite" nolabel="1"/>
                        <field name="name"/>
                    </t>
                </template>
            </kanban>
        `,
    };
});

test("Check is_favorite field is still editable even if the record/view is in readonly.", async () => {
    onRpc("project.project", "web_save", ({ args }) => {
        const [ids, vals] = args;
        expect(ids).toEqual([1]);
        expect(vals).toEqual({ is_favorite: true });
        expect.step("web_save");
    });

    await mountView({
        resModel: "project.project",
        type: "kanban",
    });

    expect("div[name=is_favorite] .o_favorite").toHaveCount(1);
    expect.verifySteps([]);
    await click("div[name=is_favorite] .o_favorite");
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test("Check is_favorite field is readonly if the field is readonly", async () => {
    onRpc("project.project", "web_save", () => {
        expect.step("web_save");
    });

    ProjectProject._views["kanban,false"] = ProjectProject._views["kanban,false"].replace(
        'widget="project_is_favorite"',
        'widget="project_is_favorite" readonly="1"'
    );

    await mountView({
        resModel: "project.project",
        type: "kanban",
    });

    expect("div[name=is_favorite] .o_favorite").toHaveCount(1);
    expect.verifySteps([]);
    await click("div[name=is_favorite] .o_favorite");
    await animationFrame();
    expect.verifySteps([]);
});
