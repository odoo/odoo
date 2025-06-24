import { describe, expect, test } from "@odoo/hoot";
import { click, edit, press, queryAllValues, queryFirst, select } from "@odoo/hoot-dom";
import { animationFrame, Deferred, runAllTimers } from "@odoo/hoot-mock";
import {
    clickSave,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    mountViewInDialog,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char({ default: "My little Foo Value" });
    bar = fields.Boolean({ default: true });
    int_field = fields.Integer();
    p = fields.One2many({
        relation: "partner",
        relation_field: "trululu",
    });
    turtles = fields.One2many({
        relation: "turtle",
        relation_field: "turtle_trululu",
    });
    trululu = fields.Many2one({ relation: "partner" });
    color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
    });
    reference = fields.Reference({
        selection: [
            ["product", "Product"],
            ["partner.type", "Partner Type"],
            ["partner", "Partner"],
        ],
    });
    reference_char = fields.Char();
    model_id = fields.Many2one({ relation: "ir.model" });

    _records = [
        {
            id: 1,
            name: "first record",
            bar: true,
            foo: "yop",
            int_field: 10,
            p: [],
            turtles: [2],
            trululu: 4,
            reference: "product,37",
        },
        {
            id: 2,
            name: "second record",
            bar: true,
            foo: "blip",
            int_field: 9,
            p: [],
            trululu: 1,
        },
        {
            id: 4,
            name: "aaa",
            bar: false,
        },
    ];
}

class Product extends models.Model {
    name = fields.Char();

    _records = [
        { id: 37, name: "xphone" },
        { id: 41, name: "xpad" },
    ];
}

class PartnerType extends models.Model {
    name = fields.Char();

    _records = [
        { id: 12, name: "gold" },
        { id: 14, name: "silver" },
    ];
}

class Turtle extends models.Model {
    name = fields.Char();
    turtle_trululu = fields.Many2one({ relation: "partner" });
    turtle_ref = fields.Reference({
        selection: [
            ["product", "Product"],
            ["partner", "Partner"],
        ],
    });
    partner_ids = fields.Many2many({ relation: "partner" });

    _records = [
        { id: 1, name: "leonardo", partner_ids: [] },
        { id: 2, name: "donatello", partner_ids: [2, 4] },
        { id: 3, name: "raphael", partner_ids: [], turtle_ref: "product,37" },
    ];
}

class IrModel extends models.Model {
    _name = "ir.model";

    name = fields.Char();
    model = fields.Char();

    _records = [
        { id: 17, name: "Partner", model: "partner" },
        { id: 20, name: "Product", model: "product" },
        { id: 21, name: "Partner Type", model: "partner.type" },
    ];
}

defineModels([Partner, Product, PartnerType, Turtle, IrModel]);

describe.current.tags("desktop");

test("ReferenceField can quick create models", async () => {
    onRpc(({ method }) => expect.step(method));

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="reference" /></form>`,
    });

    await click("select");
    await select("partner");
    await animationFrame();
    await click(".o_field_widget[name='reference'] input");
    await edit("new partner");
    await runAllTimers();
    await click(".o_field_widget[name='reference'] .o_m2o_dropdown_option_create");
    await animationFrame();

    await clickSave();

    // The name_create method should have been called
    expect.verifySteps([
        "get_views",
        "onchange",
        "web_name_search", // for the select
        "web_name_search", // for the spawned many2one
        "name_create",
        "web_save",
    ]);
});

test("ReferenceField respects no_quick_create", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="reference" options="{'no_quick_create': 1}" /></form>`,
    });

    await click("select");
    await select("partner");
    await animationFrame();
    await click(".o_field_widget[name='reference'] input");
    await edit("new partner");
    await runAllTimers();
    expect(".ui-autocomplete .o_m2o_dropdown_option").toHaveCount(1, {
        message: "Dropdown should be opened and have one item",
    });
    expect(".ui-autocomplete .o_m2o_dropdown_option:eq(0)").toHaveClass(
        "o_m2o_dropdown_option_create_edit"
    );
});

