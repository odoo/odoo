import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, hover } from "@odoo/hoot-dom";
import { contains, mockService, mountView, onRpc } from "@web/../tests/web_test_helpers";

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

    test(`template dropdown in ${viewType} view of a project with one template with showing Edit and Delete actions`, async () => {
        addTemplateTasks();

        onRpc(({ method }) => {
            if (method === "unlink") {
                expect.step(method);
            }
        });

        mockService("action", {
            doAction(action) {
                if (action.res_id === 4 && action.res_model === "project.task") {
                    expect.step("task template opened");
                }
            },
        });

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
        expect("span.dropdown-item:contains('Template Task 1')").toHaveCount(1, {
            message: "There should be an item named after the task template",
        });

        await hover("span.dropdown-item:contains('Template Task 1')");
        await animationFrame();

        await contains(".o_template_icon_group:first > button[data-icon='delete'].oi-filled").click();
        expect(".modal-body").toHaveCount(1, {
            message: "A confirmation modal should appear when deleting a template",
        });

        await contains(".modal-footer .btn-primary").click();
        expect.verifySteps(["unlink"]);

        await animationFrame();
        await contains(".o_template_icon_group:first > button[data-icon='edit']").click();
        expect.verifySteps(["task template opened"]);

    });
}

for (const [viewType, newButtonClass] of [
    ["kanban", ".o-kanban-button-new"],
    ["list", ".o_list_button_add"],
]) {
    test(`clicking a template in ${viewType} view opens the form view of the current action with the template in the context`, async () => {
        addTemplateTasks();

        mockService("action", {
            doAction(action, options) {
                expect.step("new task form opened");
                expect(options.viewType).toBe("form");
                expect(options.additionalContext).toEqual(
                    {
                        active_id: 1,
                        active_ids: [1],
                        active_model: "project.project",
                        default_task_template_id: 4,
                    },
                    {
                        message:
                            "The template should prefill the form, and the record of the action should be kept to evaluate its context",
                    }
                );
            },
        });

        await mountView({
            resModel: "project.task",
            type: viewType,
            context: {
                active_id: 1,
                active_ids: [1],
                active_model: "project.project",
                default_project_id: 1,
            },
        });
        await contains(newButtonClass).click();
        await contains("span.dropdown-item:contains('Template Task 1')").click();
        expect.verifySteps(["new task form opened"]);
    });
}

function trackTemplateLoads() {
    onRpc("web_save", () => expect.step("web_save"));
    onRpc("onchange", ({ kwargs }) => {
        expect.step(`onchange with template ${kwargs.context.default_task_template_id ?? "none"}`);
        expect(kwargs.context.default_project_id).toBe(1, {
            message: "The context of the form should be kept",
        });
    });
    mockService("action", {
        doAction() {
            expect.step("doAction");
        },
    });
}

test("clicking a template in form view saves the current task and loads a new one prefilled from it", async () => {
    addTemplateTasks();
    trackTemplateLoads();

    await mountView({
        resModel: "project.task",
        resId: 1,
        type: "form",
        context: {
            default_project_id: 1,
        },
    });
    await contains(".o_field_widget[name=name] input").edit("Edited task");
    await contains(".o_form_button_create").click();
    await contains("span.dropdown-item:contains('Template Task 1')").click();
    expect.verifySteps(["web_save", "onchange with template 4"]);
});

test("clicking another template in the form of a task opened from a template replaces it", async () => {
    addTemplateTasks();
    trackTemplateLoads();

    await mountView({
        resModel: "project.task",
        type: "form",
        context: {
            default_project_id: 1,
            default_task_template_id: 4,
        },
    });
    expect.verifySteps(["onchange with template 4"]);

    await contains(".o_form_button_create").click();
    await contains("span.dropdown-item:contains('Template Task 2')").click();
    expect.verifySteps(["onchange with template 5"]);
});

test("New Task in the form of a task opened from a template is not prefilled from it", async () => {
    addTemplateTasks();
    trackTemplateLoads();

    await mountView({
        resModel: "project.task",
        type: "form",
        context: {
            default_project_id: 1,
            default_task_template_id: 4,
        },
    });
    expect.verifySteps(["onchange with template 4"]);

    await contains(".o_form_button_create").click();
    await contains("button.dropdown-item:contains('New Task')").click();
    expect.verifySteps(["onchange with template false"]);
});
