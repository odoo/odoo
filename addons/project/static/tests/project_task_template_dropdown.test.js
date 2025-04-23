import { beforeEach, expect, test } from "@odoo/hoot";
import { contains, mountView } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();

function addTemplateTasks() {
    ProjectTask._records.push(
        {
            id: 4,
            name: "Template Task 1",
            project_id: 1,
            stage_id: 1,
            state: "01_in_progress",
            is_template: true,
        },
        {
            id: 5,
            name: "Template Task 2",
            project_id: 1,
            stage_id: 1,
            state: "01_in_progress",
            is_template: true,
        }
    );
}

beforeEach(() => {
    ProjectTask._views = {
        form: `
            <form js_class="project_task_form">
                <field name="name"/>
            </form>
        `,
        kanban: `
            <kanban js_class="project_task_kanban">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `
            <list js_class="project_task_list">
                <field name="name"/>
            </list>
        `,
    };
});

for (const [viewType, newButtonClass] of [
    ["form", ".o_form_button_create"],
    ["kanban", ".o-kanban-button-new"],
    ["list", ".o_list_button_add"],
]) {
    test(`template dropdown in ${viewType} view of a project with no template`, async () => {
        await mountView({
            resModel: "project.task",
            resId: 1,
            type: viewType,
            context: {
                default_project_id: 1,
            },
        });
        expect(newButtonClass).toHaveCount(1, {
            message: "The “New” button should be displayed",
        });
        expect(newButtonClass).not.toHaveClass("dropdown-toggle", {
            message: "The “New” button should not be a dropdown since there is no template",
        });

        // Test that we can create a new record without errors
        await contains(`${newButtonClass}`).click();
    });

    test(`template dropdown in ${viewType} view of a project with one template`, async () => {
        addTemplateTasks();
        await mountView({
            resModel: "project.task",
            resId: 1,
            type: viewType,
            context: {
                default_project_id: 1,
            },
        });
        expect(newButtonClass).toHaveCount(1, {
            message: "The “New” button should be displayed",
        });
        expect(newButtonClass).toHaveClass("dropdown-toggle", {
            message: "The “New” button should be a dropdown since there is a template",
        });

        await contains(newButtonClass).click();
        expect("button.dropdown-item:contains('New Task')").toHaveCount(1, {
            message: "The “New Task” button should be in the dropdown",
        });
        expect("button.dropdown-item:contains('Template Task 1')").toHaveCount(1, {
            message: "There should be a button named after the task template",
        });
    });
}

test("template dropdown should not appear when not in the context of a specific project", async () => {
    addTemplateTasks();
    await mountView({
        resModel: "project.task",
        type: "kanban",
    });

    expect(".o-kanban-button-new").not.toHaveClass("dropdown-toggle", {
        message:
            "The “New” button should not be a dropdown since there is no project in the context",
    });
});