test("ReferenceField in modal readonly mode", async () => {
    Partner._records[0].p = [2];
    Partner._records[1].trululu = 1;
    Partner._records[1].reference = "product,41";

    Partner._views[["form", false]] = /* xml */ `
        <form>
            <field name="display_name" />
            <field name="reference" />
        </form>
    `;
    Partner._views[["list", false]] = /* xml */ `
        <list>
            <field name="display_name"/>
            <field name="reference" />
        </list>
    `;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form edit="0">
                <field name="reference" />
                <field name="p" />
            </form>
        `,
    });

    // Current Form
    expect(".o_field_widget[name=reference] .o_form_uri").toHaveText("xphone", {
        message: "the field reference of the form should have the right value",
    });
    expect(queryFirst(".o_data_cell")).toHaveText("second record", {
        message: "the list should have one record",
    });
    await click(".o_data_cell");
    await animationFrame();

    // In modal
    expect(".modal-lg").toHaveCount(1);
    expect(".modal-lg .o_field_widget[name=reference] .o_form_uri").toHaveText("xpad", {
        message: "The field reference in the modal should have the right value",
    });
});

test("ReferenceField in modal write mode", async () => {
    Partner._records[0].p = [2];
    Partner._records[1].trululu = 1;
    Partner._records[1].reference = "product,41";

    Partner._views[["form", false]] = /* xml */ `
        <form>
            <field name="display_name" />
            <field name="reference" />
        </form>
    `;
    Partner._views[["list", false]] = /* xml */ `
        <list>
            <field name="display_name"/>
            <field name="reference" />
        </list>
    `;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="reference" />
                <field name="p" />
            </form>
        `,
    });

    // Current Form
    expect(".o_field_widget[name=reference] option:checked").toHaveText("Product", {
        message: "The reference field's model should be Product",
    });
    expect(".o_field_widget[name=reference] .o-autocomplete--input").toHaveValue("xphone", {
        message: "The reference field's record should be xphone",
    });

    await click(".o_data_cell");
    await animationFrame();

    // In modal
    expect(".modal-lg").toHaveCount(1, { message: "there should be one modal opened" });
    expect(".modal-lg .o_field_widget[name=reference] option:checked").toHaveText("Product", {
        message: "The reference field's model should be Product",
    });
    expect(".modal-lg .o_field_widget[name=reference] .o-autocomplete--input").toHaveValue("xpad", {
        message: "The reference field's record should be xpad",
    });
});

