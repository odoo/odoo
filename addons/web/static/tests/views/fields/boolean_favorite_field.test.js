import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    bar = fields.Boolean({ default: true });

    _records = [
        { id: 1, bar: true },
        { id: 2, bar: true },
        { id: 3, bar: true },
        { id: 4, bar: true },
        { id: 5, bar: false },
    ];
}

defineModels([Partner]);

test("FavoriteField in kanban view", async () => {
    await mountView({
        resModel: "partner",
        domain: [["id", "=", 1]],
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="bar" widget="boolean_favorite"/>
                        </div>
                    </t>
                </templates>
            </kanban>
        `,
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a`).toHaveText("Remove from Favorites", {
        message: `the label should say "Remove from Favorites"`,
    });

    // click on favorite
    click(`.o_field_widget .o_favorite`);
    await animationFrame();
    expect(`.o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(0, {
        message: "should not be favorite",
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a`).toHaveText("Add to Favorites", {
        message: `the label should say "Add to Favorites"`,
    });
});

test("FavoriteField saves changes by default", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("save");
        expect(args).toEqual([[1], { bar: false }]);
    });

    await mountView({
        resModel: "partner",
        domain: [["id", "=", 1]],
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="bar" widget="boolean_favorite"/>
                        </div>
                    </t>
                </templates>
            </kanban>
        `,
    });

    // click on favorite
    click(`.o_field_widget .o_favorite`);
    await animationFrame();
    expect(`.o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(0, {
        message: "should not be favorite",
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a`).toHaveText("Add to Favorites", {
        message: `the label should say "Add to Favorites"`,
    });
    expect(["save"]).toVerifySteps();
});

test("FavoriteField does not save if autosave option is set to false", async () => {
    onRpc("web_save", () => {
        expect.step("save");
    });

    await mountView({
        resModel: "partner",
        domain: [["id", "=", 1]],
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="bar" widget="boolean_favorite" options="{'autosave': False}"/>
                        </div>
                    </t>
                </templates>
            </kanban>
        `,
    });

    // click on favorite
    click(`.o_field_widget .o_favorite`);
    await animationFrame();
    expect(`.o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(0, {
        message: "should not be favorite",
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a`).toHaveText("Add to Favorites", {
        message: `the label should say "Add to Favorites"`,
    });
    expect([]).toVerifySteps();
});

test("FavoriteField in form view", async () => {
    onRpc("web_save", () => {
        expect.step("save");
    });

    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="bar" widget="boolean_favorite"/></form>`,
    });
    expect(`.o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });
    expect(`.o_field_widget .o_favorite > a`).toHaveText("Remove from Favorites", {
        message: `the label should say "Remove from Favorites"`,
    });

    // click on favorite
    click(`.o_field_widget .o_favorite`);
    await animationFrame();
    expect(["save"]).toVerifySteps();
    expect(`.o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(0, {
        message: "should not be favorite",
    });
    expect(`.o_field_widget .o_favorite > a i.fa.fa-star-o`).toHaveCount(1, {
        message: "should not be favorite",
    });
    expect(`.o_field_widget .o_favorite > a`).toHaveText("Add to Favorites", {
        message: `the label should say "Add to Favorites"`,
    });

    // click on favorite
    click(`.o_field_widget .o_favorite`);
    await animationFrame();
    expect(["save"]).toVerifySteps();
    expect(`.o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });
    expect(`.o_field_widget .o_favorite > a`).toHaveText("Remove from Favorites", {
        message: `the label should say "Remove from Favorites"`,
    });
});

test("FavoriteField in editable list view without label", async () => {
    onRpc("has_group", () => true);

    await mountView({
        resModel: "partner",
        type: "list",
        arch: `
            <tree editable="bottom">
                <field name="bar" widget="boolean_favorite" nolabel="1" options="{'autosave': False}"/>
            </tree>
        `,
    });
    expect(`.o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });

    // switch to edit mode
    click(`tbody td:not(.o_list_record_selector)`);
    await animationFrame();
    expect(`.o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });

    // click on favorite
    click(`.o_data_row .o_field_widget .o_favorite`);
    await animationFrame();
    expect(`.o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(0, {
        message: "should not be favorite",
    });

    // save
    click(`.o_list_button_save`);
    await animationFrame();
    expect(`.o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star-o`).toHaveCount(1, {
        message: "should not be favorite",
    });
});
