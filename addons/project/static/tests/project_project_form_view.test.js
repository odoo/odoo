import { expect, test } from "@odoo/hoot";
import { click, edit, animationFrame } from "@odoo/hoot-dom";
import {
    mountView,
    contains,
    onRpc,
    toggleMenuItem,
    toggleActionMenu,
} from "@web/../tests/web_test_helpers";

import { defineProjectModels } from "./project_models";

defineProjectModels();

test("project.project (form)", async () => {
    await mountView({
        resModel: "project.project",
        resId: 1,
        type: "form",
        arch: `
            <form js_class="form_description_expander">
                <field name="name"/>
            </form>
        `,
    });
    expect(".o_form_view").toHaveCount(1);
});

const formViewParams = {
    resModel: "project.project",
    type: "form",
    actionMenus: {},
    arch: `
        <form js_class="project_project_form">
            <field name="active"/>
            <field name="name"/>
        </form>
    `,
}

test("project.project (form) hide archive action for project user", async () => {
    onRpc("has_group", ({ args }) => args[1] === "project.group_project_user");
    await mountView(formViewParams);
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(0, { message: "Archive action should not be visible" });
});

test("project.project (form) show archive action for project manager", async () => {
    onRpc("has_group", () => true);
    await mountView(formViewParams);
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(1, { message: "Arhive action should be visible" });
    await toggleMenuItem("Archive");
    await contains(`.modal-footer .btn-primary`).click();
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Unarchive)`).toHaveCount(1, { message: "Unarchive action should be visible" });
    await toggleMenuItem("UnArchive");
});

test.tags("desktop");
test("project.project (form): removing analytic account shows confirm dialog and sets allow_timesheets to false on confirm", async () => {
    await mountView({
        resModel: "project.project",
        resId: 1,
        type: "form",
        arch: `
        <form js_class="project_project_form">
            <group>
                <field name="name"/>
                <field name="account_id"/>
                <field name="allow_timesheets"/>
            </group>
        </form>
    `,
    });

    expect('.o_field_widget[name="allow_timesheets"] input[type="checkbox"]').toBeChecked();
    expect('.o_field_widget[name="account_id"] input').toHaveValue("Test Analytic Account");

    await click('.o_field_widget[name="account_id"] input');
    await edit("");
    await click('.o_field_widget[name="name"] input');

    expect('.o_field_widget[name="account_id"] input').toHaveValue("");
    expect('.o_field_widget[name="allow_timesheets"] input[type="checkbox"]').toBeChecked();

    await animationFrame();

    await contains(".o_form_button_save").click();

    await contains('.o_dialog .btn-primary').click();
    await animationFrame();

    expect('.o_field_widget[name="allow_timesheets"] input[type="checkbox"]').not.toBeChecked();
    expect('.o_field_widget[name="account_id"] input').toHaveValue("");
});