test("reference in form view", async () => {
    expect.assertions(11);

    Product._views[["form", false]] = /* xml */ `
        <form>
            <field name="display_name" />
        </form>
    `;

    onRpc(({ args, method, model }) => {
        if (method === "get_formview_action") {
            expect(args[0]).toEqual([37], {
                message: "should call get_formview_action with correct id",
            });
            return {
                res_id: 17,
                type: "ir.actions.act_window",
                target: "current",
                res_model: "res.partner",
            };
        }
        if (method === "get_formview_id") {
            expect(args[0]).toEqual([37], {
                message: "should call get_formview_id with correct id",
            });
            return false;
        }
        if (method === "web_name_search") {
            expect(model).toBe("partner.type", {
                message: "the web_name_search should be done on the newly set model",
            });
        }
        if (method === "web_save") {
            expect(model).toBe("partner", { message: "should write on the current model" });
            expect(args).toEqual([[1], { reference: "partner.type,12" }], {
                message: "should write the correct value",
            });
        }
    });

    mockService("action", {
        doAction(action) {
            expect(action.res_id).toBe(17, {
                message: "should do a do_action with correct parameters",
            });
        },
    });

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="reference" string="custom label"/>
                    </group>
                </sheet>
            </form>
        `,
    });

    expect(".o_field_many2one_selection").toHaveCount(1, {
        message: "should contain one many2one",
    });
    expect(".o_field_widget select").toHaveValue("product", {
        message: "widget should contain one select with the model",
    });
    expect(".o_field_widget input").toHaveValue("xphone", {
        message: "widget should contain one input with the record",
    });

    expect(queryAllValues(".o_field_widget select > option")).toEqual(
        ["", "product", "partner.type", "partner"],
        {
            message: "the options should be correctly set",
        }
    );

    await click(".o_external_button");
    await animationFrame();

    expect(".o_dialog:not(.o_inactive_modal) .modal-title").toHaveText("Open: custom label", {
        message: "dialog title should display the custom string label",
    });

    await click(".o_dialog:not(.o_inactive_modal) .o_form_button_cancel");
    await animationFrame();

    await select("partner.type", { target: ".o_field_widget select" });
    await animationFrame();

    expect(".o_field_widget input").toHaveValue("", {
        message: "many2one value should be reset after model change",
    });

    await click(".o_field_widget[name=reference] input");
    await animationFrame();
    await click(".o_field_widget[name=reference] .ui-menu-item");

    await clickSave();
    expect(".o_field_widget[name=reference] input").toHaveValue("gold", {
        message: "should contain a link with the new value",
    });
});

test("Many2One 'Search more...' updates on resModel change", async () => {
    onRpc("has_group", () => true);

    Product._views[["list", false]] = /* xml */ `<list><field name="display_name"/></list>`;
    Product._views[["search", false]] = /* xml */ `<search/>`;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="reference"/></form>`,
    });

    // Selecting a relation
    await click("div.o_field_reference select.o_input");
    await select("partner.type");

    // Selecting another relation
    await click("div.o_field_reference select.o_input");
    await select("product");
    await animationFrame();

    // Opening the Search more... option
    await click("div.o_field_reference input.o_input");
    await animationFrame();
    await click("div.o_field_reference .o_m2o_dropdown_option_search_more");
    await animationFrame();

    expect(queryFirst("div.modal td.o_data_cell")).toHaveText("xphone", {
        message: "The search more should lead to the values of product.",
    });
});

test("computed reference field changed by onchange to 'False,0' value", async () => {
    expect.assertions(1);

    Partner._onChanges.bar = (obj) => {
        if (!obj.bar) {
            obj.reference_char = "False,0";
        }
    };
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            bar: false,
            reference_char: "False,0",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="bar"/>
                <field name="reference_char" widget="reference"/>
            </form>
        `,
    });

    // trigger the onchange to set a value for the reference field
    await click(".o_field_boolean input");
    await animationFrame();

    await clickSave();
});

test("interact with reference field changed by onchange", async () => {
    expect.assertions(2);

    Partner._onChanges.bar = (obj) => {
        if (!obj.bar) {
            obj.reference = "partner,1";
        }
    };
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            bar: false,
            reference: "partner,4",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="bar"/>
                <field name="reference"/>
            </form>
        `,
    });

    // trigger the onchange to set a value for the reference field
    await click(".o_field_boolean input");
    await animationFrame();

    expect(".o_field_widget[name=reference] select").toHaveValue("partner");

    // manually update reference field
    queryFirst(".o_field_widget[name=reference] input").tabIndex = 0;
    await click(".o_field_widget[name=reference] input");
    await edit("aaa");
    await runAllTimers();
    await click(".ui-autocomplete .ui-menu-item");

    // save
    await clickSave();
});

