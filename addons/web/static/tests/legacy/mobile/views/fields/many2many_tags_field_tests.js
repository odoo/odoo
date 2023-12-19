/** @odoo-module alias=@web/../tests/mobile/views/fields/many2many_tags_field_tests default=false */

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        timmy: { string: "pokemon", type: "many2many", relation: "partner_type" },
                    },
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char" },
                    },
                    records: [
                        { id: 12, display_name: "gold" },
                        { id: 14, display_name: "silver" },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("Many2ManyTagsField");

    QUnit.test("Many2ManyTagsField placeholder should be correct", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" placeholder="foo"/>
                </form>`,
        });
        assert.strictEqual(target.querySelector("#timmy_0").placeholder, "foo");
    });

    QUnit.test("Many2ManyTagsField placeholder should be empty", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags"/>
                </form>`,
        });
        assert.strictEqual(target.querySelector("#timmy_0").placeholder, "");
    });
});
