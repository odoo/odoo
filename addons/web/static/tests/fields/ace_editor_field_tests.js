/** @odoo-module **/

import { setupControlPanelServiceRegistry } from "../search/helpers";
import { makeView } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
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
                            foo: "yop",
                        },
                    ],
                },
            },
        };

        setupControlPanelServiceRegistry();
    });

    QUnit.module("AceEditorField");

    QUnit.test("AceEditorField on text fields works", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" widget="ace" />
                </form>
            `,
        });

        assert.ok("ace" in window, "the ace library should be loaded");
        assert.containsOnce(
            form.el,
            "div.ace_content",
            "should have rendered something with ace editor"
        );
    });
});
