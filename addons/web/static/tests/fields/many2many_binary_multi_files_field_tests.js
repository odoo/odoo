/** @odoo-module **/

import { setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
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

    QUnit.module("Many2ManyBinaryMultiFilesField");

    QUnit.skip("widget many2many_binary", async function (assert) {
        assert.expect(16);
        this.data["ir.attachment"] = {
            fields: {
                name: { string: "Name", type: "char" },
                mimetype: { string: "Mimetype", type: "char" },
            },
            records: [
                {
                    id: 17,
                    name: "Marley&Me.jpg",
                    mimetype: "jpg",
                },
            ],
        };
        this.data.turtle.fields.picture_ids = {
            string: "Pictures",
            type: "many2many",
            relation: "ir.attachment",
        };
        this.data.turtle.records[0].picture_ids = [17];

        var form = await createView({
            View: FormView,
            model: "turtle",
            data: this.data,
            arch:
                '<form string="Turtles">' +
                '<group><field name="picture_ids" widget="many2many_binary" options="{\'accepted_file_extensions\': \'image/*\'}"/></group>' +
                "</form>",
            archs: {
                "ir.attachment,false,list": '<tree string="Pictures"><field name="name"/></tree>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(route);
                if (route === "/web/dataset/call_kw/ir.attachment/read") {
                    assert.deepEqual(args.args[1], ["name", "mimetype"]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(
            form,
            "div.o_field_widget.oe_fileupload",
            "there should be the attachment widget"
        );
        assert.strictEqual(
            form.$("div.o_field_widget.oe_fileupload .o_attachments").children().length,
            1,
            "there should be no attachment"
        );
        assert.containsNone(
            form,
            "div.o_field_widget.oe_fileupload .o_attach",
            "there should not be an Add button (readonly)"
        );
        assert.containsNone(
            form,
            "div.o_field_widget.oe_fileupload .o_attachment .o_attachment_delete",
            "there should not be a Delete button (readonly)"
        );

        // to edit mode
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            "div.o_field_widget.oe_fileupload .o_attach",
            "there should be an Add button"
        );
        assert.strictEqual(
            form.$("div.o_field_widget.oe_fileupload .o_attach").text().trim(),
            "Pictures",
            "the button should be correctly named"
        );
        assert.containsOnce(
            form,
            "div.o_field_widget.oe_fileupload .o_hidden_input_file form",
            "there should be a hidden form to upload attachments"
        );

        assert.strictEqual(
            form.$("input.o_input_file").attr("accept"),
            "image/*",
            'there should be an attribute "accept" on the input'
        );

        // TODO: add an attachment
        // no idea how to test this

        // delete the attachment
        await testUtils.dom.click(
            form.$("div.o_field_widget.oe_fileupload .o_attachment .o_attachment_delete")
        );

        assert.verifySteps([
            "/web/dataset/call_kw/turtle/read",
            "/web/dataset/call_kw/ir.attachment/read",
        ]);

        await testUtils.form.clickSave(form);

        assert.strictEqual(
            form.$("div.o_field_widget.oe_fileupload .o_attachments").children().length,
            0,
            "there should be no attachment"
        );

        assert.verifySteps([
            "/web/dataset/call_kw/turtle/write",
            "/web/dataset/call_kw/turtle/read",
        ]);

        form.destroy();
    });

    QUnit.skip("name_create in form dialog", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<group>" +
                '<field name="p">' +
                "<tree>" +
                '<field name="bar"/>' +
                "</tree>" +
                "<form>" +
                '<field name="product_id"/>' +
                "</form>" +
                "</field>" +
                "</group>" +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "name_create") {
                    assert.step("name_create");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
        await testUtils.owlCompatibilityExtraNextTick();
        await testUtils.fields.many2one.searchAndClickItem("product_id", {
            selector: ".modal",
            search: "new record",
        });

        assert.verifySteps(["name_create"]);

        form.destroy();
    });
});
