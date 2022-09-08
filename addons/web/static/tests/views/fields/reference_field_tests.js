/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { actionService } from "@web/webclient/actions/action_service";
import {
    click,
    editInput,
    getFixture,
    patchWithCleanup,
    triggerEvent,
    editSelect,
    clickSave,
    clickEdit,
    triggerHotkey,
    nextTick,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        bar: { string: "Bar", type: "boolean", default: true },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        qux: { string: "Qux", type: "float", digits: [16, 1] },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "trululu",
                        },
                        turtles: {
                            string: "one2many turtle field",
                            type: "one2many",
                            relation: "turtle",
                            relation_field: "turtle_trululu",
                        },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
                        timmy: { string: "pokemon", type: "many2many", relation: "partner_type" },
                        product_id: { string: "Product", type: "many2one", relation: "product" },
                        color: {
                            type: "selection",
                            selection: [
                                ["red", "Red"],
                                ["black", "Black"],
                            ],
                            default: "red",
                            string: "Color",
                        },
                        date: { string: "Some Date", type: "date" },
                        datetime: { string: "Datetime Field", type: "datetime" },
                        reference: {
                            string: "Reference Field",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner_type", "Partner Type"],
                                ["partner", "Partner"],
                            ],
                        },
                        model_id: { string: "Model", type: "many2one", relation: "ir.model" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44,
                            p: [],
                            turtles: [2],
                            timmy: [],
                            trululu: 4,
                            reference: "product,37",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 9,
                            qux: 13,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            product_id: 37,
                            date: "2017-01-25",
                            datetime: "2016-12-12 10:55:05",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            bar: false,
                        },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char" },
                        color: { string: "Color index", type: "integer" },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                turtle: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        turtle_foo: { string: "Foo", type: "char" },
                        turtle_bar: { string: "Bar", type: "boolean", default: true },
                        turtle_int: { string: "int", type: "integer", sortable: true },
                        turtle_description: { string: "Description", type: "text" },
                        turtle_trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                        },
                        turtle_ref: {
                            string: "Reference",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner", "Partner"],
                            ],
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            required: true,
                        },
                        partner_ids: { string: "Partner", type: "many2many", relation: "partner" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "leonardo",
                            turtle_bar: true,
                            turtle_foo: "yop",
                            partner_ids: [],
                        },
                        {
                            id: 2,
                            display_name: "donatello",
                            turtle_bar: true,
                            turtle_foo: "blip",
                            turtle_int: 9,
                            partner_ids: [2, 4],
                        },
                        {
                            id: 3,
                            display_name: "raphael",
                            product_id: 37,
                            turtle_bar: false,
                            turtle_foo: "kawa",
                            turtle_int: 21,
                            partner_ids: [],
                            turtle_ref: "product,37",
                        },
                    ],
                    onchanges: {},
                },
                "ir.model": {
                    fields: {
                        model: { string: "Model", type: "char" },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Partner",
                            model: "partner",
                        },
                        {
                            id: 20,
                            name: "Product",
                            model: "product",
                        },
                        {
                            id: 21,
                            name: "Partner Type",
                            model: "partner_type",
                        },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("ReferenceField");

    QUnit.test("ReferenceField can quick create models", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="reference" /></form>',
            mockRPC(route, { method }) {
                assert.step(method || route);
            },
        });

        await editSelect(target, "select", "partner");

        await click(target, ".o_field_widget[name='reference'] input");
        await editInput(target, ".o_field_widget[name='reference'] input", "new partner");
        await click(target, ".o_field_widget[name='reference'] .o_m2o_dropdown_option_create");

        await click(target, ".o_form_button_save");

        assert.verifySteps(
            [
                "get_views",
                "onchange",
                "name_search", // for the select
                "name_search", // for the spawned many2one
                "name_create",
                "create",
                "read",
                "name_get",
            ],
            "The name_create method should have been called"
        );
    });

    QUnit.test("ReferenceField in modal readonly mode", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].trululu = 1;
        serverData.models.partner.records[1].reference = "product,41";

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name" />
                    <field name="reference" />
                </form>`,
            "partner,false,list": `
                <tree>
                    <field name="display_name"/>
                    <field name="reference" />
                </tree>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="reference" />
                    <field name="p" />
                </form>`,
        });

        // Current Form
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=reference] .o_form_uri").textContent,
            "xphone",
            "the field reference of the form should have the right value"
        );

        const cell = target.querySelector(".o_data_cell");
        assert.strictEqual(cell.textContent, "second record", "the list should have one record");
        await click(cell);

        // In modal
        assert.containsOnce(document.body, ".modal-lg");
        assert.strictEqual(
            document.body.querySelector(".modal-lg .o_field_widget[name=reference] .o_form_uri")
                .textContent,
            "xpad",
            "The field reference in the modal should have the right value"
        );

        await click(document.body, ".modal .o_form_button_cancel");
    });

    QUnit.test("ReferenceField in modal write mode", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].trululu = 1;
        serverData.models.partner.records[1].reference = "product,41";

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name" />
                    <field name="reference" />
                </form>`,
            "partner,false,list": `
                <tree>
                    <field name="display_name"/>
                    <field name="reference" />
                </tree>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="reference" />
                    <field name="p" />
                </form>`,
        });

        // current form
        await click(target, ".o_form_button_edit");

        let fieldRef = target.querySelector(".o_field_widget[name=reference]");
        assert.strictEqual(
            fieldRef.querySelector("option:checked").textContent,
            "Product",
            "The reference field's model should be Product"
        );
        assert.strictEqual(
            fieldRef.querySelector(".o-autocomplete--input").value,
            "xphone",
            "The reference field's record should be xphone"
        );

        await click(target.querySelector(".o_data_cell"));

        // In modal
        assert.containsOnce(document.body, ".modal-lg", "there should be one modal opened");

        fieldRef = document.querySelector(".modal-lg .o_field_widget[name=reference]");

        assert.strictEqual(
            fieldRef.querySelector("option:checked").textContent,
            "Product",
            "The reference field's model should be Product"
        );
        assert.strictEqual(
            fieldRef.querySelector(".o-autocomplete--input").value,
            "xpad",
            "The reference field's record should be xpad"
        );
    });

    QUnit.test("reference in form view", async function (assert) {
        assert.expect(14);

        serverData.views = {
            "product,false,form": `
                <form>
                    <field name="display_name" />
                </form>`,
        };

        patchWithCleanup(actionService, {
            start() {
                const service = this._super(...arguments);
                return {
                    ...service,
                    doAction(action) {
                        assert.strictEqual(
                            action.res_id,
                            17,
                            "should do a do_action with correct parameters"
                        );
                    },
                };
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="reference" string="custom label" />
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, { args, method, model }) {
                if (method === "get_formview_action") {
                    assert.deepEqual(
                        args[0],
                        [37],
                        "should call get_formview_action with correct id"
                    );
                    return Promise.resolve({
                        res_id: 17,
                        type: "ir.actions.act_window",
                        target: "current",
                        res_model: "res.partner",
                    });
                }
                if (method === "get_formview_id") {
                    assert.deepEqual(args[0], [37], "should call get_formview_id with correct id");
                    return Promise.resolve(false);
                }
                if (method === "name_search") {
                    assert.strictEqual(
                        model,
                        "partner_type",
                        "the name_search should be done on the newly set model"
                    );
                }
                if (method === "write") {
                    assert.strictEqual(model, "partner", "should write on the current model");
                    assert.deepEqual(
                        args,
                        [[1], { reference: "partner_type,12" }],
                        "should write the correct value"
                    );
                }
            },
        });

        assert.strictEqual(
            target.querySelector("a.o_form_uri").textContent,
            "xphone",
            "should contain a link"
        );
        await click(target, "a.o_form_uri");

        await click(target, ".o_form_button_edit");

        assert.containsOnce(target, ".o_field_many2one_selection", "should contain one many2one");
        assert.strictEqual(
            target.querySelector(".o_field_widget select").value,
            "product",
            "widget should contain one select with the model"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "xphone",
            "widget should contain one input with the record"
        );

        const options = [...target.querySelectorAll(".o_field_widget select > option")].map(
            (el) => el.value
        );
        assert.deepEqual(
            options,
            ["", "product", "partner_type", "partner"],
            "the options should be correctly set"
        );

        await click(target, ".o_external_button");

        assert.strictEqual(
            target.querySelector(".modal .modal-title").textContent.trim(),
            "Open: custom label",
            "dialog title should display the custom string label"
        );
        await click(target, ".modal .o_form_button_cancel");

        await editSelect(target, ".o_field_widget select", "partner_type");
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "",
            "many2one value should be reset after model change"
        );

        await click(target, ".o_field_widget[name=reference] input");
        await click(target.querySelector(".o_field_widget[name=reference] .ui-menu-item"));

        await clickSave(target);
        assert.strictEqual(
            target.querySelector("a.o_form_uri").textContent,
            "gold",
            "should contain a link with the new value"
        );
    });

    QUnit.test("interact with reference field changed by onchange", async function (assert) {
        assert.expect(2);

        serverData.models.partner.onchanges = {
            bar(obj) {
                if (!obj.bar) {
                    obj.reference = "partner,1";
                }
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="reference"/>
                </form>`,
            mockRPC(route, { args, method }) {
                if (method === "create") {
                    assert.deepEqual(args[0], {
                        bar: false,
                        reference: "partner,4",
                    });
                }
            },
        });

        // trigger the onchange to set a value for the reference field
        await click(target, ".o_field_boolean input");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=reference] select").value,
            "partner"
        );

        // manually update reference field
        await editInput(target, ".o_field_widget[name=reference] input", "aaa");
        await click(target.querySelector(".ui-autocomplete .ui-menu-item"));

        // save
        await click(target, ".o_form_button_save");
    });

    QUnit.test("default_get and onchange with a reference field", async function (assert) {
        serverData.models.partner.fields.reference.default = "product,37";
        serverData.models.partner.onchanges = {
            int_field(obj) {
                if (obj.int_field) {
                    obj.reference = "partner_type," + obj.int_field;
                }
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="int_field" />
                            <field name="reference" />
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, { method, model }) {
                if (method === "name_get") {
                    assert.step(model);
                }
            },
        });

        assert.verifySteps(["product"], "the first name_get should have been done");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='reference'] select").value,
            "product",
            "reference field model should be correctly set"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='reference'] input").value,
            "xphone",
            "reference field value should be correctly set"
        );

        // trigger onchange
        await editInput(target, ".o_field_widget[name=int_field] input", 12);

        assert.verifySteps(["partner_type"], "the second name_get should have been done");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='reference'] select").value,
            "partner_type",
            "reference field model should be correctly set"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='reference'] input").value,
            "gold",
            "reference field value should be correctly set"
        );
    });

    QUnit.test("default_get a reference field in a x2m", async function (assert) {
        serverData.models.partner.fields.turtles.default = [
            [0, false, { turtle_ref: "product,37" }],
        ];
        serverData.views = {
            "turtle,false,form": `
                <form>
                    <field name="display_name" />
                    <field name="turtle_ref" />
                </form>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles">
                            <tree>
                                <field name="turtle_ref" />
                            </tree>
                        </field>
                    </sheet>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector('.o_field_widget[name="turtles"] .o_data_row').textContent,
            "xphone",
            "the default value should be correctly handled"
        );
    });

    QUnit.test("ReferenceField on char field, reset by onchange", async function (assert) {
        serverData.models.partner.records[0].foo = "product,37";
        serverData.models.partner.onchanges = {
            int_field(obj) {
                obj.foo = "product," + obj.int_field;
            },
        };

        let nbNameGet = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="int_field" />
                            <field name="foo" widget="reference" readonly="1" />
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, { model, method }) {
                if (model === "product" && method === "name_get") {
                    nbNameGet++;
                }
            },
        });

        await click(target, ".o_form_button_edit");

        assert.strictEqual(nbNameGet, 1, "the first name_get should have been done");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo]").textContent,
            "xphone",
            "foo field should be correctly set"
        );

        // trigger onchange
        await editInput(target, ".o_field_widget[name=int_field] input", 41);

        assert.strictEqual(nbNameGet, 2, "the second name_get should have been done");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo]").textContent,
            "xpad",
            "foo field should have been updated"
        );
    });

    QUnit.test("reference and list navigation", async function (assert) {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="reference" />
                </tree>`,
        });

        // edit first row
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row [name='reference'] input")
        );

        triggerHotkey("Tab");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_data_row:nth-child(2) [name='reference'] select")
        );
    });

    QUnit.test("ReferenceField with model_field option", async function (assert) {
        serverData.models.partner.records[0].reference = false;
        serverData.models.partner.records[0].model_id = 20;
        serverData.models.partner.records[1].display_name = "John Smith";
        serverData.models.product.records[0].display_name = "Product 1";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="model_id" />
                    <field name="reference" options="{'model_field': 'model_id'}" />
                </form>`,
        });

        await click(target, ".o_form_button_edit");

        assert.containsNone(
            target,
            "select",
            "the selection list of the reference field should not exist."
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='reference'] input").value,
            "",
            "no record should be selected in the reference field"
        );

        await editInput(target, ".o_field_widget[name='reference'] input", "Product 1");
        await click(target, ".ui-autocomplete .ui-menu-item:first-child");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='reference'] input").value,
            "Product 1",
            "the Product 1 record should be selected in the reference field"
        );

        await editInput(target, ".o_field_widget[name='model_id'] input", "Partner");
        await click(target, ".ui-autocomplete .ui-menu-item:first-child");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='reference'] input").value,
            "",
            "no record should be selected in the reference field"
        );

        await editInput(target, ".o_field_widget[name='reference'] input", "John");
        await click(target, ".ui-autocomplete .ui-menu-item:first-child");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='reference'] input").value,
            "John Smith",
            "the John Smith record should be selected in the reference field"
        );
    });

    QUnit.test(
        "ReferenceField with model_field option (model_field not synchronized with reference)",
        async function (assert) {
            // Checks that the data is not modified even though it is not synchronized.
            // Not synchronized = model_id contains a different model than the one used in reference.
            serverData.models.partner.records[0].reference = "partner,1";
            serverData.models.partner.records[0].model_id = 20;
            serverData.models.partner.records[0].display_name = "John Smith";

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="model_id" />
                        <field name="reference" options="{'model_field': 'model_id'}" />
                   </form>`,
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget[name='model_id'] span").textContent,
                "Product",
                "the value of model_id field should be Product"
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='reference'] span").textContent,
                "John Smith",
                "the value of model_id field should be John Smith"
            );

            await click(target, ".o_form_button_edit");
            assert.containsNone(
                target,
                "select",
                "the selection list of the reference field should not exist."
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='model_id'] input").value,
                "Product",
                "the Product model should be selected in the model_id field"
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='reference'] input").value,
                "John Smith",
                "the John Smith record should be selected in the reference field"
            );
        }
    );

    QUnit.test(
        "ReferenceField with model_field option (tree list in form view)",
        async function (assert) {
            serverData.models.turtle.records[0].partner_ids = [1];
            serverData.models.partner.records[0].reference = "product,41";
            serverData.models.partner.records[0].model_id = 20;

            await makeView({
                type: "form",
                resModel: "turtle",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="partner_ids">
                            <tree editable="bottom">
                                <field name="name" />
                                <field name="model_id" />
                                <field name="reference" options="{'model_field': 'model_id'}" class="reference_field" />
                            </tree>
                        </field>
                   </form>`,
            });

            await clickEdit(target);

            assert.strictEqual(target.querySelector(".reference_field").textContent, "xpad");

            // Select the second product without changing the model
            await click(target, ".o_list_table .reference_field");
            await click(target, ".o_list_table .reference_field input");

            // Enter to select it
            await triggerEvent(target, ".o_list_table .reference_field input", "keydown", {
                key: "Enter",
            });

            assert.strictEqual(
                target.querySelector(".reference_field input").value,
                "xphone",
                "should have selected the first product"
            );
        }
    );

    QUnit.test(
        "edit a record containing a ReferenceField with model_field option (list in form view)",
        async function (assert) {
            serverData.models.turtle.records[0].partner_ids = [1];
            serverData.models.partner.records[0].reference = "product,41";
            serverData.models.partner.records[0].model_id = 20;

            await makeView({
                type: "form",
                resModel: "turtle",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="partner_ids">
                            <tree editable="bottom">
                                <field name="name" />
                                <field name="model_id" />
                                <field name="reference" options='{"model_field": "model_id"}'/>
                            </tree>
                        </field>
                   </form>`,
            });
            assert.strictEqual(
                target.querySelector(".o_list_table [name='name']").textContent,
                "name"
            );
            assert.strictEqual(
                target.querySelector(".o_list_table [name='reference']").textContent,
                "xpad"
            );

            await clickEdit(target);
            await click(target.querySelector(".o_list_table .o_data_cell"));
            await editInput(target, ".o_list_table [name='name'] input", "plop");
            await click(target, ".o_form_view");
            assert.strictEqual(
                target.querySelector(".o_list_table [name='name']").textContent,
                "plop"
            );
            assert.strictEqual(
                target.querySelector(".o_list_table [name='reference']").textContent,
                "xpad"
            );
        }
    );

    QUnit.test("model selector is displayed only when it should be", async function (assert) {
        //The model selector should be only displayed if
        //there is no hide_model=True options AND no model_field specified
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
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
                </form>`,
        });

        await click(target, ".o_form_button_edit");

        const groups = target.querySelectorAll(".o_group");

        assert.containsNone(
            groups[0],
            "select",
            "the selection list of the reference field should not exist when model_field is specified."
        );
        assert.containsNone(
            groups[1],
            "select",
            "the selection list of the reference field should not exist when model_field is specified and hide_model=True."
        );
        assert.containsNone(
            groups[2],
            "select",
            "the selection list of the reference field should not exist when hide_model=True."
        );
        assert.containsOnce(
            groups[3],
            "select",
            "the selection list of the reference field should exist when hide_model=False and no model_field specified."
        );
    });
});
