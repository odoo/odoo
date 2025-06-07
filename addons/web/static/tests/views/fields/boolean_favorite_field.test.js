import { expect, test } from "@odoo/hoot";
import { queryAllProperties, queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

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
                    <t t-name="card">
                        <field name="bar" widget="boolean_favorite"/>
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
    await contains(`.o_field_widget .o_favorite`).click();
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
                    <t t-name="card">
                        <field name="bar" widget="boolean_favorite"/>
                    </t>
                </templates>
            </kanban>
        `,
    });

    // click on favorite
    await contains(`.o_field_widget .o_favorite`).click();
    expect(`.o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(0, {
        message: "should not be favorite",
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a`).toHaveText("Add to Favorites", {
        message: `the label should say "Add to Favorites"`,
    });
    expect.verifySteps(["save"]);
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
                    <t t-name="card">
                        <field name="bar" widget="boolean_favorite" options="{'autosave': False}"/>
                    </t>
                </templates>
            </kanban>
        `,
    });

    // click on favorite
    await contains(`.o_field_widget .o_favorite`).click();
    expect(`.o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(0, {
        message: "should not be favorite",
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a`).toHaveText("Add to Favorites", {
        message: `the label should say "Add to Favorites"`,
    });
    expect.verifySteps([]);
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
    await contains(`.o_field_widget .o_favorite`).click();
    expect.verifySteps(["save"]);
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
    await contains(`.o_field_widget .o_favorite`).click();
    expect.verifySteps(["save"]);
    expect(`.o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });
    expect(`.o_field_widget .o_favorite > a`).toHaveText("Remove from Favorites", {
        message: `the label should say "Remove from Favorites"`,
    });
});

test.tags("desktop");
test("FavoriteField in editable list view without label", async () => {
    onRpc("has_group", () => true);

    await mountView({
        resModel: "partner",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="bar" widget="boolean_favorite" nolabel="1" options="{'autosave': False}"/>
            </list>
        `,
    });
    expect(`.o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });

    // switch to edit mode
    await contains(`tbody td:not(.o_list_record_selector)`).click();
    expect(`.o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });

    // click on favorite
    await contains(`.o_data_row .o_field_widget .o_favorite > a`).click();
    expect(`.o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(0, {
        message: "should not be favorite",
    });

    // save
    await contains(`.o_list_button_save`).click();
    expect(`.o_data_row:first .o_field_widget .o_favorite > a i.fa.fa-star-o`).toHaveCount(1, {
        message: "should not be favorite",
    });
});

test.tags("desktop");
test("FavoriteField in list has a fixed width if no label", async () => {
    onRpc("has_group", () => true);
    Partner._fields.char = fields.Char();

    await mountView({
        resModel: "partner",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="bar" widget="boolean_favorite" nolabel="1"/>
                <field name="bar" widget="boolean_favorite"/>
                <field name="char"/>
            </list>
        `,
    });
    const columnWidths = queryAllProperties(".o_list_table thead th", "offsetWidth");
    const columnLabels = queryAllTexts(".o_list_table thead th");
    expect(columnWidths[1]).toBe(29);
    expect(columnLabels[1]).toBe("");
    expect(columnWidths[2]).toBeGreaterThan(29);
    expect(columnLabels[2]).toBe("Bar");
});

test("FavoriteField in kanban view with readonly attribute", async () => {
    onRpc("web_save", () => {
        expect.step("should not save");
    });
    await mountView({
        resModel: "partner",
        domain: [["id", "=", 1]],
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="bar" widget="boolean_favorite" readonly="1"/>
                    </t>
                </templates>
            </kanban>
        `,
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should be favorite",
    });
    expect(`.o_kanban_record .o_field_widget .o_favorite > a`).toHaveClass("pe-none");
    expect(`.o_kanban_record .o_field_widget`).toHaveText("");

    // click on favorite
    await contains(`.o_field_widget .o_favorite`).click();
    // expect nothing to change since its readonly
    expect(`.o_kanban_record .o_field_widget .o_favorite > a i.fa.fa-star`).toHaveCount(1, {
        message: "should remain favorite",
    });
    expect.verifySteps([]);
});
