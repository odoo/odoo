import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";

import {
    clickFieldDropdownItem,
    clickSave,
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
    selectFieldDropdownItem,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    model = fields.Char({
        string: "Resource Model",
    });
    res_id = fields.Many2oneReference({
        string: "Resource Id",
        model_field: "model",
        relation: "partner.type",
    });

    _records = [
        { id: 1, model: "partner.type", res_id: 10 },
        { id: 2, res_id: false },
    ];
}

class PartnerType extends models.Model {
    id = fields.Integer();
    name = fields.Char();

    _records = [
        { id: 10, name: "gold" },
        { id: 14, name: "silver" },
    ];
}

defineModels([Partner, PartnerType]);

onRpc("has_group", () => true);

test("Many2OneReferenceField in form view", async () => {
    mockService("action", {
        doAction() {
            expect.step("doAction");
        },
    });

    onRpc("get_formview_action", ({ model, args }) => {
        expect.step(`opening ${model} ${args[0][0]}`);
        return false;
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="model" invisible="1"/>
                <field name="res_id"/>
            </form>`,
    });
    expect(".o_field_widget input").toHaveValue("gold");
    expect(".o_field_widget[name=res_id] .o_external_button").toHaveCount(1);

    await contains(".o_field_widget[name=res_id] .o_external_button", { visible: false }).click();
    expect.verifySteps(["opening partner.type 10", "doAction"]);
});

test("Many2OneReferenceField in list view", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        resId: 1,
        arch: `
            <list>
                <field name="model" column_invisible="1"/>
                <field name="res_id"/>
            </list>`,
    });

    expect(queryAllTexts(".o_data_cell")).toEqual(["gold", ""]);
});

test("Many2OneReferenceField with no_open option", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="model" invisible="1"/>
                <field name="res_id" options="{'no_open': 1}"/>
            </form>`,
    });

    expect(".o_field_widget input").toHaveValue("gold");
    expect(".o_field_widget[name=res_id] .o_external_button").toHaveCount(0);
});

test.tags("desktop")("Many2OneReferenceField edition: unset", async () => {
    expect.assertions(4);

    onRpc("web_save", ({ args }) => {
        expect(args).toEqual([[2], { model: "partner.type", res_id: 14 }]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `
            <form>
                <field name="model"/>
                <field name="res_id"/>
            </form>`,
    });

    expect(".o_field_widget[name=res_id] input").toHaveCount(0);

    await contains(".o_field_widget[name=model] input").edit("partner.type");

    expect(".o_field_widget[name=res_id] input").toHaveCount(1);

    await selectFieldDropdownItem("res_id", "silver");
    expect(".o_field_widget[name=res_id] input").toHaveValue("silver");

    await clickSave();
});

test.tags("desktop")("Many2OneReferenceField set value with search more", async () => {
    PartnerType._views = {
        list: `<list><field name="name"/></list>`,
        search: `<search/>`,
    };
    PartnerType._records = [
        { id: 1, name: "type 1" },
        { id: 2, name: "type 2" },
        { id: 3, name: "type 3" },
        { id: 4, name: "type 4" },
        { id: 5, name: "type 5" },
        { id: 6, name: "type 6" },
        { id: 7, name: "type 7" },
        { id: 8, name: "type 8" },
        { id: 9, name: "type 9" },
    ];
    Partner._records[0].res_id = 1;
    onRpc(({ method }) => {
        expect.step(method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="model" invisible="1"/>
                <field name="res_id"/>
            </form>`,
    });

    expect(".o_field_widget input").toHaveValue("type 1");
    await selectFieldDropdownItem("res_id", "Search More...");
    expect(".o_dialog .o_list_view").toHaveCount(1);
    await contains(".o_data_row .o_data_cell:eq(6)").click();
    expect(".o_dialog .o_list_view").toHaveCount(0);
    expect(".o_field_widget input").toHaveValue("type 7");
    expect.verifySteps([
        "get_views", // form view
        "web_read", // partner id 1
        "name_search", // many2one
        "get_views", // Search More...
        "web_search_read", // SelectCreateDialog
        "has_group",
        "web_read", // read selected value
    ]);
});

test.tags("desktop")("Many2OneReferenceField: quick create a value", async () => {
    onRpc(({ method }) => {
        expect.step(method);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="model" invisible="1"/>
                    <field name="res_id"/>
                </form>`,
    });

    expect(".o_field_widget input").toHaveValue("gold");

    await contains(".o_field_widget[name='res_id'] input").edit("new value", { confirm: false });
    await runAllTimers();
    expect(
        ".o_field_widget[name='res_id'] .dropdown-menu .o_m2o_dropdown_option_create"
    ).toHaveCount(1);
    await clickFieldDropdownItem("res_id", `Create "new value"`);
    expect(".o_field_widget input").toHaveValue("new value");
    expect.verifySteps(["get_views", "web_read", "name_search", "name_create"]);
});

test("Many2OneReferenceField with no_create option", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="model" invisible="1"/>
                <field name="res_id" options="{'no_create': 1}"/>
            </form>`,
    });

    await contains(".o_field_widget[name='res_id'] input").edit("new value", { confirm: false });
    await runAllTimers();
    expect(
        ".o_field_widget[name='res_id'] .dropdown-menu .o_m2o_dropdown_option_create"
    ).toHaveCount(0);
});
