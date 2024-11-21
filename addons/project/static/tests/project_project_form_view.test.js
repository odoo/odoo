import { expect, test } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";

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