test("default_get and onchange with a reference field", async () => {
    Partner._fields.reference = fields.Reference({
        selection: [
            ["product", "Product"],
            ["partner.type", "Partner Type"],
            ["partner", "Partner"],
        ],
        default: "product,37",
    });
    Partner._onChanges.int_field = (obj) => {
        if (obj.int_field) {
            obj.reference = "partner.type," + obj.int_field;
        }
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="int_field" />
                        <field name="reference" />
                    </group>
                </sheet>
            </form>
        `,
    });

    expect(".o_field_widget[name='reference'] select").toHaveValue("product", {
        message: "reference field model should be correctly set",
    });
    expect(".o_field_widget[name='reference'] input").toHaveValue("xphone", {
        message: "reference field value should be correctly set",
    });

    // trigger onchange
    await click(".o_field_widget[name=int_field] input");
    await edit(12, { confirm: "enter" });
    await animationFrame();

    expect(".o_field_widget[name='reference'] select").toHaveValue("partner.type", {
        message: "reference field model should be correctly set",
    });
    expect(".o_field_widget[name='reference'] input").toHaveValue("gold", {
        message: "reference field value should be correctly set",
    });
});

test("default_get a reference field in a x2m", async () => {
    Partner._fields.turtles = fields.One2many({
        relation: "turtle",
        relation_field: "turtle_trululu",
        default: [[0, 0, { turtle_ref: "product,37" }]],
    });
    Turtle._views[["form", false]] = /* xml */ `
        <form>
            <field name="display_name" />
            <field name="turtle_ref" />
        </form>
    `;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <field name="turtles">
                        <list>
                            <field name="turtle_ref" />
                        </list>
                    </field>
                </sheet>
            </form>
        `,
    });

    expect('.o_field_widget[name="turtles"] .o_data_row').toHaveText("xphone", {
        message: "the default value should be correctly handled",
    });
});

test("ReferenceField on char field, reset by onchange", async () => {
    Partner._records[0].foo = "product,37";
    Partner._onChanges.int_field = (obj) => (obj.foo = "product," + obj.int_field);
    let nbNameGet = 0;
    onRpc("product", "read", ({ args }) => {
        if (args[1].length === 1 && args[1][0] === "display_name") {
            nbNameGet++;
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="int_field" />
                        <field name="foo" widget="reference" readonly="1" />
                    </group>
                </sheet>
            </form>
        `,
    });

    expect(nbNameGet).toBe(1, { message: "the first name_get should have been done" });
    expect(".o_field_widget[name=foo]").toHaveText("xphone", {
        message: "foo field should be correctly set",
    });
    // trigger onchange
    await click(".o_field_widget[name=int_field] input");
    await edit(41, { confirm: "enter" });
    await runAllTimers();
    await animationFrame();
    expect(nbNameGet).toBe(2, { message: "the second name_get should have been done" });
    expect(".o_field_widget[name=foo]").toHaveText("xpad", {
        message: "foo field should have been updated",
    });
});

test("reference and list navigation", async () => {
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list editable="bottom">
                <field name="reference" />
            </list>
        `,
    });

    // edit first row
    await click(".o_data_row .o_data_cell");
    await animationFrame();
    expect(".o_data_row [name='reference'] input").toBeFocused();

    await press("Tab");
    await animationFrame();
    expect(".o_data_row:nth-child(2) [name='reference'] select").toBeFocused();
});

test("ReferenceField with model_field option", async () => {
    Partner._records[0].reference = false;
    Partner._records[0].model_id = 20;
    Partner._records[1].name = "John Smith";
    Product._records[0].name = "Product 1";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="model_id" />
                <field name="reference" options="{'model_field': 'model_id'}" />
            </form>
        `,
    });
    expect("select").toHaveCount(0, {
        message: "the selection list of the reference field should not exist.",
    });
    expect(".o_field_widget[name='reference'] input").toHaveValue("", {
        message: "no record should be selected in the reference field",
    });

    await click(".o_field_widget[name='reference'] input");
    await edit("Product 1");
    await runAllTimers();
    await click(".ui-autocomplete .ui-menu-item:first-child");
    await animationFrame();
    expect(".o_field_widget[name='reference'] input").toHaveValue("Product 1", {
        message: "the Product 1 record should be selected in the reference field",
    });

    await click(".o_field_widget[name='model_id'] input");
    await edit("Partner");
    await runAllTimers();
    await click(".ui-autocomplete .ui-menu-item:first-child");
    await runAllTimers();
    await animationFrame();
    expect(".o_field_widget[name='reference'] input").toHaveValue("", {
        message: "no record should be selected in the reference field",
    });

    await click(".o_field_widget[name='reference'] input");
    await edit("John");
    await runAllTimers();
    await click(".ui-autocomplete .ui-menu-item:first-child");
    await animationFrame();
    expect(".o_field_widget[name='reference'] input").toHaveValue("John Smith", {
        message: "the John Smith record should be selected in the reference field",
    });
});

test("ReferenceField with model_field option (model_field not synchronized with reference)", async () => {
    // Checks that the data is not modified even though it is not synchronized.
    // Not synchronized = model_id contains a different model than the one used in reference.
    Partner._records[0].reference = "partner,1";
    Partner._records[0].model_id = 20;
    Partner._records[0].name = "John Smith";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="model_id" />
                <field name="reference" options="{'model_field': 'model_id'}" />
           </form>
        `,
    });

    expect("select").toHaveCount(0, {
        message: "the selection list of the reference field should not exist.",
    });
    expect(".o_field_widget[name='model_id'] input").toHaveValue("Product", {
        message: "the Product model should be selected in the model_id field",
    });
    expect(".o_field_widget[name='reference'] input").toHaveValue("John Smith", {
        message: "the John Smith record should be selected in the reference field",
    });
});

