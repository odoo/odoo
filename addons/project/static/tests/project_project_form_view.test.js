import { expect, test } from "@odoo/hoot";
import {
    onRpc,
    mountView,
    contains,
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

test("project.project (form) show archive action for project manager", async () => {
    onRpc("has_group", () => true);

    await mountView({
        resModel: "project.project",
        type: "form",
        actionMenus: {},
        arch: `
            <form js_class="project_project_form">
                <field name="active"/>
                <field name="name"/>
            </form>
        `,
    });

    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(1);
    await toggleMenuItem("Archive");
    expect(`.modal`).toHaveCount(1);
    await contains(`.modal-footer .btn-primary`).click();
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Unarchive)`).toHaveCount(1);
    await toggleMenuItem("UnArchive");
});
