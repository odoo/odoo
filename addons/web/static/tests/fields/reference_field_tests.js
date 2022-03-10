/** @odoo-module **/

import { setupViewRegistries } from "../views/helpers";

// WOWL remove after adapting tests
let testUtils, createView, FormView, ListView;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        // WOWL
        // eslint-disable-next-line no-undef
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
                        user_id: { string: "User", type: "many2one", relation: "user" },
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
                            user_id: 17,
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
                            user_id: 17,
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
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        partner_ids: {
                            string: "one2many partners field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "user_id",
                        },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Aline",
                            partner_ids: [1, 2],
                        },
                        {
                            id: 19,
                            name: "Christine",
                        },
                    ],
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
    });

    QUnit.module("ReferenceField");

    QUnit.skipWOWL("ReferenceField can quick create models", async function (assert) {
        assert.expect(8);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form><field name="reference"/></form>`,
            mockRPC(route, args) {
                assert.step(args.method || route);
                return this._super(...arguments);
            },
        });

        await testUtils.fields.editSelect(form.$("select"), "partner");
        await testUtils.fields.many2one.searchAndClickItem("reference", { search: "new partner" });
        await testUtils.form.clickSave(form);

        assert.verifySteps(
            [
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

        form.destroy();
    });

    QUnit.skipWOWL("ReferenceField in modal readonly mode", async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].trululu = 1;
        this.data.partner.records[1].reference = "product,41";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="reference"/>' +
                '<field name="p"/>' +
                "</form>",
            archs: {
                // make field reference readonly as the modal opens in edit mode
                "partner,false,form":
                    '<form><field name="reference" attrs="{\'readonly\': 1}"/></form>',
                "partner,false,list": '<tree><field name="display_name"/></tree>',
            },
            res_id: 1,
        });

        // Current Form
        assert.equal(
            form.$(".o_form_uri.o_field_widget[name=reference]").text(),
            "xphone",
            "the field reference of the form should have the right value"
        );

        var $cell_o2m = form.$(".o_data_cell");
        assert.equal($cell_o2m.text(), "second record", "the list should have one record");

        await testUtils.dom.click($cell_o2m);

        // In modal
        var $modal = $(".modal-lg");
        assert.equal($modal.length, 1, "there should be one modal opened");

        assert.equal(
            $modal.find(".o_form_uri.o_field_widget[name=reference]").text(),
            "xpad",
            "The field reference in the modal should have the right value"
        );

        await testUtils.dom.click($modal.find(".o_form_button_cancel"));

        form.destroy();
    });

    QUnit.skipWOWL("ReferenceField in modal write mode", async function (assert) {
        assert.expect(5);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].trululu = 1;
        this.data.partner.records[1].reference = "product,41";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="reference"/>' +
                '<field name="p"/>' +
                "</form>",
            archs: {
                "partner,false,form": '<form><field name="reference"/></form>',
                "partner,false,list": '<tree><field name="display_name"/></tree>',
            },
            res_id: 1,
        });

        // current form
        await testUtils.form.clickEdit(form);

        var $fieldRef = form.$(".o_field_widget.o_field_many2one[name=reference]");
        assert.equal(
            $fieldRef.find("option:selected").text(),
            "Product",
            "The reference field's model should be Product"
        );
        assert.equal(
            $fieldRef.find(".o_input.ui-autocomplete-input").val(),
            "xphone",
            "The reference field's record should be xphone"
        );

        await testUtils.dom.click(form.$(".o_data_cell"));

        // In modal
        var $modal = $(".modal-lg");
        assert.equal($modal.length, 1, "there should be one modal opened");

        var $fieldRefModal = $modal.find(".o_field_widget.o_field_many2one[name=reference]");

        assert.equal(
            $fieldRefModal.find("option:selected").text(),
            "Product",
            "The reference field's model should be Product"
        );
        assert.equal(
            $fieldRefModal.find(".o_input.ui-autocomplete-input").val(),
            "xpad",
            "The reference field's record should be xpad"
        );

        form.destroy();
    });

    QUnit.skipWOWL("reference in form view", async function (assert) {
        assert.expect(15);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="reference" string="custom label"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            archs: {
                "product,false,form": '<form string="Product"><field name="display_name"/></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "get_formview_action") {
                    assert.deepEqual(
                        args.args[0],
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
                if (args.method === "get_formview_id") {
                    assert.deepEqual(
                        args.args[0],
                        [37],
                        "should call get_formview_id with correct id"
                    );
                    return Promise.resolve(false);
                }
                if (args.method === "name_search") {
                    assert.strictEqual(
                        args.model,
                        "partner_type",
                        "the name_search should be done on the newly set model"
                    );
                }
                if (args.method === "write") {
                    assert.strictEqual(args.model, "partner", "should write on the current model");
                    assert.deepEqual(
                        args.args,
                        [[1], { reference: "partner_type,12" }],
                        "should write the correct value"
                    );
                }
                return this._super(route, args);
            },
        });

        testUtils.mock.intercept(form, "do_action", function (event) {
            assert.strictEqual(
                event.data.action.res_id,
                17,
                "should do a do_action with correct parameters"
            );
        });

        assert.strictEqual(
            form.$("a.o_form_uri:contains(xphone)").length,
            1,
            "should contain a link"
        );
        await testUtils.dom.click(form.$("a.o_form_uri"));

        await testUtils.form.clickEdit(form);

        assert.containsN(
            form,
            ".o_field_widget",
            2,
            "should contain two field widgets (selection and many2one)"
        );
        assert.containsOnce(form, ".o_field_many2one", "should contain one many2one");
        assert.strictEqual(
            form.$(".o_field_widget select").val(),
            "product",
            "widget should contain one select with the model"
        );
        assert.strictEqual(
            form.$(".o_field_widget input").val(),
            "xphone",
            "widget should contain one input with the record"
        );

        var options = _.map(form.$(".o_field_widget select > option"), function (el) {
            return $(el).val();
        });
        assert.deepEqual(
            options,
            ["", "product", "partner_type", "partner"],
            "the options should be correctly set"
        );

        await testUtils.dom.click(form.$(".o_external_button"));

        assert.strictEqual(
            $(".modal .modal-title").text().trim(),
            "Open: custom label",
            "dialog title should display the custom string label"
        );
        await testUtils.dom.click($(".modal .o_form_button_cancel"));

        await testUtils.fields.editSelect(form.$(".o_field_widget select"), "partner_type");
        assert.strictEqual(
            form.$(".o_field_widget input").val(),
            "",
            "many2one value should be reset after model change"
        );

        await testUtils.fields.many2one.clickOpenDropdown("reference");
        await testUtils.fields.many2one.clickHighlightedItem("reference");

        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$("a.o_form_uri:contains(gold)").length,
            1,
            "should contain a link with the new value"
        );

        form.destroy();
    });

    QUnit.skipWOWL("interact with reference field changed by onchange", async function (assert) {
        assert.expect(2);

        this.data.partner.onchanges = {
            bar: function (obj) {
                if (!obj.bar) {
                    obj.reference = "partner,1";
                }
            },
        };
        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form>
                    <field name="bar"/>
                    <field name="reference"/>
                </form>`,
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.deepEqual(args.args[0], {
                        bar: false,
                        reference: "partner,4",
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // trigger the onchange to set a value for the reference field
        await testUtils.dom.click(form.$(".o_field_boolean input"));

        assert.strictEqual(form.$(".o_field_widget[name=reference] select").val(), "partner");

        // manually update reference field
        await testUtils.fields.many2one.searchAndClickItem("reference", { search: "aaa" });

        // save
        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.skipWOWL("default_get and onchange with a reference field", async function (assert) {
        assert.expect(8);

        this.data.partner.fields.reference.default = "product,37";
        this.data.partner.onchanges = {
            int_field: function (obj) {
                if (obj.int_field) {
                    obj.reference = "partner_type," + obj.int_field;
                }
            },
        };

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="int_field"/>' +
                '<field name="reference"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            viewOptions: {
                mode: "edit",
            },
            mockRPC: function (route, args) {
                if (args.method === "name_get") {
                    assert.step(args.model);
                }
                return this._super(route, args);
            },
        });

        assert.verifySteps(["product"], "the first name_get should have been done");
        assert.strictEqual(
            form.$('.o_field_widget[name="reference"] select').val(),
            "product",
            "reference field model should be correctly set"
        );
        assert.strictEqual(
            form.$('.o_field_widget[name="reference"] input').val(),
            "xphone",
            "reference field value should be correctly set"
        );

        // trigger onchange
        await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), 12);

        assert.verifySteps(["partner_type"], "the second name_get should have been done");
        assert.strictEqual(
            form.$('.o_field_widget[name="reference"] select').val(),
            "partner_type",
            "reference field model should be correctly set"
        );
        assert.strictEqual(
            form.$('.o_field_widget[name="reference"] input').val(),
            "gold",
            "reference field value should be correctly set"
        );
        form.destroy();
    });

    QUnit.skipWOWL("default_get a reference field in a x2m", async function (assert) {
        assert.expect(1);

        this.data.partner.fields.turtles.default = [[0, false, { turtle_ref: "product,37" }]];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="turtles">' +
                "<tree>" +
                '<field name="turtle_ref"/>' +
                "</tree>" +
                "</field>" +
                "</sheet>" +
                "</form>",
            viewOptions: {
                mode: "edit",
            },
            archs: {
                "turtle,false,form":
                    '<form><field name="display_name"/><field name="turtle_ref"/></form>',
            },
        });
        assert.strictEqual(
            form.$('.o_field_one2many[name="turtles"] .o_data_row:first').text(),
            "xphone",
            "the default value should be correctly handled"
        );
        form.destroy();
    });

    QUnit.skipWOWL("ReferenceField on char field, reset by onchange", async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].foo = "product,37";
        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.foo = "product," + obj.int_field;
            },
        };

        var nbNameGet = 0;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="int_field"/>' +
                '<field name="foo" widget="reference" readonly="1"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
            viewOptions: {
                mode: "edit",
            },
            mockRPC: function (route, args) {
                if (args.model === "product" && args.method === "name_get") {
                    nbNameGet++;
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(nbNameGet, 1, "the first name_get should have been done");
        assert.strictEqual(
            form.$('a[name="foo"]').text(),
            "xphone",
            "foo field should be correctly set"
        );

        // trigger onchange
        await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), 41);

        assert.strictEqual(nbNameGet, 2, "the second name_get should have been done");
        assert.strictEqual(
            form.$('a[name="foo"]').text(),
            "xpad",
            "foo field should have been updated"
        );
        form.destroy();
    });

    QUnit.skipWOWL("reference and list navigation", async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom"><field name="reference"/></tree>',
        });

        // edit first row
        await testUtils.dom.click(list.$(".o_data_row .o_data_cell").first());
        assert.strictEqual(
            list.$('.o_data_row:eq(0) .o_field_widget[name="reference"] input')[0],
            document.activeElement,
            "input of first data row should be selected"
        );

        // press TAB to go to next line
        await testUtils.dom.triggerEvents(list.$(".o_data_row:eq(0) input:eq(1)"), [
            $.Event("keydown", {
                which: $.ui.keyCode.TAB,
                keyCode: $.ui.keyCode.TAB,
            }),
        ]);
        assert.strictEqual(
            list.$('.o_data_row:eq(1) .o_field_widget[name="reference"] select')[0],
            document.activeElement,
            "select of second data row should be selected"
        );

        list.destroy();
    });

    QUnit.skipWOWL("ReferenceField with model_field option", async function (assert) {
        assert.expect(5);
        this.data.partner.records[0].reference = false;
        this.data.partner.records[0].model_id = 20;
        this.data.partner.records[1].display_name = "John Smith";
        this.data.product.records[0].display_name = "Product 1";

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form string="Partners">
                        <field name="model_id"/>
                        <field name="reference"  options='{"model_field": "model_id"}'/>
                   </form>`,
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.containsNone(
            form.$("select"),
            "the selection list of the reference field should not exist."
        );
        assert.strictEqual(
            form.$('.o_field_many2one[name="reference"] input').val(),
            "",
            "no record should be selected in the reference field"
        );

        await testUtils.fields.editInput(
            form.$('.o_field_many2one[name="reference"] input'),
            "Product 1"
        );
        await testUtils.dom.click($(".ui-autocomplete .ui-menu-item:first-child"));
        assert.strictEqual(
            form.$('.o_field_many2one[name="reference"] input').val(),
            "Product 1",
            "the Product 1 record should be selected in the reference field"
        );

        await testUtils.fields.editInput(
            form.$('.o_field_many2one[name="model_id"] input'),
            "Partner"
        );
        await testUtils.dom.click($(".ui-autocomplete .ui-menu-item:first-child"));
        assert.strictEqual(
            form.$('.o_field_many2one[name="reference"] input').val(),
            "",
            "no record should be selected in the reference field"
        );

        await testUtils.fields.editInput(
            form.$('.o_field_many2one[name="reference"] input'),
            "John"
        );
        await testUtils.dom.click($(".ui-autocomplete .ui-menu-item:first-child"));
        assert.strictEqual(
            form.$('.o_field_many2one[name="reference"] input').val(),
            "John Smith",
            "the John Smith record should be selected in the reference field"
        );

        form.destroy();
    });

    QUnit.skipWOWL(
        "ReferenceField with model_field option (model_field not synchronized with reference)",
        async function (assert) {
            // Checks that the data is not modified even though it is not synchronized.
            // Not synchronized = model_id contains a different model than the one used in reference.
            assert.expect(5);
            this.data.partner.records[0].reference = "partner,1";
            this.data.partner.records[0].model_id = 20;
            this.data.partner.records[0].display_name = "John Smith";

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `<form string="Partners">
                        <field name="model_id"/>
                        <field name="reference"  options='{"model_field": "model_id"}'/>
                   </form>`,
                res_id: 1,
            });

            assert.containsNone(
                form.$("select"),
                "the selection list of the reference field should not exist."
            );
            assert.strictEqual(
                form.$('.o_field_widget[name="model_id"] span').text(),
                "Product",
                "the value of model_id field should be Product"
            );
            assert.strictEqual(
                form.$('.o_field_widget[name="reference"] span').text(),
                "John Smith",
                "the value of model_id field should be John Smith"
            );

            await testUtils.form.clickEdit(form);
            assert.strictEqual(
                form.$('.o_field_many2one[name="model_id"] input').val(),
                "Product",
                "the Product model should be selected in the model_id field"
            );
            assert.strictEqual(
                form.$('.o_field_many2one[name="reference"] input').val(),
                "John Smith",
                "the John Smith record should be selected in the reference field"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "ReferenceField with model_field option (tree list in form view)",
        async function (assert) {
            assert.expect(2);

            this.data.turtle.records[0].partner_ids = [1];
            this.data.partner.records[0].reference = "product,41";
            this.data.partner.records[0].model_id = 20;

            const form = await createView({
                View: FormView,
                model: "turtle",
                data: this.data,
                arch: `<form string="Turtle">
                        <field name="partner_ids">
                            <tree string="Partner" editable="bottom">
                                <field name="name"/>
                                <field name="model_id"/>
                                <field name="reference" options="{'model_field': 'model_id'}" class="reference_field"/>
                            </tree>
                        </field>
                   </form>`,
                res_id: 1,
            });

            await testUtils.form.clickEdit(form);

            assert.strictEqual(
                form.$(".reference_field").text(),
                "xpad",
                "should have the second product"
            );

            // Select the second product without changing the model
            await testUtils.dom.click($(".o_list_table .reference_field"));
            await testUtils.dom.click($(".o_list_table .reference_field input"));

            // Enter to select it
            $(".o_list_table .reference_field input").trigger(
                $.Event("keydown", {
                    keyCode: $.ui.keyCode.ENTER,
                    which: $.ui.keyCode.ENTER,
                })
            );

            await testUtils.nextTick();

            assert.strictEqual(
                form.$('.reference_field[name="reference"]').text(),
                "xphone",
                "should have selected the first product"
            );

            form.destroy();
        }
    );
});
