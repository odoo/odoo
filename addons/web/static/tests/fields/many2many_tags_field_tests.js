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

    QUnit.module("Many2ManyTagsField");

    QUnit.skipWOWL("fieldmany2many tags with and without color", async function (assert) {
        assert.expect(5);

        this.data.partner.fields.partner_ids = {
            string: "Partner",
            type: "many2many",
            relation: "partner",
        };
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="partner_ids" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                '<field name="timmy" widget="many2many_tags"/>' +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "read" && args.model === "partner_type") {
                    assert.deepEqual(
                        args.args,
                        [[12], ["display_name"]],
                        "should not read any color field"
                    );
                } else if (args.method === "read" && args.model === "partner") {
                    assert.deepEqual(
                        args.args,
                        [[1], ["display_name", "color"]],
                        "should read color field"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        // add a tag on field partner_ids
        await testUtils.fields.many2one.clickOpenDropdown("partner_ids");
        await testUtils.fields.many2one.clickHighlightedItem("partner_ids");

        // add a tag on field timmy
        await testUtils.fields.many2one.clickOpenDropdown("timmy");
        var $input = form.$('.o_field_many2manytags[name="timmy"] input');
        assert.strictEqual(
            $input.autocomplete("widget").find("li").length,
            3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')"
        );
        await testUtils.fields.many2one.clickHighlightedItem("timmy");
        assert.containsOnce(
            form,
            '.o_field_many2manytags[name="timmy"] .badge',
            "should contain 1 tag"
        );
        assert.containsOnce(
            form,
            '.o_field_many2manytags[name="timmy"] .badge:contains("gold")',
            "should contain newly added tag 'gold'"
        );

        form.destroy();
    });

    QUnit.skipWOWL(
        "fieldmany2many tags with color: rendering and edition",
        async function (assert) {
            assert.expect(28);

            this.data.partner.records[0].timmy = [12, 14];
            this.data.partner_type.records.push({ id: 13, display_name: "red", color: 8 });
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<field name=\"timmy\" widget=\"many2many_tags\" options=\"{'color_field': 'color', 'no_create_edit': True}\"/>" +
                    "</form>",
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === "/web/dataset/call_kw/partner/write") {
                        var commands = args.args[1].timmy;
                        assert.strictEqual(commands.length, 1, "should have generated one command");
                        assert.strictEqual(
                            commands[0][0],
                            6,
                            "generated command should be REPLACE WITH"
                        );
                        assert.ok(
                            _.isEqual(_.sortBy(commands[0][2], _.identity.bind(_)), [12, 13]),
                            "new value should be [12, 13]"
                        );
                    }
                    if (args.method === "read" && args.model === "partner_type") {
                        assert.deepEqual(
                            args.args[1],
                            ["display_name", "color"],
                            "should read the color field"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });
            assert.containsN(
                form,
                ".o_field_many2manytags .badge .dropdown-toggle",
                2,
                "should contain 2 tags"
            );
            assert.ok(
                form.$(".badge .dropdown-toggle:contains(gold)").length,
                "should have fetched and rendered gold partner tag"
            );
            assert.ok(
                form.$(".badge .dropdown-toggle:contains(silver)").length,
                "should have fetched and rendered silver partner tag"
            );
            assert.strictEqual(
                form.$(".badge:first()").data("color"),
                2,
                "should have correctly fetched the color"
            );

            await testUtils.form.clickEdit(form);

            assert.containsN(
                form,
                ".o_field_many2manytags .badge .dropdown-toggle",
                2,
                "should still contain 2 tags in edit mode"
            );
            assert.ok(
                form.$(".o_tag_color_2 .o_badge_text:contains(gold)").length,
                'first tag should still contain "gold" and be color 2 in edit mode'
            );
            assert.containsN(
                form,
                ".o_field_many2manytags .o_delete",
                2,
                "tags should contain a delete button"
            );

            // add an other existing tag
            var $input = form.$(".o_field_many2manytags input");
            await testUtils.fields.many2one.clickOpenDropdown("timmy");
            assert.strictEqual(
                $input.autocomplete("widget").find("li").length,
                2,
                "autocomplete dropdown should have 2 entry"
            );
            assert.strictEqual(
                $input.autocomplete("widget").find('li a:contains("red")').length,
                1,
                "autocomplete dropdown should contain 'red'"
            );
            await testUtils.fields.many2one.clickHighlightedItem("timmy");
            assert.containsN(
                form,
                ".o_field_many2manytags .badge .dropdown-toggle",
                3,
                "should contain 3 tags"
            );
            assert.ok(
                form.$('.o_field_many2manytags .badge .dropdown-toggle:contains("red")').length,
                "should contain newly added tag 'red'"
            );
            assert.ok(
                form.$(
                    '.o_field_many2manytags .badge[data-color=8] .dropdown-toggle:contains("red")'
                ).length,
                "should have fetched the color of added tag"
            );

            // remove tag with id 14
            await testUtils.dom.click(
                form.$(".o_field_many2manytags .badge[data-id=14] .o_delete")
            );
            assert.containsN(
                form,
                ".o_field_many2manytags .badge .dropdown-toggle",
                2,
                "should contain 2 tags"
            );
            assert.ok(
                !form.$('.o_field_many2manytags .badge .dropdown-toggle:contains("silver")').length,
                "should not contain tag 'silver' anymore"
            );

            // save the record (should do the write RPC with the correct commands)
            await testUtils.form.clickSave(form);

            // checkbox 'Hide in Kanban'
            $input = form.$(".o_field_many2manytags .badge[data-id=13] .dropdown-toggle"); // selects 'red' tag
            await testUtils.dom.click($input);
            var $checkBox = form.$(
                ".o_field_many2manytags .badge[data-id=13] .custom-checkbox input"
            );
            assert.strictEqual(
                $checkBox.length,
                1,
                "should have a checkbox in the colorpicker dropdown menu"
            );
            assert.notOk(
                $checkBox.is(":checked"),
                "should have unticked checkbox in colorpicker dropdown menu"
            );

            await testUtils.fields.editAndTrigger($checkBox, null, ["mouseenter", "mousedown"]);

            $input = form.$(".o_field_many2manytags .badge[data-id=13] .dropdown-toggle"); // refresh
            await testUtils.dom.click($input);
            $checkBox = form.$(".o_field_many2manytags .badge[data-id=13] .custom-checkbox input"); // refresh
            assert.equal(
                $input.parent().data("color"),
                "0",
                "should become transparent when toggling on checkbox"
            );
            assert.ok(
                $checkBox.is(":checked"),
                "should have a ticked checkbox in colorpicker dropdown menu after mousedown"
            );

            await testUtils.fields.editAndTrigger($checkBox, null, ["mouseenter", "mousedown"]);

            $input = form.$(".o_field_many2manytags .badge[data-id=13] .dropdown-toggle"); // refresh
            await testUtils.dom.click($input);
            $checkBox = form.$(".o_field_many2manytags .badge[data-id=13] .custom-checkbox input"); // refresh
            assert.equal(
                $input.parent().data("color"),
                "8",
                "should revert to old color when toggling off checkbox"
            );
            assert.notOk(
                $checkBox.is(":checked"),
                "should have an unticked checkbox in colorpicker dropdown menu after 2nd click"
            );

            // TODO: it would be nice to test the behaviors of the autocomplete dropdown
            // (like refining the research, creating new tags...), but ui-autocomplete
            // makes it difficult to test
            form.destroy();
        }
    );

    QUnit.skipWOWL("fieldmany2many tags in tree view", async function (assert) {
        assert.expect(3);

        this.data.partner.records[0].timmy = [12, 14];
        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch:
                '<tree string="Partners">' +
                '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                "</tree>",
        });
        assert.containsN(list, ".o_field_many2manytags .badge", 2, "there should be 2 tags");
        assert.containsNone(list, ".badge.dropdown-toggle", "the tags should not be dropdowns");

        testUtils.mock.intercept(list, "switch_view", function (event) {
            assert.strictEqual(event.data.view_type, "form", "should switch to form view");
        });
        // click on the tag: should do nothing and open the form view
        testUtils.dom.click(list.$(".o_field_many2manytags .badge:first"));

        list.destroy();
    });

    QUnit.skipWOWL("fieldmany2many tags view a domain", async function (assert) {
        assert.expect(7);

        this.data.partner.fields.timmy.domain = [["id", "<", 50]];
        this.data.partner.records[0].timmy = [12];
        this.data.partner_type.records.push({ id: 99, display_name: "red", color: 8 });

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="timmy" widget="many2many_tags" options="{\'no_create_edit\': True}"/>' +
                "</form>",
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "name_search") {
                    assert.deepEqual(
                        args.kwargs.args,
                        [
                            ["id", "<", 50],
                            ["id", "not in", [12]],
                        ],
                        "domain sent to name_search should be correct"
                    );
                    return Promise.resolve([[14, "silver"]]);
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.containsOnce(form, ".o_field_many2manytags .badge", "should contain 1 tag");
        assert.ok(
            form.$(".badge:contains(gold)").length,
            "should have fetched and rendered gold partner tag"
        );

        await testUtils.form.clickEdit(form);

        // add an other existing tag
        var $input = form.$(".o_field_many2manytags input");
        await testUtils.fields.many2one.clickOpenDropdown("timmy");
        assert.strictEqual(
            $input.autocomplete("widget").find("li").length,
            2,
            "autocomplete dropdown should have 2 entry"
        );
        assert.strictEqual(
            $input.autocomplete("widget").find('li a:contains("silver")').length,
            1,
            "autocomplete dropdown should contain 'silver'"
        );
        await testUtils.fields.many2one.clickHighlightedItem("timmy");
        assert.containsN(form, ".o_field_many2manytags .badge", 2, "should contain 2 tags");
        assert.ok(
            form.$('.o_field_many2manytags .badge:contains("silver")').length,
            "should contain newly added tag 'silver'"
        );

        form.destroy();
    });

    QUnit.skipWOWL("fieldmany2many tags in a new record", async function (assert) {
        assert.expect(7);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="timmy" widget="many2many_tags"/>' +
                "</form>",
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/partner/create") {
                    var commands = args.args[0].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(
                        commands[0][0],
                        6,
                        "generated command should be REPLACE WITH"
                    );
                    assert.ok(_.isEqual(commands[0][2], [12]), "new value should be [12]");
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.hasClass(form.$(".o_form_view"), "o_form_editable", "form should be in edit mode");

        await testUtils.fields.many2one.clickOpenDropdown("timmy");
        assert.strictEqual(
            form.$(".o_field_many2manytags input").autocomplete("widget").find("li").length,
            3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')"
        );
        await testUtils.fields.many2one.clickHighlightedItem("timmy");

        assert.containsOnce(form, ".o_field_many2manytags .badge", "should contain 1 tag");
        assert.ok(
            form.$('.o_field_many2manytags .badge:contains("gold")').length,
            "should contain newly added tag 'gold'"
        );

        // save the record (should do the write RPC with the correct commands)
        await testUtils.form.clickSave(form);
        form.destroy();
    });

    QUnit.skipWOWL("fieldmany2many tags: update color", async function (assert) {
        assert.expect(5);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records[0].color = 0;

        var color;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[1], { color: color }, "shoud write the new color");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        // First checks that default color 0 is rendered as 0 color
        assert.ok(
            form.$(".badge.dropdown:first()").is(".o_tag_color_0"),
            "first tag color should be 0"
        );

        // Update the color in readonly
        color = 1;
        await testUtils.dom.click(form.$(".badge:first() .dropdown-toggle"));
        await testUtils.dom.triggerEvents($('.o_colorpicker a[data-color="' + color + '"]'), [
            "mousedown",
        ]);
        await testUtils.nextTick();
        assert.strictEqual(
            form.$(".badge:first()").data("color"),
            color,
            "should have correctly updated the color (in readonly)"
        );

        // Update the color in edit
        color = 6;
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$(".badge:first() .dropdown-toggle"));
        await testUtils.dom.triggerEvents($('.o_colorpicker a[data-color="' + color + '"]'), [
            "mousedown",
        ]); // choose color 6
        await testUtils.nextTick();
        assert.strictEqual(
            form.$(".badge:first()").data("color"),
            color,
            "should have correctly updated the color (in edit)"
        );

        form.destroy();
    });

    QUnit.skipWOWL("fieldmany2many tags with no_edit_color option", async function (assert) {
        assert.expect(1);

        this.data.partner.records[0].timmy = [12];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<field name=\"timmy\" widget=\"many2many_tags\" options=\"{'color_field': 'color', 'no_edit_color': 1}\"/>" +
                "</form>",
            res_id: 1,
        });

        // Click to try to open colorpicker
        await testUtils.dom.click(form.$(".badge:first() .dropdown-toggle"));
        assert.containsNone(document.body, ".o_colorpicker");

        form.destroy();
    });

    QUnit.skipWOWL("fieldmany2many tags in editable list", async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            context: { take: "five" },
            arch:
                '<tree editable="bottom">' +
                '<field name="foo"/>' +
                '<field name="timmy" widget="many2many_tags"/>' +
                "</tree>",
            mockRPC: function (route, args) {
                if (args.method === "read" && args.model === "partner_type") {
                    assert.deepEqual(
                        args.kwargs.context,
                        { take: "five" },
                        "The context should be passed to the RPC"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(
            list,
            ".o_data_row:first .o_field_many2manytags .badge",
            "m2m field should contain one tag"
        );

        // edit first row
        await testUtils.dom.click(list.$(".o_data_row:first td:nth(2)"));

        var $m2o = list.$(".o_data_row:first .o_field_many2manytags .o_field_many2one");
        assert.strictEqual($m2o.length, 1, "a many2one widget should have been instantiated");

        // add a tag
        await testUtils.fields.many2one.clickOpenDropdown("timmy");
        await testUtils.fields.many2one.clickHighlightedItem("timmy");

        assert.containsN(
            list,
            ".o_data_row:first .o_field_many2manytags .badge",
            2,
            "m2m field should contain 2 tags"
        );

        // leave edition
        await testUtils.dom.click(list.$(".o_data_row:nth(1) td:nth(2)"));

        assert.containsN(
            list,
            ".o_data_row:first .o_field_many2manytags .badge",
            2,
            "m2m field should contain 2 tags"
        );

        list.destroy();
    });

    QUnit.skipWOWL("search more in many2one: group and use the pager", async function (assert) {
        assert.expect(2);

        this.data.partner.records.push(
            {
                id: 5,
                display_name: "Partner 4",
            },
            {
                id: 6,
                display_name: "Partner 5",
            },
            {
                id: 7,
                display_name: "Partner 6",
            },
            {
                id: 8,
                display_name: "Partner 7",
            },
            {
                id: 9,
                display_name: "Partner 8",
            },
            {
                id: 10,
                display_name: "Partner 9",
            }
        );
        this.data.partner.fields.datetime.searchable = true;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="trululu"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",

            res_id: 1,
            archs: {
                "partner,false,list": '<tree limit="7"><field name="display_name"/></tree>',
                "partner,false,search":
                    "<search><group>" +
                    '    <filter name="bar" string="Bar" context="{\'group_by\': \'bar\'}"/>' +
                    "</group></search>",
            },
            viewOptions: {
                mode: "edit",
            },
        });
        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        await testUtils.fields.many2one.clickItem("trululu", "Search");
        const modal = document.body.querySelector(".modal");
        await cpHelpers.toggleGroupByMenu(modal);
        await cpHelpers.toggleMenuItem(modal, "Bar");

        await testUtils.dom.click($(".modal .o_group_header:first"));

        assert.strictEqual(
            $(".modal tbody:nth(1) .o_data_row").length,
            7,
            "should display 7 records in the first page"
        );
        await testUtils.dom.click($(".modal .o_group_header:first .o_pager_next"));
        assert.strictEqual(
            $(".modal tbody:nth(1) .o_data_row").length,
            1,
            "should display 1 record in the second page"
        );

        form.destroy();
    });

    QUnit.skipWOWL("many2many_tags can load more than 40 records", async function (assert) {
        assert.expect(1);

        this.data.partner.fields.partner_ids = {
            string: "Partner",
            type: "many2many",
            relation: "partner",
        };
        this.data.partner.records[0].partner_ids = [];
        for (var i = 15; i < 115; i++) {
            this.data.partner.records.push({ id: i, display_name: "walter" + i });
            this.data.partner.records[0].partner_ids.push(i);
        }
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="partner_ids" widget="many2many_tags"/>' +
                "</form>",
            res_id: 1,
        });
        assert.containsN(
            form,
            '.o_field_widget[name="partner_ids"] .badge',
            100,
            "should have rendered 100 tags"
        );
        form.destroy();
    });

    QUnit.skipWOWL(
        "many2many_tags loads records according to limit defined on widget prototype",
        async function (assert) {
            assert.expect(1);

            const M2M_LIMIT = relationalFields.FieldMany2ManyTags.prototype.limit;
            relationalFields.FieldMany2ManyTags.prototype.limit = 30;
            this.data.partner.fields.partner_ids = {
                string: "Partner",
                type: "many2many",
                relation: "partner",
            };
            this.data.partner.records[0].partner_ids = [];
            for (var i = 15; i < 50; i++) {
                this.data.partner.records.push({ id: i, display_name: "walter" + i });
                this.data.partner.records[0].partner_ids.push(i);
            }
            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: '<form><field name="partner_ids" widget="many2many_tags"/></form>',
                res_id: 1,
            });

            assert.strictEqual(
                form.$('.o_field_widget[name="partner_ids"] .badge').length,
                30,
                "should have rendered 30 tags even though 35 records linked"
            );

            relationalFields.FieldMany2ManyTags.prototype.limit = M2M_LIMIT;
            form.destroy();
        }
    );

    QUnit.skipWOWL("field many2many_tags keeps focus when being edited", async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];
        this.data.partner.onchanges.foo = function (obj) {
            obj.timmy = [[5]]; // DELETE command
        };

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="foo"/>' +
                '<field name="timmy" widget="many2many_tags"/>' +
                "</form>",
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.containsOnce(form, ".o_field_many2manytags .badge", "should contain one tag");

        // update foo, which will trigger an onchange and update timmy
        // -> m2mtags input should not have taken the focus
        form.$("input[name=foo]").focus();
        await testUtils.fields.editInput(form.$("input[name=foo]"), "trigger onchange");
        assert.containsNone(form, ".o_field_many2manytags .badge", "should contain no tags");
        assert.strictEqual(
            form.$("input[name=foo]").get(0),
            document.activeElement,
            "foo input should have kept the focus"
        );

        // add a tag -> m2mtags input should still have the focus
        await testUtils.fields.many2one.clickOpenDropdown("timmy");
        await testUtils.fields.many2one.clickHighlightedItem("timmy");

        assert.containsOnce(form, ".o_field_many2manytags .badge", "should contain a tag");
        assert.strictEqual(
            form.$(".o_field_many2manytags input").get(0),
            document.activeElement,
            "m2m tags input should have kept the focus"
        );

        // remove a tag -> m2mtags input should still have the focus
        await testUtils.dom.click(form.$(".o_field_many2manytags .o_delete"));
        assert.containsNone(form, ".o_field_many2manytags .badge", "should contain no tags");
        assert.strictEqual(
            form.$(".o_field_many2manytags input").get(0),
            document.activeElement,
            "m2m tags input should have kept the focus"
        );

        form.destroy();
    });

    QUnit.skipWOWL("widget many2many_tags in one2many with display_name", async function (assert) {
        assert.expect(4);
        this.data.turtle.records[0].partner_ids = [2];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="turtles">' +
                "<tree>" +
                '<field name="partner_ids" widget="many2many_tags"/>' + // will use display_name
                "</tree>" +
                "<form>" +
                "<sheet>" +
                '<field name="partner_ids"/>' +
                "</sheet>" +
                "</form>" +
                "</field>" +
                "</sheet>" +
                "</form>",
            archs: {
                "partner,false,list": '<tree><field name="foo"/></tree>',
            },
            res_id: 1,
        });

        assert.strictEqual(
            form
                .$(
                    '.o_field_one2many[name="turtles"] .o_list_view .o_field_many2manytags[name="partner_ids"]'
                )
                .text()
                .replace(/\s/g, ""),
            "secondrecordaaa",
            "the tags should be correctly rendered"
        );

        // open the x2m form view
        await testUtils.dom.click(
            form.$('.o_field_one2many[name="turtles"] .o_list_view td.o_data_cell:first')
        );
        await testUtils.nextTick(); // wait for quick edit
        assert.strictEqual(
            $(
                '.modal .o_form_view .o_field_many2many[name="partner_ids"] .o_list_view .o_data_cell'
            ).text(),
            "blipMy little Foo Value",
            "the list view should be correctly rendered with foo"
        );

        await testUtils.dom.click($(".modal button.o_form_button_cancel"));
        assert.strictEqual(
            form
                .$(
                    '.o_field_one2many[name="turtles"] .o_list_view .o_field_many2manytags[name="partner_ids"]'
                )
                .text()
                .replace(/\s/g, ""),
            "secondrecordaaa",
            "the tags should still be correctly rendered"
        );

        assert.strictEqual(
            form
                .$(
                    '.o_field_one2many[name="turtles"] .o_list_view .o_field_many2manytags[name="partner_ids"]'
                )
                .text()
                .replace(/\s/g, ""),
            "secondrecordaaa",
            "the tags should still be correctly rendered"
        );

        form.destroy();
    });

    QUnit.skipWOWL("widget many2many_tags: tags title attribute", async function (assert) {
        assert.expect(1);
        this.data.turtle.records[0].partner_ids = [2];

        var form = await createView({
            View: FormView,
            model: "turtle",
            data: this.data,
            arch:
                '<form string="Turtles">' +
                "<sheet>" +
                '<field name="display_name"/>' +
                '<field name="partner_ids" widget="many2many_tags"/>' +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        assert.deepEqual(
            form.$(".o_field_many2manytags.o_field_widget .badge .o_badge_text").attr("title"),
            "second record",
            "the title should be filled in"
        );

        form.destroy();
    });

    QUnit.skipWOWL(
        "widget many2many_tags: toggle colorpicker multiple times",
        async function (assert) {
            assert.expect(11);

            this.data.partner.records[0].timmy = [12];
            this.data.partner_type.records[0].color = 0;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.strictEqual($(".o_field_many2manytags .badge").length, 1, "should have one tag");
            assert.strictEqual(
                $(".o_field_many2manytags .badge").data("color"),
                0,
                "tag should have color 0"
            );
            assert.strictEqual(
                $(".o_colorpicker:visible").length,
                0,
                "colorpicker should be closed"
            );

            // click on the badge to open colorpicker
            await testUtils.dom.click(form.$(".o_field_many2manytags .badge .dropdown-toggle"));

            assert.strictEqual($(".o_colorpicker:visible").length, 1, "colorpicker should be open");

            // click on the badge again to close colorpicker
            await testUtils.dom.click(form.$(".o_field_many2manytags .badge .dropdown-toggle"));

            assert.strictEqual(
                $(".o_field_many2manytags .badge").data("color"),
                0,
                "tag should still have color 0"
            );
            assert.strictEqual(
                $(".o_colorpicker:visible").length,
                0,
                "colorpicker should be closed"
            );

            // click on the badge to open colorpicker
            await testUtils.dom.click(form.$(".o_field_many2manytags .badge .dropdown-toggle"));

            assert.strictEqual($(".o_colorpicker:visible").length, 1, "colorpicker should be open");

            // click on the colorpicker, but not on a color
            await testUtils.dom.click(form.$(".o_colorpicker"));

            assert.strictEqual(
                $(".o_field_many2manytags .badge").data("color"),
                0,
                "tag should still have color 0"
            );
            assert.strictEqual(
                $(".o_colorpicker:visible").length,
                0,
                "colorpicker should be closed"
            );

            // click on the badge to open colorpicker
            await testUtils.dom.click(form.$(".o_field_many2manytags .badge .dropdown-toggle"));

            // click on a color in the colorpicker
            await testUtils.dom.triggerEvents(form.$(".o_colorpicker .o_tag_color_2"), [
                "mousedown",
            ]);

            assert.strictEqual(
                $(".o_field_many2manytags .badge").data("color"),
                2,
                "tag should have color 2"
            );
            assert.strictEqual(
                $(".o_colorpicker:visible").length,
                0,
                "colorpicker should be closed"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL("widget many2many_tags_avatar", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "turtle",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="partner_ids" widget="many2many_tags_avatar"/>' +
                "</sheet>" +
                "</form>",
            res_id: 2,
        });

        assert.containsN(
            form,
            ".o_field_many2manytags.avatar.o_field_widget .badge",
            2,
            "should have 2 records"
        );
        assert.strictEqual(
            form.$(".o_field_many2manytags.avatar.o_field_widget .badge:first img").data("src"),
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image"
        );

        form.destroy();
    });

    QUnit.skipWOWL("widget many2many_tags_avatar in list view", async function (assert) {
        assert.expect(18);

        const records = [];
        for (let id = 5; id <= 15; id++) {
            records.push({
                id,
                display_name: `record ${id}`,
            });
        }
        this.data.partner.records = this.data.partner.records.concat(records);

        this.data.turtle.records.push({
            id: 4,
            display_name: "crime master gogo",
            turtle_bar: true,
            turtle_foo: "yop",
            partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        });
        this.data.turtle.records[0].partner_ids = [1];
        this.data.turtle.records[1].partner_ids = [1, 2, 4, 5, 6, 7];
        this.data.turtle.records[2].partner_ids = [1, 2, 4, 5, 7];

        const list = await createView({
            View: ListView,
            model: "turtle",
            data: this.data,
            arch:
                '<tree editable="bottom"><field name="partner_ids" widget="many2many_tags_avatar"/></tree>',
        });

        assert.strictEqual(
            list.$(".o_data_row:first .o_field_many2manytags img.o_m2m_avatar").data("src"),
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            list
                .$(".o_data_row:first .o_many2many_tags_avatar_cell .o_field_many2manytags div")
                .text()
                .trim(),
            "first record",
            "should display like many2one avatar if there is only one record"
        );

        assert.containsN(
            list,
            ".o_data_row:eq(1) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)",
            4,
            "should have 4 records"
        );
        assert.containsN(
            list,
            ".o_data_row:eq(2) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)",
            5,
            "should have 5 records"
        );
        assert.containsOnce(
            list,
            ".o_data_row:eq(1) .o_field_many2manytags .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            list.$(".o_data_row:eq(1) .o_field_many2manytags .o_m2m_avatar_empty").text().trim(),
            "+2",
            "should have +2 in o_m2m_avatar_empty"
        );
        assert.strictEqual(
            list.$(".o_data_row:eq(1) .o_field_many2manytags img.o_m2m_avatar:first").data("src"),
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            list.$(".o_data_row:eq(1) .o_field_many2manytags img.o_m2m_avatar:eq(1)").data("src"),
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            list.$(".o_data_row:eq(1) .o_field_many2manytags img.o_m2m_avatar:eq(2)").data("src"),
            "/web/image/partner/4/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            list.$(".o_data_row:eq(1) .o_field_many2manytags img.o_m2m_avatar:eq(3)").data("src"),
            "/web/image/partner/5/avatar_128",
            "should have correct avatar image"
        );
        assert.containsNone(
            list,
            ".o_data_row:eq(2) .o_field_many2manytags .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.containsN(
            list,
            ".o_data_row:eq(3) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)",
            4,
            "should have 4 records"
        );
        assert.containsOnce(
            list,
            ".o_data_row:eq(3) .o_field_many2manytags .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            list.$(".o_data_row:eq(3) .o_field_many2manytags .o_m2m_avatar_empty").text().trim(),
            "+9",
            "should have +9 in o_m2m_avatar_empty"
        );

        list.$(".o_data_row:eq(1) .o_field_many2manytags .o_m2m_avatar_empty").trigger(
            $.Event("mouseenter")
        );
        await testUtils.nextTick();
        assert.containsOnce(list, ".popover", "should open a popover hover on o_m2m_avatar_empty");
        assert.strictEqual(
            list.$(".popover .popover-body > div").text().trim(),
            "record 6record 7",
            "should have a right text in popover"
        );

        await testUtils.dom.click(list.$(".o_data_row:eq(0) .o_many2many_tags_avatar_cell"));
        assert.containsN(
            list,
            ".o_data_row.o_selected_row .o_many2many_tags_avatar_cell .badge",
            1,
            "should have 1 many2many badges in edit mode"
        );

        await testUtils.fields.many2one.clickOpenDropdown("partner_ids");
        await testUtils.fields.many2one.clickItem("partner_ids", "second record");
        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.containsN(
            list,
            ".o_data_row:eq(0) .o_field_many2manytags span",
            2,
            "should have 2 records"
        );

        list.destroy();
    });

    QUnit.skipWOWL("widget many2many_tags_avatar in kanban view", async function (assert) {
        assert.expect(13);

        const records = [];
        for (let id = 5; id <= 15; id++) {
            records.push({
                id,
                display_name: `record ${id}`,
            });
        }
        this.data.partner.records = this.data.partner.records.concat(records);

        this.data.turtle.records.push({
            id: 4,
            display_name: "crime master gogo",
            turtle_bar: true,
            turtle_foo: "yop",
            partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        });
        this.data.turtle.records[0].partner_ids = [1];
        this.data.turtle.records[1].partner_ids = [1, 2, 4];
        this.data.turtle.records[2].partner_ids = [1, 2, 4, 5];

        const kanban = await createView({
            View: KanbanView,
            model: "turtle",
            data: this.data,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="display_name"/>
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                "turtle,false,form": '<form><field name="display_name"/></form>',
            },
            intercepts: {
                switch_view: function (event) {
                    const { mode, model, res_id, view_type } = event.data;
                    assert.deepEqual(
                        { mode, model, res_id, view_type },
                        {
                            mode: "readonly",
                            model: "turtle",
                            res_id: 1,
                            view_type: "form",
                        },
                        "should trigger an event to open the clicked record in a form view"
                    );
                },
            },
        });

        assert.strictEqual(
            kanban.$(".o_kanban_record:first .o_field_many2manytags img.o_m2m_avatar").data("src"),
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );

        assert.containsN(
            kanban,
            ".o_kanban_record:eq(1) .o_field_many2manytags span",
            3,
            "should have 3 records"
        );
        assert.containsN(
            kanban,
            ".o_kanban_record:eq(2) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)",
            2,
            "should have 2 records"
        );
        assert.strictEqual(
            kanban
                .$(".o_kanban_record:eq(2) .o_field_many2manytags img.o_m2m_avatar:first")
                .data("src"),
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            kanban
                .$(".o_kanban_record:eq(2) .o_field_many2manytags img.o_m2m_avatar:eq(1)")
                .data("src"),
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image"
        );
        assert.containsOnce(
            kanban,
            ".o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            kanban
                .$(".o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty")
                .text()
                .trim(),
            "+2",
            "should have +2 in o_m2m_avatar_empty"
        );

        assert.containsN(
            kanban,
            ".o_kanban_record:eq(3) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)",
            2,
            "should have 2 records"
        );
        assert.containsOnce(
            kanban,
            ".o_kanban_record:eq(3) .o_field_many2manytags .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            kanban
                .$(".o_kanban_record:eq(3) .o_field_many2manytags .o_m2m_avatar_empty")
                .text()
                .trim(),
            "9+",
            "should have 9+ in o_m2m_avatar_empty"
        );

        kanban
            .$(".o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty")
            .trigger($.Event("mouseenter"));
        await testUtils.nextTick();
        assert.containsOnce(
            kanban,
            ".popover",
            "should open a popover hover on o_m2m_avatar_empty"
        );
        assert.strictEqual(
            kanban.$(".popover .popover-body > div").text().trim(),
            "aaarecord 5",
            "should have a right text in popover"
        );
        await testUtils.dom.click(
            kanban.$(".o_kanban_record:first .o_field_many2manytags img.o_m2m_avatar")
        );

        kanban.destroy();
    });

    QUnit.skipWOWL("fieldmany2many tags: quick create a new record", async function (assert) {
        assert.expect(3);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form><field name="timmy" widget="many2many_tags"/></form>`,
        });

        assert.containsNone(form, ".o_field_many2manytags .badge");

        await testUtils.fields.many2one.searchAndClickItem("timmy", { search: "new value" });

        assert.containsOnce(form, ".o_field_many2manytags .badge");

        await testUtils.form.clickSave(form);

        assert.strictEqual(
            form.el.querySelector(".o_field_many2manytags").innerText.trim(),
            "new value"
        );

        form.destroy();
    });

    QUnit.skipWOWL("select a many2many value by focusing out", async function (assert) {
        assert.expect(4);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form><field name="timmy" widget="many2many_tags"/></form>`,
        });

        assert.containsNone(form, ".o_field_many2manytags .badge");

        form.$(".o_field_many2manytags input").focus().val("go").trigger("input").trigger("keyup");
        await testUtils.nextTick();
        form.$(".o_field_many2manytags input").trigger("blur");
        await testUtils.nextTick();

        assert.containsNone(document.body, ".modal");
        assert.containsOnce(form, ".o_field_many2manytags .badge");
        assert.strictEqual(form.$(".o_field_many2manytags .badge").text().trim(), "gold");

        form.destroy();
    });
});
