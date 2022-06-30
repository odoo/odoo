/** @odoo-module **/

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
                        foo: {
                            string: "Foo",
                            type: "text",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: `yop`,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("AceEditorField");

    QUnit.test("AceEditorField on text fields works", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" widget="ace" />
                </form>`,
        });

        assert.ok("ace" in window, "the ace library should be loaded");
        assert.containsOnce(
            target,
            "div.ace_content",
            "should have rendered something with ace editor"
        );

        assert.ok(target.querySelector(".o_field_ace").textContent.includes("yop"));
    });
});