test("Reference field with default value in list view", async () => {
    expect.assertions(1);

    onRpc("has_group", () => true);
    onRpc(({ method, args }) => {
        if (method === "onchange") {
            return {
                value: {
                    reference: {
                        id: { id: 2, model: "partner" },
                        name: "second record",
                    },
                },
            };
        } else if (method === "web_save") {
            expect(args[1].reference).toBe("partner,2");
        }
    });
    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list string="Test" editable="top">
                <field name="reference"/>
                <field name="name"/>
            </list>
        `,
    });
    await click(".o_control_panel_main_buttons .o_list_button_add");
    await animationFrame();
    await click('.o_list_char[name="name"] input');
    await edit("Blabla");
    await runAllTimers();
    await click(".o_control_panel_main_buttons .o_list_button_save");
    await animationFrame();
});

test("ReferenceField with model_field option (tree list in form view)", async () => {
    Turtle._records[0].partner_ids = [1];
    Partner._records[0].reference = "product,41";
    Partner._records[0].model_id = 20;

    await mountView({
        type: "form",
        resModel: "turtle",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="partner_ids">
                    <list editable="bottom">
                        <field name="name" />
                        <field name="model_id" />
                        <field name="reference" options="{'model_field': 'model_id'}" class="reference_field" />
                    </list>
                </field>
            </form>
        `,
    });

    expect(".reference_field").toHaveText("xpad");

    // Select the second product without changing the model
    await click(".o_list_table .reference_field");
    await animationFrame();

    await click(".o_list_table .reference_field input");
    await animationFrame();

    // Enter to select it
    await press("Enter");
    await animationFrame();

    expect(".reference_field input").toHaveValue("xphone", {
        message: "should have selected the first product",
    });
});

