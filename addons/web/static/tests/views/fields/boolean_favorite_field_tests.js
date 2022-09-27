/** @odoo-module **/

import { click, clickSave, getFixture } from "@web/../tests/helpers/utils";
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
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                    },
                    records: [
                        { id: 1, bar: true },
                        { id: 2, bar: true },
                        { id: 4, bar: true },
                        { id: 3, bar: true },
                        { id: 5, bar: false },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BooleanFavoriteField");

    QUnit.test("FavoriteField in kanban view", async function (assert) {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="bar" widget="boolean_favorite" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            domain: [["id", "=", 1]],
        });

        assert.containsOnce(
            target,
            ".o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star",
            "should be favorite"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_record .o_field_widget .o_favorite > a").textContent,
            " Remove from Favorites",
            'the label should say "Remove from Favorites"'
        );

        // click on favorite
        await click(target, ".o_field_widget .o_favorite");
        assert.containsNone(
            target,
            ".o_kanban_record  .o_field_widget .o_favorite > a i.fa.fa-star",
            "should not be favorite"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_record .o_field_widget .o_favorite > a").textContent,
            " Add to Favorites",
            'the label should say "Add to Favorites"'
        );
    });

    QUnit.test("FavoriteField in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="bar" widget="boolean_favorite" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.containsOnce(
            target,
            ".o_field_widget .o_favorite > a i.fa.fa-star",
            "should be favorite"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .o_favorite > a").textContent,
            " Remove from Favorites",
            'the label should say "Remove from Favorites"'
        );

        // click on favorite
        await click(target, ".o_field_widget .o_favorite");
        assert.containsNone(
            target,
            ".o_field_widget .o_favorite > a i.fa.fa-star",
            "should not be favorite"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .o_favorite > a").textContent,
            " Add to Favorites",
            'the label should say "Add to Favorites"'
        );

        assert.containsOnce(
            target,
            ".o_field_widget .o_favorite > a i.fa.fa-star-o",
            "should not be favorite"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .o_favorite > a").textContent,
            " Add to Favorites",
            'the label should say "Add to Favorites"'
        );

        // click on favorite
        await click(target, ".o_field_widget .o_favorite");
        assert.containsOnce(
            target,
            ".o_field_widget .o_favorite > a i.fa.fa-star",
            "should be favorite"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .o_favorite > a").textContent,
            " Remove from Favorites",
            'the label should say "Remove from Favorites"'
        );

        // save
        await clickSave(target);
        assert.containsOnce(
            target,
            ".o_field_widget .o_favorite > a i.fa.fa-star",
            "should be favorite"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .o_favorite > a").textContent,
            " Remove from Favorites",
            'the label should say "Remove from Favorites"'
        );
    });

    QUnit.test("FavoriteField in editable list view without label", async function (assert) {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="bar" widget="boolean_favorite" nolabel="1" />
                </tree>`,
        });

        assert.containsOnce(
            target,
            ".o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star",
            "should be favorite"
        );

        // switch to edit mode
        await click(target.querySelector("tbody td:not(.o_list_record_selector)"));
        assert.containsOnce(
            target,
            ".o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star",
            "should be favorite"
        );

        // click on favorite
        await click(target.querySelector(".o_data_row .o_field_widget .o_favorite"));
        assert.containsNone(
            target,
            ".o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star",
            "should not be favorite"
        );

        // save
        await clickSave(target);
        assert.containsOnce(
            target,
            ".o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star-o",
            "should not be favorite"
        );
    });
});
