/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let makeViewParams, target;

QUnit.module("Project", (hooks) => {
    hooks.beforeEach(() => {
        makeViewParams = {
            type: "form",
            resModel: "project.project",
            serverData: {
                models: {
                    "project.project": {
                        fields: {
                            id: { string: "Id", type: "integer" },
                        },
                        records: [{ id: 1, display_name: "First record" }],
                    },
                },
            },
            arch: `<form js_class="form_description_expander"><field name="display_name"/></form>`,
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.module("Form");
    QUnit.test("project form view", async function (assert) {
        await makeView(makeViewParams);
        assert.containsOnce(target, ".o_form_view");
    });
});