test("edit a record containing a ReferenceField with model_field option (list in form view)", async () => {
    Turtle._records[0].partner_ids = [1];
    Partner._records[0].reference = "product,41";
    Partner._records[0].model_id = 20;

    await mountView({
        type: "form",
        resModel: "turtle",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="partner_ids">
                    <list editable="bottom">
                        <field name="name" />
                        <field name="model_id" />
                        <field name="reference" options='{"model_field": "model_id"}'/>
                    </list>
                </field>
            </form>
        `,
    });

    expect(".o_list_table [name='name']").toHaveText("first record");
    expect(".o_list_table [name='reference']").toHaveText("xpad");

    await click(".o_list_table .o_data_cell");
    await animationFrame();

    await click(".o_list_table [name='name'] input");
    await edit("plop");
    await animationFrame();
    await click(".o_form_view");
    await animationFrame();

    expect(".o_list_table [name='name']").toHaveText("plop");
    expect(".o_list_table [name='reference']").toHaveText("xpad");
});

test("Change model field of a ReferenceField then select an invalid value (tree list in form view)", async () => {
    Turtle._records[0].partner_ids = [1];
    Partner._records[0].reference = "product,41";
    Partner._records[0].model_id = 20;

    await mountView({
        type: "form",
        resModel: "turtle",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="partner_ids">
                    <list editable="bottom">
                        <field name="name" />
                        <field name="model_id"/>
                        <field name="reference" required="true" options="{'model_field': 'model_id'}" class="reference_field" />
                    </list>
                </field>
            </form>
        `,
    });

    expect(".reference_field").toHaveText("xpad");
    expect(".o_list_many2one").toHaveText("Product");

    await click(".o_list_table td.o_list_many2one");
    await animationFrame();
    await click(".o_list_table .o_list_many2one input");
    await animationFrame();
    //Select the "Partner" option, different from original "Product"
    await click(
        ".o_list_table .o_list_many2one .o_input_dropdown .dropdown-item:contains(Partner)"
    );
    await runAllTimers();
    await animationFrame();
    expect(".reference_field input").toHaveValue("");
    expect(".o_list_many2one input").toHaveValue("Partner");
    //Void the associated, required, "reference" field and make sure the form marks the field as required
    await click(".o_list_table .reference_field input");
    const textInput = queryFirst(".o_list_table .reference_field input");
    textInput.setSelectionRange(0, textInput.value.length);
    await click(".o_list_table .reference_field input");
    await press("Backspace");
    await click(".o_form_view_container");
    await animationFrame();

    expect(".o_list_table .reference_field.o_field_invalid").toHaveCount(1);
});

test("model selector is displayed only when it should be", async () => {
    //The model selector should be only displayed if
    //there is no hide_model=True options AND no model_field specified
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <group>
                    <field name="reference" options="{'model_field': 'model_id'}" />
                </group>
                <group>
                    <field name="reference" options="{'model_field': 'model_id', 'hide_model': True}" />
                </group>
                <group>
                    <field name="reference" options="{'hide_model': True}" />
                </group>
                <group>
                    <field name="reference" />
                </group>
            </form>
        `,
    });

    expect(".o_inner_group:eq(0) select").toHaveCount(0, {
        message:
            "the selection list of the reference field should not exist when model_field is specified.",
    });
    expect(".o_inner_group:eq(1) select").toHaveCount(0, {
        message:
            "the selection list of the reference field should not exist when model_field is specified and hide_model=True.",
    });
    expect(".o_inner_group:eq(2) select").toHaveCount(0, {
        message: "the selection list of the reference field should not exist when hide_model=True.",
    });
    expect(".o_inner_group:eq(3) select").toHaveCount(1, {
        message:
            "the selection list of the reference field should exist when hide_model=False and no model_field specified.",
    });
});

test("reference field should await fetch model before render", async () => {
    Partner._records[0].model_id = 20;

    const def = new Deferred();
    onRpc("ir.model", "read", async () => {
        await def;
    });
    mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="model_id" invisible="1"/>
                <field name="reference" options="{'model_field': 'model_id'}" />
            </form>
        `,
    });

    await animationFrame();
    expect(".o_form_view").toHaveCount(0);
    def.resolve();

    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
});

test("do not ask for display_name if field is invisible", async () => {
    expect.assertions(1);

    onRpc("web_read", ({ kwargs }) => {
        expect(kwargs.specification).toEqual({
            display_name: {},
            reference: {
                fields: {},
            },
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="reference" invisible="1"/></form>`,
    });
});

test("reference char with list view pager navigation", async () => {
    Partner._records[0].reference_char = "product,37";
    Partner._records[1].reference_char = "product,41";
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        resIds: [1, 2],
        arch: `<form edit="0"><field name="reference_char" widget="reference" string="Record"/></form>`,
    });
    expect(".o_field_reference").toHaveText("xphone");
    await click(".o_pager_next");
    await animationFrame();
    expect(".o_field_reference").toHaveText("xpad");
});
