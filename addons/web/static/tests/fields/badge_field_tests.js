/** @odoo-module **/

import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        char_field: {
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
                            char_field: "first record",
                            many2one_field: 4,
                            selection_field: "blocked",
                        },
                        {
                            id: 2,
                            char_field: "second record",
                            many2one_field: 1,
                            selection_field: "normal",
                        },
                        {
                            id: 3,
                            char_field: "", // empty value
                            selection_field: "done",
                        },
                        {
                            id: 4,
                            char_field: "fourth record",
                            selection_field: "done",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BadgeField");

    QUnit.test("BadgeField component on a char field in list view", async function (assert) {
        assert.expect(3);

        const list = await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `<list><field name="char_field" widget="badge"/></list>`,
        });

        assert.containsOnce(list.el, '.o_field_badge[name="char_field"]:contains(first record)');
        assert.containsOnce(list.el, '.o_field_badge[name="char_field"]:contains(second record)');
        assert.containsOnce(list.el, '.o_field_badge[name="char_field"]:contains(fourth record)');
    });

    QUnit.test("BadgeField component on a selection field in list view", async function (assert) {
        assert.expect(3);

        const list = await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `<list><field name="selection_field" widget="badge"/></list>`,
        });

        assert.containsOnce(list.el, '.o_field_badge[name="selection_field"]:contains(Blocked)');
        assert.containsOnce(list.el, '.o_field_badge[name="selection_field"]:contains(Normal)');
        assert.containsN(list.el, '.o_field_badge[name="selection_field"]:contains(Done)', 2);
    });

    QUnit.skip("BadgeField component on a many2one field in list view", async function (assert) {
        assert.expect(2);

        const list = await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `<list><field name="many2one_field" widget="badge"/></list>`,
        });

        // assert.containsOnce(list.el, '.o_field_badge[name="many2one_field"]:contains(first record)');
        // assert.containsOnce(list.el, '.o_field_badge[name="many2one_field"]:contains(aaa)');
    });

    QUnit.skip("BadgeField component with decoration-xxx attributes", async function (assert) {
        assert.expect(3);

        const list = await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `
                <list>
                    <field name="selection_field" widget="badge"/>
                    <field name="char_field" widget="badge" decoration-danger="selection_field == 'done'" decoration-warning="selection_field == 'blocked'"/>
                </list>`,
        });

        assert.containsN(list.el, '.o_field_badge[name="char_field"]', 4);
        assert.containsN(list.el, '.o_field_badge[name="char_field"].bg-danger-light', 2);
        assert.containsN(list.el, '.o_field_badge[name="char_field"].bg-warning-light', 1);
    });
});
