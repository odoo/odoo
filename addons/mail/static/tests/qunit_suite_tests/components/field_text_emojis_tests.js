/**@odoo-module **/

import { clickEdit, clickSave, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("Field text emojis", (hooks) => {
    let target = undefined;
    let serverData = undefined;
    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: { type: "char" }
                    },
                    records: [{ id: 1 }]
                }
            }
        };

        setupViewRegistries();
    });

    QUnit.test("emojis button is not shown in readonly", async (assert) => {
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            arch: `<form><field name="foo" widget="text_emojis" /></form>`,
            serverData
        });

        assert.containsOnce(target, ".o_field_text_emojis");
        assert.containsOnce(target, ".o_field_text_emojis button");
        assert.isNotVisible(target.querySelector(".o_field_text_emojis button"));

        await clickEdit(target);
        assert.isVisible(target, ".o_field_text_emojis button .fa-smile");

        await clickSave(target);
        assert.containsOnce(target, ".o_field_text_emojis button");
        assert.isNotVisible(target.querySelector(".o_field_text_emojis button"));
    });
});
