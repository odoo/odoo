import { describe, expect, test } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("project form view", async () => {
    await mountView({
        resModel: "project.project",
        type: "form",
        arch: `<form js_class="project_form"><field name="display_name"/></form>`,
    });
    expect(".o_form_view").toBeDisplayed();
});
