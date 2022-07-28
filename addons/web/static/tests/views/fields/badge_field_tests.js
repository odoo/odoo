/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: {
                            string: "Char Field",
                            type: "char",
                            default: "Default char value",
                            searchable: true,
                            trim: true,
                        },
                        many2one_field: {
                            string: "Many2one Field",
                            type: "many2one",
                            relation: "partner",
                            searchable: true,
                        },
                        selection_field: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            many2one_field: 4,
                            selection_field: "blocked",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            many2one_field: 1,
                            selection_field: "normal",
                        },
                        {
                            id: 3,
                            display_name: "", // empty value
                            selection_field: "done",
                        },
                        {
                            id: 4,
                            display_name: "fourth record",
                            selection_field: "done",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
        target = getFixture();
    });

    QUnit.module("BadgeField");

    QUnit.test("BadgeField component on a char field in list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: '<list><field name="display_name" widget="badge"/></list>',
        });

        assert.containsOnce(target, '.o_field_badge[name="display_name"]:contains(first record)');
        assert.containsOnce(target, '.o_field_badge[name="display_name"]:contains(second record)');
        assert.containsOnce(target, '.o_field_badge[name="display_name"]:contains(fourth record)');
    });

    QUnit.test("BadgeField component on a selection field in list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: '<list><field name="selection_field" widget="badge"/></list>',
        });

        assert.containsOnce(target, '.o_field_badge[name="selection_field"]:contains(Blocked)');
        assert.containsOnce(target, '.o_field_badge[name="selection_field"]:contains(Normal)');
        assert.containsN(target, '.o_field_badge[name="selection_field"]:contains(Done)', 2);
    });

    QUnit.test("BadgeField component on a many2one field in list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: '<list><field name="many2one_field" widget="badge"/></list>',
        });

        assert.containsOnce(target, '.o_field_badge[name="many2one_field"]:contains(first record)');
        assert.containsOnce(
            target,
            '.o_field_badge[name="many2one_field"]:contains(fourth record)'
        );
    });

    QUnit.test("BadgeField component with decoration-xxx attributes", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `
                <list>
                    <field name="selection_field" widget="badge"/>
                    <field name="display_name" widget="badge" decoration-danger="selection_field == 'done'" decoration-warning="selection_field == 'blocked'"/>
                </list>`,
        });

        assert.containsN(target, '.o_field_badge[name="display_name"]', 4);
        assert.containsOnce(target, '.o_field_badge[name="display_name"] .bg-danger');
        assert.containsOnce(target, '.o_field_badge[name="display_name"] .bg-warning');
    });
});
