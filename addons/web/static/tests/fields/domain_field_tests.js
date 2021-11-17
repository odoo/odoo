/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import { click, makeDeferred, nextTick, triggerEvent, triggerEvents } from "../helpers/utils";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";
import { makeView } from "../views/helpers";

const serviceRegistry = registry.category("services");

let serverData;

function hasGroup(group) {
    return group === "base.group_allow_export";
}

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date", searchable: true },
                        datetime: { string: "A datetime", type: "datetime", searchable: true },
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        txt: {
                            string: "txt",
                            type: "text",
                            default: "My little txt Value\nHo-ho-hoooo Merry Christmas",
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                            searchable: true,
                        },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                        document: { string: "Binary", type: "binary" },
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            p: [],
                            timmy: [],
                            trululu: 4,
                            selection: "blocked",
                            document: "coucou==\n",
                            hex_color: "#ff0000",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 0,
                            qux: 0,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            sequence: 4,
                            currency_id: 2,
                            selection: "normal",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            sequence: 9,
                            int_field: false,
                            qux: false,
                            selection: "done",
                        },
                        { id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859 },
                        { id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, currency_id: 1 },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
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
                        name: { string: "Partner Type", type: "char", searchable: true },
                        color: { string: "Color index", type: "integer", searchable: true },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                currency: {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: { string: "Currency Sumbol", type: "char", searchable: true },
                        position: { string: "Currency Position", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "$",
                            symbol: "$",
                            position: "before",
                        },
                        {
                            id: 2,
                            display_name: "€",
                            symbol: "€",
                            position: "after",
                        },
                    ],
                },
                "ir.translation": {
                    fields: {
                        lang: { type: "char" },
                        value: { type: "char" },
                        res_id: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            res_id: 37,
                            value: "",
                            lang: "en_US",
                        },
                    ],
                },
            },
        };

        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });
    });

    QUnit.module("DomainField");

    QUnit.skip(
        "The domain editor should not crash the view when given a dynamic filter",
        async function (assert) {
            //dynamic filters (containing variables, such as uid, parent or today)
            //are not handled by the domain editor, but it shouldn't crash the view
            assert.expect(1);

            this.data.partner.records[0].foo = '[["int_field", "=", uid]]';

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="foo" widget="domain" options="{\'model\': \'partner\'}"/>' +
                    '<field name="int_field" invisible="1"/>' +
                    "</form>",
                res_id: 1,
                session: {
                    user_context: { uid: 14 },
                },
            });

            assert.strictEqual(
                form.$(".o_read_mode").text(),
                "This domain is not supported.",
                "The widget should not crash the view, but gracefully admit its failure."
            );
            form.destroy();
        }
    );

    QUnit.skip("basic domain field usage is ok", async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].foo = "[]";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="domain" options="{\'model\': \'partner_type\'}"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });
        await testUtils.form.clickEdit(form);

        // As the domain is empty, there should be a button to add the first
        // domain part
        var $domain = form.$(".o_field_domain");
        var $domainAddFirstNodeButton = $domain.find(".o_domain_add_first_node_button");
        assert.equal(
            $domainAddFirstNodeButton.length,
            1,
            "there should be a button to create first domain element"
        );

        // Clicking on the button should add the [["id", "=", "1"]] domain, so
        // there should be a field selector in the DOM
        await testUtils.dom.click($domainAddFirstNodeButton);
        var $fieldSelector = $domain.find(".o_field_selector");
        assert.equal($fieldSelector.length, 1, "there should be a field selector");

        // Focusing the field selector input should open the field selector
        // popover
        await testUtils.dom.triggerEvents($fieldSelector, "focus");
        var $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"), "field selector popover should be visible");

        assert.containsOnce(
            $fieldSelectorPopover,
            ".o_field_selector_search input",
            "field selector popover should contain a search input"
        );

        // The popover should contain the list of partner_type fields and so
        // there should be the "Color index" field
        var $lis = $fieldSelectorPopover.find("li");
        var $colorIndex = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Color index") >= 0) {
                $colorIndex = $li;
            }
        });
        assert.equal(
            $colorIndex.length,
            1,
            "field selector popover should contain 'Color index' field"
        );

        // Clicking on this field should close the popover, then changing the
        // associated value should reveal one matched record
        await testUtils.dom.click($colorIndex);
        await testUtils.fields.editAndTrigger($(".o_domain_leaf_value_input"), 2, ["change"]);
        assert.equal(
            $domain.find(".o_domain_show_selection_button").text().trim().substr(0, 2),
            "1 ",
            "changing color value to 2 should reveal only one record"
        );

        // Saving the form view should show a readonly domain containing the
        // "color" field
        await testUtils.form.clickSave(form);
        $domain = form.$(".o_field_domain");
        assert.ok(
            $domain.html().indexOf("Color index") >= 0,
            "field selector readonly value should now contain 'Color index'"
        );
        form.destroy();
    });

    QUnit.skip("domain field is correctly reset on every view change", async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].foo = '[["id","=",1]]';
        this.data.partner.fields.bar.type = "char";
        this.data.partner.records[0].bar = "product";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                "<group>" +
                '<field name="bar"/>' +
                '<field name="foo" widget="domain" options="{\'model\': \'bar\'}"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });
        await testUtils.form.clickEdit(form);

        // As the domain is equal to [["id", "=", 1]] there should be a field
        // selector to change this
        var $domain = form.$(".o_field_domain");
        var $fieldSelector = $domain.find(".o_field_selector");
        assert.equal($fieldSelector.length, 1, "there should be a field selector");

        // Focusing its input should open the field selector popover
        await testUtils.dom.triggerEvents($fieldSelector, "focus");
        var $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"), "field selector popover should be visible");

        // As the value of the "bar" field is "product", the field selector
        // popover should contain the list of "product" fields
        var $lis = $fieldSelectorPopover.find("li");
        var $sampleLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Product Name") >= 0) {
                $sampleLi = $li;
            }
        });
        assert.strictEqual($lis.length, 1, "field selector popover should contain only one field");
        assert.strictEqual(
            $sampleLi.length,
            1,
            "field selector popover should contain 'Product Name' field"
        );

        // Now change the value of the "bar" field to "partner_type"
        await testUtils.dom.click(form.$("input.o_field_widget"));
        await testUtils.fields.editInput(form.$("input.o_field_widget"), "partner_type");

        // Refocusing the field selector input should open the popover again
        $fieldSelector = form.$(".o_field_selector");
        $fieldSelector.trigger("focusin");
        $fieldSelectorPopover = $fieldSelector.find(".o_field_selector_popover");
        assert.ok($fieldSelectorPopover.is(":visible"), "field selector popover should be visible");

        // Now the list of fields should be the ones of the "partner_type" model
        $lis = $fieldSelectorPopover.find("li");
        $sampleLi = $();
        $lis.each(function () {
            var $li = $(this);
            if ($li.html().indexOf("Color index") >= 0) {
                $sampleLi = $li;
            }
        });
        assert.strictEqual($lis.length, 2, "field selector popover should contain two fields");
        assert.strictEqual(
            $sampleLi.length,
            1,
            "field selector popover should contain 'Color index' field"
        );
        form.destroy();
    });

    QUnit.skip(
        "domain field can be reset with a new domain (from onchange)",
        async function (assert) {
            assert.expect(2);

            this.data.partner.records[0].foo = "[]";
            this.data.partner.onchanges = {
                display_name: function (obj) {
                    obj.foo = '[["id", "=", 1]]';
                },
            };

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="display_name"/>' +
                    '<field name="foo" widget="domain" options="{\'model\': \'partner\'}"/>' +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.equal(
                form.$(".o_domain_show_selection_button").text().trim(),
                "5 record(s)",
                "the domain being empty, there should be 5 records"
            );

            // update display_name to trigger the onchange and reset foo
            await testUtils.fields.editInput(
                form.$(".o_field_widget[name=display_name]"),
                "new value"
            );

            assert.equal(
                form.$(".o_domain_show_selection_button").text().trim(),
                "1 record(s)",
                "the domain has changed, there should be only 1 record"
            );

            form.destroy();
        }
    );

    QUnit.skip("domain field: handle false domain as []", async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].foo = false;
        this.data.partner.fields.bar.type = "char";
        this.data.partner.records[0].bar = "product";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                "<group>" +
                '<field name="bar"/>' +
                '<field name="foo" widget="domain" options="{\'model\': \'bar\'}"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "search_count") {
                    assert.deepEqual(args.args[0], [], "should send a valid domain");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        assert.strictEqual(
            form.$(".o_field_widget[name=foo]:not(.o_field_empty)").length,
            1,
            "there should be a domain field, not considered empty"
        );

        await testUtils.form.clickEdit(form);

        var $warning = form.$(".o_field_widget[name=foo] .text-warning");
        assert.strictEqual($warning.length, 0, "should not display that the domain is invalid");

        form.destroy();
    });

    QUnit.skip("basic domain field: show the selection", async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].foo = "[]";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="domain" options="{\'model\': \'partner_type\'}"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            archs: {
                "partner_type,false,list": '<tree><field name="display_name"/></tree>',
                "partner_type,false,search": '<search><field name="name" string="Name"/></search>',
            },
            res_id: 1,
        });

        assert.equal(
            form.$(".o_domain_show_selection_button").text().trim().substr(0, 2),
            "2 ",
            "selection should contain 2 records"
        );

        // open the selection
        await testUtils.dom.click(form.$(".o_domain_show_selection_button"));
        assert.strictEqual(
            $(".modal .o_list_view .o_data_row").length,
            2,
            "should have open a list view with 2 records in a dialog"
        );

        // click on a record -> should not open the record
        // we don't actually check that it doesn't open the record because even
        // if it tries to, it will crash as we don't define an arch in this test
        await testUtils.dom.click($(".modal .o_list_view .o_data_row:first .o_data_cell"));

        form.destroy();
    });

    QUnit.skip("field context is propagated when opening selection", async function (assert) {
        assert.expect(1);

        this.data.partner.records[0].foo = "[]";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form>
                    <field name="foo" widget="domain" options="{'model': 'partner_type'}" context="{'tree_view_ref': 3}"/>
                </form>
            `,
            archs: {
                "partner_type,false,list": '<tree><field name="display_name"/></tree>',
                "partner_type,3,list": '<tree><field name="id"/></tree>',
                "partner_type,false,search": '<search><field name="name" string="Name"/></search>',
            },
            res_id: 1,
        });

        await testUtils.dom.click(form.$(".o_domain_show_selection_button"));

        assert.strictEqual(
            $(".modal .o_data_row").text(),
            "1214",
            "should have picked the correct list view"
        );

        form.destroy();
    });

    QUnit.skip("domain field: manually edit domain with textarea", async function (assert) {
        assert.expect(9);

        const originalDebug = odoo.debug;
        odoo.debug = true;

        this.data.partner.records[0].foo = false;
        this.data.partner.fields.bar.type = "char";
        this.data.partner.records[0].bar = "product";

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "search_count") {
                    assert.step(JSON.stringify(args.args[0]));
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                mode: "edit",
            },
            res_id: 1,
        });

        assert.strictEqual(form.$(".o_domain_show_selection_button").text().trim(), "2 record(s)");
        assert.verifySteps(["[]"]);

        await testUtils.fields.editAndTrigger(
            form.$(".o_domain_debug_input"),
            "[['id', '<', 40]]",
            ["change"]
        );
        // the count should not be re-computed when editing with the textarea
        assert.strictEqual(form.$(".o_domain_show_selection_button").text().trim(), "2 record(s)");
        assert.verifySteps([]);

        await testUtils.form.clickSave(form);
        assert.strictEqual(form.$(".o_domain_show_selection_button").text().trim(), "1 record(s)");
        assert.verifySteps([
            '[["id","<",40]]', // to validate the domain, before saving
            '[["id","<",40]]', // to render in readonly once it has been saved
        ]);

        form.destroy();
        odoo.debug = originalDebug;
    });

    QUnit.skip(
        "domain field: manually set an invalid domain with textarea",
        async function (assert) {
            assert.expect(9);

            const originalDebug = odoo.debug;
            odoo.debug = true;

            this.data.partner.records[0].foo = false;
            this.data.partner.fields.bar.type = "char";
            this.data.partner.records[0].bar = "product";

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
                mockRPC(route, args) {
                    if (args.method === "search_count") {
                        assert.step(JSON.stringify(args.args[0]));
                    }
                    if (args.method === "write") {
                        throw new Error("should not save");
                    }
                    return this._super.apply(this, arguments);
                },
                viewOptions: {
                    mode: "edit",
                },
                res_id: 1,
            });

            assert.strictEqual(
                form.$(".o_domain_show_selection_button").text().trim(),
                "2 record(s)"
            );
            assert.verifySteps(["[]"]);

            await testUtils.fields.editAndTrigger(form.$(".o_domain_debug_input"), "[['abc']]", [
                "change",
            ]);
            // the count should not be re-computed when editing with the textarea
            assert.strictEqual(
                form.$(".o_domain_show_selection_button").text().trim(),
                "2 record(s)"
            );
            assert.verifySteps([]);

            await testUtils.form.clickSave(form);
            assert.hasClass(
                form.$(".o_field_domain"),
                "o_field_invalid",
                "the field is marked as invalid"
            );
            assert.hasClass(
                form.$(".o_form_view"),
                "o_form_editable",
                "the view is still in edit mode"
            );
            assert.verifySteps(['[["abc"]]']);

            form.destroy();
            odoo.debug = originalDebug;
        }
    );

    QUnit.skip(
        "domain field: reload count by clicking on the refresh button",
        async function (assert) {
            assert.expect(7);

            const originalDebug = odoo.debug;
            odoo.debug = true;

            this.data.partner.records[0].foo = "[]";
            this.data.partner.fields.bar.type = "char";
            this.data.partner.records[0].bar = "product";

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
                async mockRPC(route, args) {
                    if (args.method === "search_count") {
                        assert.step(JSON.stringify(args.args[0]));
                    }
                    return this._super.apply(this, arguments);
                },
                viewOptions: {
                    mode: "edit",
                },
                res_id: 1,
            });

            assert.strictEqual(
                form.$(".o_domain_show_selection_button").text().trim(),
                "2 record(s)"
            );

            await testUtils.fields.editAndTrigger(
                form.$(".o_domain_debug_input"),
                "[['id', '<', 40]]",
                ["change"]
            );
            // the count should not be re-computed when editing with the textarea
            assert.strictEqual(
                form.$(".o_domain_show_selection_button").text().trim(),
                "2 record(s)"
            );
            assert.verifySteps(["[]"]);

            // click on the refresh button
            await testUtils.dom.click(form.$(".o_refresh_count"));
            assert.strictEqual(
                form.$(".o_domain_show_selection_button").text().trim(),
                "1 record(s)"
            );
            assert.verifySteps(['[["id","<",40]]']);

            form.destroy();
            odoo.debug = originalDebug;
        }
    );

    QUnit.skip("domain field: does not wait for the count to render", async function (assert) {
        assert.expect(5);

        this.data.partner.records[0].foo = "[]";
        this.data.partner.fields.bar.type = "char";
        this.data.partner.records[0].bar = "product";

        const def = testUtils.makeTestPromise();
        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
            async mockRPC(route, args) {
                const result = this._super.apply(this, arguments);
                if (args.method === "search_count") {
                    await def;
                }
                return result;
            },
            res_id: 1,
        });

        assert.containsOnce(form, ".o_field_domain_panel .fa-circle-o-notch.fa-spin");
        assert.containsNone(form, ".o_field_domain_panel .o_domain_show_selection_button");

        def.resolve();
        await testUtils.nextTick();

        assert.containsNone(form, ".o_field_domain_panel .fa-circle-o-notch .fa-spin");
        assert.containsOnce(form, ".o_field_domain_panel .o_domain_show_selection_button");
        assert.strictEqual(form.$(".o_domain_show_selection_button").text().trim(), "2 record(s)");

        form.destroy();
    });
});
