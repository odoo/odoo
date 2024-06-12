/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Mrp", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                foo: {
                    fields: {
                        duration: { string: "Duration", type: "float" },
                    },
                    records: [{ id: 1, duration: 150.5 }],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.module("MrpTimer");

    QUnit.test("ensure the rendering is based on minutes and seconds", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "foo",
            resId: 1,
            arch: '<form><field name="duration" widget="mrp_timer" readonly="1"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_mrp_timer").textContent,
            "150:30",
            "should not contain hours and be correctly set base on minutes seconds"
        );
    });
});
