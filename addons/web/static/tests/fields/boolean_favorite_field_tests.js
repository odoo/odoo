/** @odoo-module **/

import { click } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
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
        assert.expect(4);

        const kanban = await makeView({
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
                </kanban>
            `,
            domain: [["id", "=", 1]],
        });

        assert.containsOnce(
            kanban.el,
            ".o_kanban_record .o_field_widget.o_favorite > a i.fa.fa-star",
            "should be favorite"
        );
        assert.strictEqual(
            kanban.el.querySelector(".o_kanban_record .o_field_widget.o_favorite > a").textContent,
            " Remove from Favorites",
            'the label should say "Remove from Favorites"'
        );

        // click on favorite
        await click(kanban.el, ".o_field_widget.o_favorite");
        assert.containsNone(
            kanban.el,
            ".o_kanban_record  .o_field_widget.o_favorite > a i.fa.fa-star",
            "should not be favorite"
        );
        assert.strictEqual(
            kanban.el.querySelector(".o_kanban_record .o_field_widget.o_favorite > a").textContent,
            " Add to Favorites",
            'the label should say "Add to Favorites"'
        );
    });

    QUnit.test("FavoriteField in form view", async function (assert) {
        assert.expect(10);

        const form = await makeView({
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
                </form>
            `,
        });

        assert.containsOnce(
            form.el,
            ".o_field_widget.o_favorite > a i.fa.fa-star",
            "should be favorite"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget.o_favorite > a").textContent,
            " Remove from Favorites",
            'the label should say "Remove from Favorites"'
        );

        // click on favorite
        await click(form.el, ".o_field_widget.o_favorite");
        assert.containsNone(
            form.el,
            ".o_field_widget.o_favorite > a i.fa.fa-star",
            "should not be favorite"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget.o_favorite > a").textContent,
            " Add to Favorites",
            'the label should say "Add to Favorites"'
        );

        // switch to edit mode
        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form.el,
            ".o_field_widget.o_favorite > a i.fa.fa-star-o",
            "should not be favorite"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget.o_favorite > a").textContent,
            " Add to Favorites",
            'the label should say "Add to Favorites"'
        );

        // click on favorite
        await click(form.el, ".o_field_widget.o_favorite");
        assert.containsOnce(
            form.el,
            ".o_field_widget.o_favorite > a i.fa.fa-star",
            "should be favorite"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget.o_favorite > a").textContent,
            " Remove from Favorites",
            'the label should say "Remove from Favorites"'
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.containsOnce(
            form.el,
            ".o_field_widget.o_favorite > a i.fa.fa-star",
            "should be favorite"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget.o_favorite > a").textContent,
            " Remove from Favorites",
            'the label should say "Remove from Favorites"'
        );
    });

    QUnit.skip("FavoriteField in editable list view without label", async function (assert) {
        assert.expect(4);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="bar" widget="boolean_favorite" nolabel="1" />
                </tree>
            `,
        });

        assert.containsOnce(
            list.el,
            ".o_data_row:first .o_field_widget.o_favorite > a i.fa.fa-star",
            "should be favorite"
        );

        // switch to edit mode
        await click(list.el.querySelector("tbody td:not(.o_list_record_selector)"));
        assert.containsOnce(
            list.el,
            ".o_data_row:first .o_field_widget.o_favorite > a i.fa.fa-star",
            "should be favorite"
        );

        // click on favorite
        await click(list.el.querySelector(".o_data_row .o_field_widget.o_favorite"));
        assert.containsNone(
            list.el,
            ".o_data_row:first .o_field_widget.o_favorite > a i.fa.fa-star",
            "should not be favorite"
        );

        // save
        await click(list.el, ".o_list_button_save");
        assert.containsOnce(
            list.el,
            ".o_data_row:first .o_field_widget.o_favorite > a i.fa.fa-star-o",
            "should not be favorite"
        );
    });
});
