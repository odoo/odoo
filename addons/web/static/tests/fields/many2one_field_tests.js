/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/fields/many2one_field";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import {
    click,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerEvents,
} from "../helpers/utils";
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
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        bar: { string: "Bar", type: "boolean", default: true },
                        int_field: { string: "int_field", type: "integer", sortable: true },
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
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
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
                        display_name: { string: "Partner Type", type: "char" },
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
            },
        };

        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });

        patchWithCleanup(Many2OneField, {
            AUTOCOMPLETE_DELAY: 0,
        });
    });

    QUnit.module("Many2oneField");

    QUnit.skip("many2ones in form views", async function (assert) {
        assert.expect(5);
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="trululu" string="custom label"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            archs: {
                "partner,false,form": '<form string="Partners"><field name="display_name"/></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "get_formview_action") {
                    assert.deepEqual(
                        args.args[0],
                        [4],
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
                        [4],
                        "should call get_formview_id with correct id"
                    );
                    return Promise.resolve(false);
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

        assert.strictEqual(form.$("a.o_form_uri:contains(aaa)").length, 1, "should contain a link");
        await testUtils.dom.click(form.$("a.o_form_uri"));

        await testUtils.form.clickEdit(form);

        await testUtils.dom.click(form.$(".o_external_button"));
        assert.strictEqual(
            $(".modal .modal-title").text().trim(),
            "Open: custom label",
            "dialog title should display the custom string label"
        );

        // TODO: test that we can edit the record in the dialog, and that
        // the value is correctly updated on close
        form.destroy();
    });

    QUnit.skip("editing a many2one, but not changing anything", async function (assert) {
        assert.expect(2);
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="trululu"/>' +
                "</sheet>" +
                "</form>",
            archs: {
                "partner,false,form": '<form string="Partners"><field name="display_name"/></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    assert.deepEqual(
                        args.args[0],
                        [4],
                        "should call get_formview_id with correct id"
                    );
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },
            viewOptions: {
                ids: [1, 2],
            },
        });

        await testUtils.form.clickEdit(form);

        // click on the external button (should do an RPC)
        await testUtils.dom.click(form.$(".o_external_button"));
        // save and close modal
        await testUtils.dom.click($(".modal .modal-footer .btn-primary:first"));
        // save form
        await testUtils.form.clickSave(form);
        // click next on pager
        await testUtils.dom.click(form.el.querySelector(".o_pager .o_pager_next"));

        // this checks that the view did not ask for confirmation that the
        // record is dirty
        assert.strictEqual(
            form.el.querySelector(".o_pager").innerText.trim(),
            "2 / 2",
            "pager should be at second page"
        );
        form.destroy();
    });

    QUnit.skip("context in many2one and default get", async function (assert) {
        assert.expect(1);

        this.data.partner.fields.int_field.default = 14;
        this.data.partner.fields.trululu.default = 2;

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="int_field"/>' +
                '<field name="trululu"  context="{\'blip\':int_field}" options=\'{"always_reload": True}\'/>' +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "name_get") {
                    assert.strictEqual(
                        args.kwargs.context.blip,
                        14,
                        "context should have been properly sent to the nameget rpc"
                    );
                }
                return this._super(route, args);
            },
        });
        form.destroy();
    });

    QUnit.skip(
        "editing a many2one (with form view opened with external button)",
        async function (assert) {
            assert.expect(1);
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    '<field name="trululu"/>' +
                    "</sheet>" +
                    "</form>",
                archs: {
                    "partner,false,form": '<form string="Partners"><field name="foo"/></form>',
                },
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === "get_formview_id") {
                        return Promise.resolve(false);
                    }
                    return this._super(route, args);
                },
                viewOptions: {
                    ids: [1, 2],
                },
            });

            await testUtils.form.clickEdit(form);

            // click on the external button (should do an RPC)
            await testUtils.dom.click(form.$(".o_external_button"));

            await testUtils.fields.editInput($('.modal input[name="foo"]'), "brandon");

            // save and close modal
            await testUtils.dom.click($(".modal .modal-footer .btn-primary:first"));
            // save form
            await testUtils.form.clickSave(form);
            // click next on pager
            await testUtils.dom.click(form.el.querySelector(".o_pager .o_pager_next"));

            // this checks that the view did not ask for confirmation that the
            // record is dirty
            assert.strictEqual(
                form.el.querySelector(".o_pager").innerText.trim(),
                "2 / 2",
                "pager should be at second page"
            );
            form.destroy();
        }
    );

    QUnit.skip("many2ones in form views with show_address", async function (assert) {
        assert.expect(6);
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                "<field " +
                'name="trululu" ' +
                'string="custom label" ' +
                "context=\"{'show_address': 1}\" " +
                "options=\"{'always_reload': True}\"" +
                "/>" +
                "</group>" +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "name_get") {
                    return this._super(route, args).then(function (result) {
                        result[0][1] += "\nStreet\nCity ZIP";
                        return result;
                    });
                }
                return this._super(route, args);
            },
            res_id: 1,
        });

        assert.strictEqual(
            form.$("a.o_form_uri").html(),
            "<span>aaa</span><br><span>Street</span><br><span>City ZIP</span>",
            "input should have a multi-line content in readonly due to show_address"
        );
        await testUtils.form.clickEdit(form);

        assert.strictEqual(form.$("input.o_input").val(), "aaa");
        assert.strictEqual(
            form.$(".o_field_many2one_extra").html(),
            "<span>Street</span><br><span>City ZIP</span>"
        );

        assert.containsOnce(
            form,
            "button.o_external_button:visible",
            "should have an open record button"
        );

        testUtils.dom.click(form.$("input.o_input"));

        assert.containsOnce(
            form,
            "button.o_external_button:visible",
            "should still have an open record button"
        );
        form.$("input.o_input").trigger("focusout");
        assert.strictEqual(
            $(".modal button:contains(Create and edit)").length,
            0,
            "there should not be a quick create modal"
        );

        form.destroy();
    });

    QUnit.skip("many2one show_address in edit", async function (assert) {
        assert.expect(6);

        const addresses = {
            aaa: "\nAAA\nRecord",
            "first record": "\nFirst\nRecord",
            "second record": "\nSecond\nRecord",
        };

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form><sheet><group>
                    <field name="trululu" context="{'show_address': 1}" options="{'always_reload': True}"/>
                </group></sheet></form>
            `,
            mockRPC: function (route, args) {
                if (args.method === "name_get") {
                    return this._super(route, args).then(function (result) {
                        result[0][1] += addresses[result[0][1]];
                        return result;
                    });
                }
                return this._super(route, args);
            },
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.strictEqual(form.$("input").val(), "aaa");
        assert.strictEqual(
            form.$(".o_field_many2one_extra").html(),
            "<span>AAA</span><br><span>Record</span>"
        );

        await testUtils.fields.editInput(form.$("input"), "first record");
        await testUtils.fields.many2one.clickHighlightedItem("trululu");

        assert.strictEqual(form.$("input").val(), "first record");
        assert.strictEqual(
            form.$(".o_field_many2one_extra").html(),
            "<span>First</span><br><span>Record</span>"
        );

        await testUtils.fields.editInput(form.$("input"), "second record");
        await testUtils.fields.many2one.clickHighlightedItem("trululu");
        assert.strictEqual(form.$("input").val(), "second record");
        assert.strictEqual(
            form.$(".o_field_many2one_extra").html(),
            "<span>Second</span><br><span>Record</span>"
        );

        form.destroy();
    });

    QUnit.skip(
        "show_address works in a view embedded in a view of another type",
        async function (assert) {
            assert.expect(2);

            this.data.turtle.records[1].turtle_trululu = 2;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="turtles"/>' +
                    "</form>",
                res_id: 1,
                archs: {
                    "turtle,false,form":
                        '<form string="T">' +
                        '<field name="display_name"/>' +
                        '<field name="turtle_trululu" context="{\'show_address\': 1}" options="{\'always_reload\': True}"/>' +
                        "</form>",
                    "turtle,false,list": "<tree>" + '<field name="display_name"/>' + "</tree>",
                },
                mockRPC: function (route, args) {
                    if (args.method === "name_get") {
                        return this._super(route, args).then(function (result) {
                            if (args.model === "partner" && args.kwargs.context.show_address) {
                                result[0][1] += "\nrue morgue\nparis 75013";
                            }
                            return result;
                        });
                    }
                    return this._super(route, args);
                },
            });
            // click the turtle field, opens a modal with the turtle form view
            await testUtils.dom.click(form.$(".o_data_row:first td.o_data_cell"));

            assert.strictEqual(
                $('[name="turtle_trululu"] .o_input').val(),
                "second record",
                "many2one value should be displayed in input"
            );
            assert.strictEqual(
                $('[name="turtle_trululu"] .o_field_many2one_extra').text(),
                "rue morgueparis 75013",
                "The partner's address should be displayed"
            );
            form.destroy();
        }
    );

    QUnit.skip(
        "many2one data is reloaded if there is a context to take into account",
        async function (assert) {
            assert.expect(2);

            this.data.turtle.records[1].turtle_trululu = 2;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="turtles"/>' +
                    "</form>",
                res_id: 1,
                archs: {
                    "turtle,false,form":
                        '<form string="T">' +
                        '<field name="display_name"/>' +
                        '<field name="turtle_trululu" context="{\'show_address\': 1}" options="{\'always_reload\': True}"/>' +
                        "</form>",
                    "turtle,false,list":
                        "<tree>" +
                        '<field name="display_name"/>' +
                        '<field name="turtle_trululu"/>' +
                        "</tree>",
                },
                mockRPC: function (route, args) {
                    if (args.method === "name_get") {
                        return this._super(route, args).then(function (result) {
                            if (args.model === "partner" && args.kwargs.context.show_address) {
                                result[0][1] += "\nrue morgue\nparis 75013";
                            }
                            return result;
                        });
                    }
                    return this._super(route, args);
                },
            });
            // click the turtle field, opens a modal with the turtle form view
            await testUtils.dom.click(form.$(".o_data_row:first"));

            assert.strictEqual(
                $('.modal [name="turtle_trululu"] .o_input').val(),
                "second record",
                "many2one value should be displayed in input"
            );
            assert.strictEqual(
                $(".modal [name=turtle_trululu] .o_field_many2one_extra").text(),
                "rue morgueparis 75013",
                "The partner's address should be displayed"
            );
            form.destroy();
        }
    );

    QUnit.skip("many2ones in form views with search more", async function (assert) {
        assert.expect(3);
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

        // add custom filter needs this
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

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
            archs: {
                "partner,false,list": '<tree><field name="display_name"/></tree>',
                "partner,false,search": '<search><field name="datetime"/></search>',
            },
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        await testUtils.fields.many2one.clickItem("trululu", "Search");

        assert.strictEqual($("tr.o_data_row").length, 9, "should display 9 records");

        const modal = document.body.querySelector(".modal");

        await cpHelpers.toggleFilterMenu(modal);
        await cpHelpers.toggleAddCustomFilter(modal);
        assert.strictEqual(
            modal.querySelector(".o_generator_menu_field").value,
            "datetime",
            "datetime field should be selected"
        );
        await cpHelpers.applyFilter(modal);

        assert.strictEqual($("tr.o_data_row").length, 0, "should display 0 records");
        form.destroy();
    });

    QUnit.skip(
        "onchanges on many2ones trigger when editing record in form view",
        async function (assert) {
            assert.expect(10);

            this.data.partner.onchanges.user_id = function () {};
            this.data.user.fields.other_field = { string: "Other Field", type: "char" };
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    "<group>" +
                    '<field name="user_id"/>' +
                    "</group>" +
                    "</sheet>" +
                    "</form>",
                archs: {
                    "user,false,form": '<form string="Users"><field name="other_field"/></form>',
                },
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    if (args.method === "get_formview_id") {
                        return Promise.resolve(false);
                    }
                    if (args.method === "onchange") {
                        assert.strictEqual(
                            args.args[1].user_id,
                            17,
                            "onchange is triggered with correct user_id"
                        );
                    }
                    return this._super(route, args);
                },
            });

            // open the many2one in form view and change something
            await testUtils.form.clickEdit(form);
            await testUtils.dom.click(form.$(".o_external_button"));
            await testUtils.fields.editInput($('.modal-body input[name="other_field"]'), "wood");

            // save the modal and make sure an onchange is triggered
            await testUtils.dom.click($(".modal .modal-footer .btn-primary").first());
            assert.verifySteps([
                "read",
                "get_formview_id",
                "load_views",
                "read",
                "write",
                "read",
                "onchange",
            ]);

            // save the main record, and check that no extra rpcs are done (record
            // is not dirty, only a related record was modified)
            await testUtils.form.clickSave(form);
            assert.verifySteps([]);
            form.destroy();
        }
    );

    QUnit.skip("many2one doesn't trigger field_change when being emptied", async function (assert) {
        assert.expect(2);

        const list = await createView({
            arch: `
                <tree multi_edit="1">
                    <field name="trululu"/>
                </tree>`,
            data: this.data,
            model: "partner",
            View: ListView,
        });

        // Select two records
        await testUtils.dom.click(list.$(".o_data_row:eq(0) .o_list_record_selector input"));
        await testUtils.dom.click(list.$(".o_data_row:eq(1) .o_list_record_selector input"));

        await testUtils.dom.click(list.$(".o_data_row:first() .o_data_cell:first()"));

        const $input = list.$(".o_field_widget[name=trululu] input");

        await testUtils.fields.editInput($input, "");
        await testUtils.dom.triggerEvents($input, ["keyup"]);

        assert.containsNone(
            document.body,
            ".modal",
            "No save should be triggered when removing value"
        );

        await testUtils.fields.many2one.clickHighlightedItem("trululu");

        assert.containsOnce(
            document.body,
            ".modal",
            "Saving should be triggered when selecting a value"
        );
        await testUtils.dom.click($(".modal .btn-primary"));

        list.destroy();
    });

    QUnit.skip("focus tracking on a many2one in a list", async function (assert) {
        assert.expect(4);

        const list = await createView({
            arch: '<tree editable="top"><field name="trululu"/></tree>',
            archs: {
                "partner,false,form": '<form string="Partners"><field name="foo"/></form>',
            },
            data: this.data,
            model: "partner",
            View: ListView,
        });

        // Select two records
        await testUtils.dom.click(list.$(".o_data_row:eq(0) .o_list_record_selector input"));
        await testUtils.dom.click(list.$(".o_data_row:eq(1) .o_list_record_selector input"));

        await testUtils.dom.click(list.$(".o_data_row:first() .o_data_cell:first()"));

        const input = list.$(".o_data_row:first() .o_data_cell:first() input")[0];

        assert.strictEqual(document.activeElement, input, "Input should be focused when activated");

        await testUtils.fields.many2one.createAndEdit("trululu", "ABC");

        // At this point, if the focus is correctly registered by the m2o, there
        // should be only one modal (the "Create" one) and none for saving changes.
        assert.containsOnce(document.body, ".modal", "There should be only one modal");

        await testUtils.dom.click($(".modal .btn:not(.btn-primary)"));

        assert.strictEqual(
            document.activeElement,
            input,
            "Input should be focused after dialog closes"
        );
        assert.strictEqual(input.value, "", "Input should be empty after discard");

        list.destroy();
    });

    QUnit.test('many2one fields with option "no_open"', async function (assert) {
        assert.expect(3);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="trululu" options="{'no_open': 1}" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        assert.containsOnce(
            form,
            "span.o_field_widget[name='trululu']",
            "should be displayed inside a span (sanity check)"
        );
        assert.containsNone(form, "span.o_form_uri", "should not have an anchor");

        await click(form.el, ".o_form_button_edit");
        assert.containsNone(
            form,
            ".o_field_widget[name='trululu'] .o_external_button",
            "should not have the button to open the record"
        );
    });

    QUnit.test("empty many2one field", async function (assert) {
        assert.expect(4);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form string="Partners">
                    <sheet>
                        <group>
                            <field name="trululu" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        await click(form.el, ".o_field_many2one input");
        assert.containsNone(
            document.body,
            ".dropdown-menu li.o_m2o_dropdown_option",
            "autocomplete should not contains dropdown options"
        );
        assert.containsOnce(
            document.body,
            ".dropdown-menu li.o_m2o_start_typing",
            "autocomplete should contains start typing option"
        );

        const input = form.el.querySelector(".o_field_many2one[name='trululu'] input");
        input.value = "abc";
        await triggerEvents(input, null, ["input", "change"]);

        assert.containsN(
            document.body,
            ".dropdown-menu li.o_m2o_dropdown_option",
            2,
            "autocomplete should contains 2 dropdown options"
        );
        assert.containsNone(
            document.body,
            ".dropdown-menu li.o_m2o_start_typing",
            "autocomplete should not contains start typing option"
        );
    });

    QUnit.test("empty many2one field with node options", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form string="Partners">
                    <sheet>
                        <group>
                            <field name="trululu" options="{'no_create_edit': 1}" />
                            <field name="product_id" options="{'no_create_edit': 1, 'no_quick_create': 1}" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        const $dropdownTrululu = $(form.el)
            .find(".o_field_many2one[name='trululu'] input")
            .autocomplete("widget");
        const $dropdownProduct = $(form.el)
            .find(".o_field_many2one[name='product_id'] input")
            .autocomplete("widget");

        await click(form.el, ".o_field_many2one[name='trululu'] input");
        assert.containsOnce(
            $dropdownTrululu,
            "li.o_m2o_start_typing",
            "autocomplete should contains start typing option"
        );

        await click(form.el, ".o_field_many2one[name='product_id'] input");
        assert.containsNone(
            $dropdownProduct,
            "li.o_m2o_start_typing",
            "autocomplete should contains start typing option"
        );
    });

    QUnit.skip("many2one in edit mode", async function (assert) {
        assert.expect(17);

        // create 10 partners to have the 'Search More' option in the autocomplete dropdown
        for (var i = 0; i < 10; i++) {
            var id = 20 + i;
            this.data.partner.records.push({ id: id, display_name: "Partner " + id });
        }

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
                "partner,false,list": '<tree string="Partners"><field name="display_name"/></tree>',
                "partner,false,search":
                    '<search string="Partners">' +
                    '<field name="display_name" string="Name"/>' +
                    "</search>",
            },
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(args.args[1].trululu, 20, "should write the correct id");
                }
                return this._super.apply(this, arguments);
            },
        });

        // the SelectCreateDialog requests the session, so intercept its custom
        // event to specify a fake session to prevent it from crashing
        testUtils.mock.intercept(form, "get_session", function (event) {
            event.data.callback({ user_context: {} });
        });

        await testUtils.form.clickEdit(form);

        var $dropdown = form.$(".o_field_many2one input").autocomplete("widget");

        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        assert.ok(
            $dropdown.is(":visible"),
            "clicking on the m2o input should open the dropdown if it is not open yet"
        );
        assert.strictEqual(
            $dropdown.find("li:not(.o_m2o_dropdown_option)").length,
            7,
            "autocomplete should contains 8 suggestions"
        );
        assert.strictEqual(
            $dropdown.find("li.o_m2o_dropdown_option").length,
            1,
            'autocomplete should contain "Search More"'
        );
        assert.containsNone(
            $dropdown,
            "li.o_m2o_start_typing",
            "autocomplete should not contains start typing option if value is available"
        );

        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        assert.ok(
            !$dropdown.is(":visible"),
            "clicking on the m2o input should close the dropdown if it is open"
        );

        // change the value of the m2o with a suggestion of the dropdown
        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        await testUtils.fields.many2one.clickHighlightedItem("trululu");
        assert.ok(!$dropdown.is(":visible"), "clicking on a value should close the dropdown");
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "first record",
            "value of the m2o should have been correctly updated"
        );

        // change the value of the m2o with a record in the 'Search More' modal
        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        // click on 'Search More' (mouseenter required by ui-autocomplete)
        await testUtils.fields.many2one.clickItem("trululu", "Search");
        assert.ok($(".modal .o_list_view").length, "should have opened a list view in a modal");
        assert.ok(
            !$(".modal .o_list_view .o_list_record_selector").length,
            "there should be no record selector in the list view"
        );
        assert.ok(
            !$(".modal .modal-footer .o_select_button").length,
            "there should be no 'Select' button in the footer"
        );
        assert.ok($(".modal tbody tr").length > 10, "list should contain more than 10 records");
        const modal = document.body.querySelector(".modal");
        await cpHelpers.editSearch(modal, "P");
        await cpHelpers.validateSearch(modal);
        assert.strictEqual(
            $(".modal tbody tr").length,
            10,
            "list should be restricted to records containing a P (10 records)"
        );
        // choose a record
        await testUtils.dom.click($(".modal tbody tr:contains(Partner 20)"));
        assert.ok(!$(".modal").length, "should have closed the modal");
        assert.ok(!$dropdown.is(":visible"), "should have closed the dropdown");
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "Partner 20",
            "value of the m2o should have been correctly updated"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$("a.o_form_uri").text(),
            "Partner 20",
            "should display correct value after save"
        );

        form.destroy();
    });

    QUnit.test("many2one in non edit mode", async function (assert) {
        assert.expect(3);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="trululu" />
                </form>
            `,
        });

        assert.containsOnce(form.el, "a.o_form_uri", "should display 1 m2o link in form");
        assert.hasAttrValue(
            form.el.querySelector("a.o_form_uri"),
            "href",
            "#id=4&model=partner",
            "href should contain id and model"
        );

        // Remove value from many2one and then save, there should not have href with id and model on m2o anchor
        await click(form.el, ".o_form_button_edit");

        const input = form.el.querySelector(".o_field_many2one input");
        input.value = "";
        await triggerEvent(input, null, "change");

        await click(form.el, ".o_form_button_save");
        assert.hasAttrValue(
            form.el.querySelector("a.o_form_uri"),
            "href",
            "#",
            "href should have #"
        );
    });

    QUnit.skip("many2one with co-model whose name field is a many2one", async function (assert) {
        assert.expect(4);

        this.data.product.fields.name = {
            string: "User Name",
            type: "many2one",
            relation: "user",
        };

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="product_id"/></form>',
            archs: {
                "product,false,form": '<form><field name="name"/></form>',
            },
        });

        await testUtils.fields.many2one.createAndEdit("product_id", "ABC");
        assert.containsOnce(document.body, ".modal .o_form_view");

        // quick create 'new value'
        await testUtils.fields.many2one.searchAndClickItem("name", { search: "new value" });
        assert.strictEqual($(".modal .o_field_many2one input").val(), "new value");

        await testUtils.dom.click($(".modal .modal-footer .btn-primary")); // save in modal
        assert.containsNone(document.body, ".modal .o_form_view");
        assert.strictEqual(form.$(".o_field_many2one input").val(), "new value");

        form.destroy();
    });

    QUnit.test("many2one searches with correct value", async function (assert) {
        assert.expect(6);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="trululu" />
                    </sheet>
                </form>
            `,
            mockRPC(route, { method, kwargs }) {
                if (method === "name_search") {
                    assert.step(`search: ${kwargs.name}`);
                }
            },
        });
        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector(".o_field_many2one input").value,
            "aaa",
            "should be initially set to 'aaa'"
        );

        const input = form.el.querySelector(".o_field_many2one input");
        await click(input);

        // unset the many2one -> should search again with ''
        input.value = "";
        await triggerEvents(input, null, ["input", "change"]);

        input.value = "p";
        await triggerEvents(input, null, ["input", "change"]);

        // close and re-open the dropdown -> should search with 'p' again
        await click(input);
        await click(input);

        assert.verifySteps(["search: ", "search: ", "search: p", "search: p"]);
    });

    QUnit.skip("many2one search with trailing and leading spaces", async function (assert) {
        assert.expect(10);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form><field name="trululu"/></form>`,
            mockRPC: function (route, args) {
                if (args.method === "name_search") {
                    assert.step("search: " + args.kwargs.name);
                }
                return this._super.apply(this, arguments);
            },
        });

        const $dropdown = form.$(".o_field_many2one input").autocomplete("widget");

        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        assert.isVisible($dropdown);
        assert.containsN(
            $dropdown,
            "li:not(.o_m2o_dropdown_option)",
            4,
            "autocomplete should contains 4 suggestions"
        );

        // search with leading spaces
        form.$(".o_field_many2one input").val("   first").trigger("keydown").trigger("keyup");
        await testUtils.nextTick();
        assert.containsOnce(
            $dropdown,
            "li:not(.o_m2o_dropdown_option)",
            "autocomplete should contains 1 suggestion"
        );

        // search with trailing spaces
        form.$(".o_field_many2one input").val("first  ").trigger("keydown").trigger("keyup");
        await testUtils.nextTick();
        assert.containsOnce(
            $dropdown,
            "li:not(.o_m2o_dropdown_option)",
            "autocomplete should contains 1 suggestion"
        );

        // search with leading and trailing spaces
        form.$(".o_field_many2one input").val("   first   ").trigger("keydown").trigger("keyup");
        await testUtils.nextTick();
        assert.containsOnce(
            $dropdown,
            "li:not(.o_m2o_dropdown_option)",
            "autocomplete should contains 1 suggestion"
        );

        assert.verifySteps(["search: ", "search: first", "search: first", "search: first"]);

        form.destroy();
    });

    QUnit.skip("many2one field with option always_reload", async function (assert) {
        assert.expect(4);
        var count = 0;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="trululu" options="{\'always_reload\': True}"/>' +
                "</form>",
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === "name_get") {
                    count++;
                    return Promise.resolve([[1, "first record\nand some address"]]);
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(count, 1, "an extra name_get should have been done");
        assert.ok(
            form.$("a:contains(and some address)").length,
            "should display additional result"
        );

        await testUtils.form.clickEdit(form);

        assert.strictEqual(
            form.$(".o_field_widget[name=trululu] input").val(),
            "first record",
            "actual field value should be displayed to be edited"
        );

        await testUtils.form.clickSave(form);

        assert.ok(
            form.$("a:contains(and some address)").length,
            "should still display additional result"
        );
        form.destroy();
    });

    QUnit.skip("many2one field and list navigation", async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom"><field name="trululu"/></tree>',
        });

        // edit first input, to trigger autocomplete
        await testUtils.dom.click(list.$(".o_data_row .o_data_cell").first());
        await testUtils.fields.editInput(list.$(".o_data_cell input"), "");

        // press keydown, to select first choice
        await testUtils.fields.triggerKeydown(list.$(".o_data_cell input").focus(), "down");

        // we now check that the dropdown is open (and that the focus did not go
        // to the next line)
        var $dropdown = list.$(".o_field_many2one input").autocomplete("widget");
        assert.ok($dropdown.is(":visible"), "dropdown should be visible");
        assert.hasClass(
            list.$(".o_data_row:eq(0)"),
            "o_selected_row",
            "first data row should still be selected"
        );
        assert.doesNotHaveClass(
            list.$(".o_data_row:eq(1)"),
            "o_selected_row",
            "second data row should not be selected"
        );

        list.destroy();
    });

    QUnit.skip("standalone many2one field", async function (assert) {
        assert.expect(4);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var fixture = $("#qunit-fixture");
        var self = this;

        var model = await testUtils.createModel({
            Model: BasicModel,
            data: this.data,
        });
        var record;
        model
            .makeRecord("coucou", [
                {
                    name: "partner_id",
                    relation: "partner",
                    type: "many2one",
                    value: [1, "first partner"],
                },
            ])
            .then(function (recordID) {
                record = model.get(recordID);
            });
        await testUtils.nextTick();
        // create a new widget that uses the StandaloneFieldManagerMixin
        var StandaloneWidget = Widget.extend(StandaloneFieldManagerMixin, {
            init: function (parent) {
                this._super.apply(this, arguments);
                StandaloneFieldManagerMixin.init.call(this, parent);
            },
        });
        var parent = new StandaloneWidget(model);
        model.setParent(parent);
        await testUtils.mock.addMockEnvironment(parent, {
            data: self.data,
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        var relField = new relationalFields.FieldMany2One(parent, "partner_id", record, {
            mode: "edit",
            noOpen: true,
        });

        relField.appendTo(fixture);
        await testUtils.nextTick();
        await testUtils.fields.editInput($("input.o_input"), "xyzzrot");

        await testUtils.fields.many2one.clickItem("partner_id", "Create");

        assert.containsNone(
            relField,
            ".o_external_button",
            "should not have the button to open the record"
        );
        assert.verifySteps(["name_search", "name_create"]);

        parent.destroy();
        model.destroy();
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
    });

    // QUnit.skip('onchange on a many2one to a different model', async function (assert) {
    // This test is commented because the mock server does not give the correct response.
    // It should return a couple [id, display_name], but I don't know the logic used
    // by the server, so it's hard to emulate it correctly
    //     assert.expect(2);

    //     this.data.partner.records[0].product_id = 41;
    //     this.data.partner.onchanges = {
    //         foo: function(obj) {
    //             obj.product_id = 37;
    //         },
    //     };

    //     var form = await createView({
    //         View: FormView,
    //         model: 'partner',
    //         data: this.data,
    //         arch: '<form>' +
    //                 '<field name="foo"/>' +
    //                 '<field name="product_id"/>' +
    //             '</form>',
    //         res_id: 1,
    //     });
    //     await testUtils.form.clickEdit(form);
    //     assert.strictEqual(form.$('input').eq(1).val(), 'xpad', "initial product_id val should be xpad");

    //     testUtils.fields.editInput(form.$('input').eq(0), "let us trigger an onchange");

    //     assert.strictEqual(form.$('input').eq(1).val(), 'xphone', "onchange should have been applied");
    // });

    QUnit.skip("form: quick create then save directly", async function (assert) {
        assert.expect(5);

        var prom = testUtils.makeTestPromise();
        var newRecordID;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: "<form>" + '<field name="trululu"/>' + "</form>",
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "name_create") {
                    assert.step("name_create");
                    return prom.then(_.constant(result)).then(function (nameGet) {
                        newRecordID = nameGet[0];
                        return nameGet;
                    });
                }
                if (args.method === "create") {
                    assert.step("create");
                    assert.strictEqual(
                        args.args[0].trululu,
                        newRecordID,
                        "should create with the correct m2o id"
                    );
                }
                return result;
            },
        });
        await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "b" });
        await testUtils.form.clickSave(form);

        assert.verifySteps(
            ["name_create"],
            "should wait for the name_create before creating the record"
        );

        await prom.resolve();
        await testUtils.nextTick();

        assert.verifySteps(["create"]);
        form.destroy();
    });

    QUnit.skip(
        "form: quick create for field that returns false after name_create call",
        async function (assert) {
            assert.expect(3);
            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: '<form><field name="trululu"/></form>',
                mockRPC: function (route, args) {
                    const result = this._super.apply(this, arguments);
                    if (args.method === "name_create") {
                        assert.step("name_create");
                        // Resolve the name_create call to false. This is possible if
                        // _rec_name for the model of the field is unassigned.
                        return Promise.resolve(false);
                    }
                    return result;
                },
            });
            await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "beam" });
            assert.verifySteps(["name_create"], "attempt to name_create");
            assert.strictEqual(
                form.$(".o_input_dropdown input").val(),
                "",
                "the input should contain no text after search and click"
            );
            form.destroy();
        }
    );

    QUnit.skip("list: quick create then save directly", async function (assert) {
        assert.expect(8);

        var prom = testUtils.makeTestPromise();
        var newRecordID;
        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="top">' + '<field name="trululu"/>' + "</tree>",
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "name_create") {
                    assert.step("name_create");
                    return prom.then(_.constant(result)).then(function (nameGet) {
                        newRecordID = nameGet[0];
                        return nameGet;
                    });
                }
                if (args.method === "create") {
                    assert.step("create");
                    assert.strictEqual(
                        args.args[0].trululu,
                        newRecordID,
                        "should create with the correct m2o id"
                    );
                }
                return result;
            },
        });

        await testUtils.dom.click(list.$buttons.find(".o_list_button_add"));

        await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "b" });
        list.$buttons.find(".o_list_button_add").show();
        testUtils.dom.click(list.$buttons.find(".o_list_button_add"));

        assert.verifySteps(
            ["name_create"],
            "should wait for the name_create before creating the record"
        );
        assert.containsN(
            list,
            ".o_data_row",
            4,
            "should wait for the name_create before adding the new row"
        );

        await prom.resolve();
        await testUtils.nextTick();

        assert.verifySteps(["create"]);
        assert.strictEqual(
            list.$(".o_data_row:nth(1) .o_data_cell").text(),
            "b",
            "created row should have the correct m2o value"
        );
        assert.containsN(list, ".o_data_row", 5, "should have added the fifth row");

        list.destroy();
    });

    QUnit.skip("list in form: quick create then save directly", async function (assert) {
        assert.expect(6);

        var prom = testUtils.makeTestPromise();
        var newRecordID;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="p">' +
                '<tree editable="bottom">' +
                '<field name="trululu"/>' +
                "</tree>" +
                "</field>" +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "name_create") {
                    assert.step("name_create");
                    return prom.then(_.constant(result)).then(function (nameGet) {
                        newRecordID = nameGet[0];
                        return nameGet;
                    });
                }
                if (args.method === "create") {
                    assert.step("create");
                    assert.strictEqual(
                        args.args[0].p[0][2].trululu,
                        newRecordID,
                        "should create with the correct m2o id"
                    );
                }
                return result;
            },
        });

        await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
        await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "b" });
        await testUtils.form.clickSave(form);

        assert.verifySteps(
            ["name_create"],
            "should wait for the name_create before creating the record"
        );

        await prom.resolve();
        await testUtils.nextTick();

        assert.verifySteps(["create"]);
        assert.strictEqual(
            form.$(".o_data_row:first .o_data_cell").text(),
            "b",
            "first row should have the correct m2o value"
        );
        form.destroy();
    });

    QUnit.skip("list in form: quick create then add a new line directly", async function (assert) {
        // required many2one inside a one2many list: directly after quick creating
        // a new many2one value (before the name_create returns), click on add an item:
        // at this moment, the many2one has still no value, and as it is required,
        // the row is discarded if a saveLine is requested. However, it should
        // wait for the name_create to return before trying to save the line.
        assert.expect(8);

        this.data.partner.onchanges = {
            trululu: function () {},
        };

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var prom = testUtils.makeTestPromise();
        var newRecordID;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="p">' +
                '<tree editable="bottom">' +
                '<field name="trululu" required="1"/>' +
                "</tree>" +
                "</field>" +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "name_create") {
                    return prom.then(_.constant(result)).then(function (nameGet) {
                        newRecordID = nameGet[0];
                        return nameGet;
                    });
                }
                if (args.method === "create") {
                    assert.deepEqual(args.args[0].p[0][2].trululu, newRecordID);
                }
                return result;
            },
        });

        await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
        await testUtils.fields.editAndTrigger(form.$(".o_field_many2one input"), "b", "keydown");
        await testUtils.fields.many2one.clickHighlightedItem("trululu");
        await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));

        assert.containsOnce(form, ".o_data_row", "there should still be only one row");
        assert.hasClass(
            form.$(".o_data_row"),
            "o_selected_row",
            "the row should still be in edition"
        );

        await prom.resolve();
        await testUtils.nextTick();

        assert.strictEqual(
            form.$(".o_data_row:first .o_data_cell").text(),
            "b",
            "first row should have the correct m2o value"
        );
        assert.containsN(form, ".o_data_row", 2, "there should now be 2 rows");
        assert.hasClass(
            form.$(".o_data_row:nth(1)"),
            "o_selected_row",
            "the second row should be in edition"
        );

        await testUtils.form.clickSave(form);

        assert.containsOnce(
            form,
            ".o_data_row",
            "there should be 1 row saved (the second one was empty and invalid)"
        );
        assert.strictEqual(
            form.$(".o_data_row .o_data_cell").text(),
            "b",
            "should have the correct m2o value"
        );

        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        form.destroy();
    });

    QUnit.skip("list in form: create with one2many with many2one", async function (assert) {
        assert.expect(1);

        this.data.partner.fields.p.default = [[0, 0, { display_name: "new record", p: [] }]];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="p">' +
                '<tree editable="bottom">' +
                '<field name="display_name"/>' +
                '<field name="trululu"/>' +
                "</tree>" +
                "</field>" +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "name_get") {
                    throw new Error("Nameget should not be called");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(
            $("td.o_data_cell:first").text(),
            "new record",
            "should have created the new record in the o2m with the correct name"
        );

        form.destroy();
    });

    QUnit.skip(
        "list in form: create with one2many with many2one (version 2)",
        async function (assert) {
            // This test simulates the exact same scenario as the previous one,
            // except that the value for the many2one is explicitely set to false,
            // which is stupid, but this happens, so we have to handle it
            assert.expect(1);

            this.data.partner.fields.p.default = [
                [0, 0, { display_name: "new record", trululu: false, p: [] }],
            ];

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    "<sheet>" +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '<field name="trululu"/>' +
                    "</tree>" +
                    "</field>" +
                    "</sheet>" +
                    "</form>",
                mockRPC: function (route, args) {
                    if (args.method === "name_get") {
                        throw new Error("Nameget should not be called");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.strictEqual(
                $("td.o_data_cell:first").text(),
                "new record",
                "should have created the new record in the o2m with the correct name"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "item not dropped on discard with empty required field (default_get)",
        async function (assert) {
            // This test simulates discarding a record that has been created with
            // one of its required field that is empty. When we discard the changes
            // on this empty field, it should not assume that this record should be
            // abandonned, since it has been added (even though it is a new record).
            assert.expect(8);

            this.data.partner.fields.p.default = [
                [0, 0, { display_name: "new record", trululu: false, p: [] }],
            ];

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    "<sheet>" +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '<field name="trululu" required="1"/>' +
                    "</tree>" +
                    "</field>" +
                    "</sheet>" +
                    "</form>",
            });

            assert.strictEqual(
                $("tr.o_data_row").length,
                1,
                "should have created the new record in the o2m"
            );
            assert.strictEqual(
                $("td.o_data_cell").first().text(),
                "new record",
                "should have the correct displayed name"
            );

            var requiredElement = $("td.o_data_cell.o_required_modifier");
            assert.strictEqual(
                requiredElement.length,
                1,
                "should have a required field on this record"
            );
            assert.strictEqual(
                requiredElement.text(),
                "",
                "should have empty string in the required field on this record"
            );

            testUtils.dom.click(requiredElement);
            // discard by clicking on body
            testUtils.dom.click($("body"));

            assert.strictEqual(
                $("tr.o_data_row").length,
                1,
                "should still have the record in the o2m"
            );
            assert.strictEqual(
                $("td.o_data_cell").first().text(),
                "new record",
                "should still have the correct displayed name"
            );

            // update selector of required field element
            requiredElement = $("td.o_data_cell.o_required_modifier");
            assert.strictEqual(
                requiredElement.length,
                1,
                "should still have the required field on this record"
            );
            assert.strictEqual(
                requiredElement.text(),
                "",
                "should still have empty string in the required field on this record"
            );
            form.destroy();
        }
    );

    QUnit.skip("list in form: name_get with unique ids (default_get)", async function (assert) {
        assert.expect(1);

        this.data.partner.records[0].display_name = "MyTrululu";
        this.data.partner.fields.p.default = [
            [0, 0, { trululu: 1, p: [] }],
            [0, 0, { trululu: 1, p: [] }],
        ];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="p">' +
                '<tree editable="bottom">' +
                '<field name="trululu"/>' +
                "</tree>" +
                "</field>" +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "name_get") {
                    throw new Error("should not call name_get");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(
            form.$("td.o_data_cell").text(),
            "MyTrululuMyTrululu",
            "both records should have the correct display_name for trululu field"
        );

        form.destroy();
    });

    QUnit.skip(
        "list in form: show name of many2one fields in multi-page (default_get)",
        async function (assert) {
            assert.expect(4);

            this.data.partner.fields.p.default = [
                [0, 0, { display_name: "record1", trululu: 1, p: [] }],
                [0, 0, { display_name: "record2", trululu: 2, p: [] }],
            ];

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    "<sheet>" +
                    '<field name="p">' +
                    '<tree editable="bottom" limit="1">' +
                    '<field name="display_name"/>' +
                    '<field name="trululu"/>' +
                    "</tree>" +
                    "</field>" +
                    "</sheet>" +
                    "</form>",
            });

            assert.strictEqual(
                form.$("td.o_data_cell").first().text(),
                "record1",
                "should show display_name of 1st record"
            );
            assert.strictEqual(
                form.$("td.o_data_cell").first().next().text(),
                "first record",
                "should show display_name of trululu of 1st record"
            );

            await testUtils.dom.click(form.$("button.o_pager_next"));

            assert.strictEqual(
                form.$("td.o_data_cell").first().text(),
                "record2",
                "should show display_name of 2nd record"
            );
            assert.strictEqual(
                form.$("td.o_data_cell").first().next().text(),
                "second record",
                "should show display_name of trululu of 2nd record"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "list in form: item not dropped on discard with empty required field (onchange in default_get)",
        async function (assert) {
            // variant of the test "list in form: discard newly added element with
            // empty required field (default_get)", in which the `default_get`
            // performs an `onchange` at the same time. This `onchange` may create
            // some records, which should not be abandoned on discard, similarly
            // to records created directly by `default_get`
            assert.expect(7);

            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

            this.data.partner.fields.product_id.default = 37;
            this.data.partner.onchanges = {
                product_id: function (obj) {
                    if (obj.product_id === 37) {
                        obj.p = [[0, 0, { display_name: "entry", trululu: false }]];
                    }
                },
            };

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="product_id"/>' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '<field name="trululu" required="1"/>' +
                    "</tree>" +
                    "</field>" +
                    "</form>",
            });

            // check that there is a record in the editable list with empty string as required field
            assert.containsOnce(form, ".o_data_row", "should have a row in the editable list");
            assert.strictEqual(
                $("td.o_data_cell").first().text(),
                "entry",
                "should have the correct displayed name"
            );
            var requiredField = $("td.o_data_cell.o_required_modifier");
            assert.strictEqual(
                requiredField.length,
                1,
                "should have a required field on this record"
            );
            assert.strictEqual(
                requiredField.text(),
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            testUtils.dom.click(requiredField);
            // click off so that the required field still stay empty
            testUtils.dom.click($("body"));

            // record should not be dropped
            assert.containsOnce(
                form,
                ".o_data_row",
                "should not have dropped record in the editable list"
            );
            assert.strictEqual(
                $("td.o_data_cell").first().text(),
                "entry",
                "should still have the correct displayed name"
            );
            assert.strictEqual(
                $("td.o_data_cell.o_required_modifier").text(),
                "",
                "should still have empty string in the required field"
            );

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
        }
    );

    QUnit.skip(
        "list in form: item not dropped on discard with empty required field (onchange on list after default_get)",
        async function (assert) {
            // discarding a record from an `onchange` in a `default_get` should not
            // abandon the record. This should not be the case for following
            // `onchange`, except if an onchange make some changes on the list:
            // in particular, if an onchange make changes on the list such that
            // a record is added, this record should not be dropped on discard
            assert.expect(8);

            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

            this.data.partner.onchanges = {
                product_id: function (obj) {
                    if (obj.product_id === 37) {
                        obj.p = [[0, 0, { display_name: "entry", trululu: false }]];
                    }
                },
            };

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="product_id"/>' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '<field name="trululu" required="1"/>' +
                    "</tree>" +
                    "</field>" +
                    "</form>",
            });

            // check no record in list
            assert.containsNone(form, ".o_data_row", "should have no row in the editable list");

            // select product_id to force on_change in editable list
            await testUtils.dom.click(form.$('.o_field_widget[name="product_id"] .o_input'));
            await testUtils.dom.click($(".ui-menu-item").first());

            // check that there is a record in the editable list with empty string as required field
            assert.containsOnce(form, ".o_data_row", "should have a row in the editable list");
            assert.strictEqual(
                $("td.o_data_cell").first().text(),
                "entry",
                "should have the correct displayed name"
            );
            var requiredField = $("td.o_data_cell.o_required_modifier");
            assert.strictEqual(
                requiredField.length,
                1,
                "should have a required field on this record"
            );
            assert.strictEqual(
                requiredField.text(),
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            await testUtils.dom.click(requiredField);
            // click off so that the required field still stay empty
            await testUtils.dom.click($("body"));

            // record should not be dropped
            assert.containsOnce(
                form,
                ".o_data_row",
                "should not have dropped record in the editable list"
            );
            assert.strictEqual(
                $("td.o_data_cell").first().text(),
                "entry",
                "should still have the correct displayed name"
            );
            assert.strictEqual(
                $("td.o_data_cell.o_required_modifier").text(),
                "",
                "should still have empty string in the required field"
            );

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
        }
    );

    QUnit.skip(
        'item dropped on discard with empty required field with "Add an item" (invalid on "ADD")',
        async function (assert) {
            // when a record in a list is added with "Add an item", it should
            // always be dropped on discard if some required field are empty
            // at the record creation.
            assert.expect(6);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '<field name="trululu" required="1"/>' +
                    "</tree>" +
                    "</field>" +
                    "</form>",
            });

            // Click on "Add an item"
            await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
            var charField = form.$('.o_field_widget.o_field_char[name="display_name"]');
            var requiredField = form.$('.o_field_widget.o_required_modifier[name="trululu"]');
            charField.val("some text");
            assert.strictEqual(
                charField.length,
                1,
                "should have a char field 'display_name' on this record"
            );
            assert.doesNotHaveClass(
                charField,
                "o_required_modifier",
                "the char field should not be required on this record"
            );
            assert.strictEqual(
                charField.val(),
                "some text",
                "should have entered text in the char field on this record"
            );
            assert.strictEqual(
                requiredField.length,
                1,
                "should have a required field 'trululu' on this record"
            );
            assert.strictEqual(
                requiredField.val().trim(),
                "",
                "should have empty string in the required field on this record"
            );

            // click on empty required field in editable list record
            await testUtils.dom.click(requiredField);
            // click off so that the required field still stay empty
            await testUtils.dom.click($("body"));

            // record should be dropped
            assert.containsNone(
                form,
                ".o_data_row",
                "should have dropped record in the editable list"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        'item not dropped on discard with empty required field with "Add an item" (invalid on "UPDATE")',
        async function (assert) {
            // when a record in a list is added with "Add an item", it should
            // be temporarily added to the list when it is valid (e.g. required
            // fields are non-empty). If the record is updated so that the required
            // field is empty, and it is discarded, then the record should not be
            // dropped.
            assert.expect(8);

            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '<field name="trululu" required="1"/>' +
                    "</tree>" +
                    "</field>" +
                    "</form>",
            });

            assert.containsNone(
                form,
                ".o_data_row",
                "should initially not have any record in the list"
            );

            // Click on "Add an item"
            await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
            assert.containsOnce(form, ".o_data_row", "should have a temporary record in the list");

            var $inputEditMode = form.$(
                '.o_field_widget.o_required_modifier[name="trululu"] input'
            );
            assert.strictEqual(
                $inputEditMode.length,
                1,
                "should have a required field 'trululu' on this record"
            );
            assert.strictEqual(
                $inputEditMode.val(),
                "",
                "should have empty string in the required field on this record"
            );

            // add something to required field and leave edit mode of the record
            await testUtils.dom.click($inputEditMode);
            await testUtils.dom.click($("li.ui-menu-item").first());
            await testUtils.dom.click($("body"));

            var $inputReadonlyMode = form.$(".o_data_cell.o_required_modifier");
            assert.containsOnce(
                form,
                ".o_data_row",
                "should not have dropped valid record when leaving edit mode"
            );
            assert.strictEqual(
                $inputReadonlyMode.text(),
                "first record",
                "should have put some content in the required field on this record"
            );

            // remove the required field and leave edit mode of the record
            await testUtils.dom.click($(".o_data_row"));
            assert.containsOnce(
                form,
                ".o_data_row",
                "should not have dropped record in the list on discard (invalid on UPDATE)"
            );
            assert.strictEqual(
                $inputReadonlyMode.text(),
                "first record",
                "should keep previous valid required field content on this record"
            );

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
        }
    );

    QUnit.skip("list in form: default_get with x2many create", async function (assert) {
        assert.expect(3);
        this.data.partner.fields.timmy.default = [
            [0, 0, { display_name: "brandon is the new timmy", name: "brandon" }],
        ];
        var displayName = "brandon is the new timmy";
        this.data.partner.onchanges.timmy = function (obj) {
            obj.int_field = obj.timmy.length;
        };

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="timmy">' +
                '<tree editable="bottom">' +
                '<field name="display_name"/>' +
                "</tree>" +
                "</field>" +
                '<field name="int_field"/>' +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    assert.deepEqual(
                        args.args[0],
                        {
                            int_field: 2,
                            timmy: [
                                [6, false, []],
                                // LPE TODO 1 taskid-2261084: remove this entire comment including code snippet
                                // when the change in behavior has been thoroughly tested.
                                // We can't distinguish a value coming from a default_get
                                // from one coming from the onchange, and so we can either store and
                                // send it all the time, or never.
                                // [0, args.args[0].timmy[1][1], { display_name: displayName, name: 'brandon' }],
                                [0, args.args[0].timmy[1][1], { display_name: displayName }],
                            ],
                        },
                        "should send the correct values to create"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(
            $("td.o_data_cell:first").text(),
            "brandon is the new timmy",
            "should have created the new record in the m2m with the correct name"
        );
        assert.strictEqual(
            $("input.o_field_integer").val(),
            "1",
            "should have called and executed the onchange properly"
        );

        // edit the subrecord and save
        displayName = "new value";
        await testUtils.dom.click(form.$(".o_data_cell"));
        await testUtils.fields.editInput(form.$(".o_data_cell input"), displayName);
        await testUtils.form.clickSave(form);

        form.destroy();
    });

    QUnit.skip(
        "list in form: default_get with x2many create and onchange",
        async function (assert) {
            assert.expect(1);

            this.data.partner.fields.turtles.default = [[6, 0, [2, 3]]];

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    "<sheet>" +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    "</tree>" +
                    "</field>" +
                    '<field name="int_field"/>' +
                    "</sheet>" +
                    "</form>",
                mockRPC: function (route, args) {
                    if (args.method === "create") {
                        assert.deepEqual(
                            args.args[0].turtles,
                            [
                                [4, 2, false],
                                [4, 3, false],
                            ],
                            "should send proper commands to create method"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await testUtils.form.clickSave(form);

            form.destroy();
        }
    );

    QUnit.skip("list in form: call button in sub view", async function (assert) {
        assert.expect(11);

        this.data.partner.records[0].p = [2];
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="p">' +
                '<tree editable="bottom">' +
                '<field name="product_id"/>' +
                "</tree>" +
                "</field>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/product/get_formview_id") {
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (event) {
                    assert.strictEqual(
                        event.data.env.model,
                        "product",
                        "should call with correct model in env"
                    );
                    assert.strictEqual(
                        event.data.env.currentID,
                        37,
                        "should call with correct currentID in env"
                    );
                    assert.deepEqual(
                        event.data.env.resIDs,
                        [37],
                        "should call with correct resIDs in env"
                    );
                    assert.step(event.data.action_data.name);
                },
            },
            archs: {
                "product,false,form":
                    '<form string="Partners">' +
                    "<header>" +
                    '<button name="action" type="action" string="Just do it !"/>' +
                    '<button name="object" type="object" string="Just don\'t do it !"/>' +
                    '<field name="display_name"/>' +
                    "</header>" +
                    "</form>",
            },
        });

        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$("td.o_data_cell:first"));
        await testUtils.dom.click(form.$(".o_external_button"));
        await testUtils.dom.click($('button:contains("Just do it !")'));
        assert.verifySteps(["action"]);
        await testUtils.dom.click($('button:contains("Just don\'t do it !")'));
        assert.verifySteps([]); // the second button is disabled, it can't be clicked

        await testUtils.dom.click($(".modal .btn-secondary:contains(Discard)"));
        await testUtils.dom.click(form.$(".o_external_button"));
        await testUtils.dom.click($('button:contains("Just don\'t do it !")'));
        assert.verifySteps(["object"]);
        form.destroy();
    });

    QUnit.skip("X2Many sequence list in modal", async function (assert) {
        assert.expect(5);

        this.data.partner.fields.sequence = { string: "Sequence", type: "integer" };
        this.data.partner.records[0].sequence = 1;
        this.data.partner.records[1].sequence = 2;
        this.data.partner.onchanges = {
            sequence: function (obj) {
                if (obj.id === 2) {
                    obj.sequence = 1;
                    assert.step("onchange sequence");
                }
            },
        };

        this.data.product.fields.turtle_ids = {
            string: "Turtles",
            type: "one2many",
            relation: "turtle",
        };
        this.data.product.records[0].turtle_ids = [1];

        this.data.turtle.fields.partner_types_ids = {
            string: "Partner",
            type: "one2many",
            relation: "partner",
        };
        this.data.turtle.fields.type_id = {
            string: "Partner Type",
            type: "many2one",
            relation: "partner_type",
        };

        this.data.partner_type.fields.partner_ids = {
            string: "Partner",
            type: "one2many",
            relation: "partner",
        };
        this.data.partner_type.records[0].partner_ids = [1, 2];

        var form = await createView({
            View: FormView,
            model: "product",
            data: this.data,
            arch:
                "<form>" +
                '<field name="name"/>' +
                '<field name="turtle_ids" widget="one2many">' +
                '<tree string="Turtles" editable="bottom">' +
                '<field name="type_id"/>' +
                "</tree>" +
                "</field>" +
                "</form>",
            archs: {
                "partner_type,false,form": '<form><field name="partner_ids"/></form>',
                "partner,false,list":
                    '<tree string="Vendors">' +
                    '<field name="display_name"/>' +
                    '<field name="sequence" widget="handle"/>' +
                    "</tree>",
            },
            res_id: 37,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/product/read") {
                    return Promise.resolve([
                        { id: 37, name: "xphone", display_name: "leonardo", turtle_ids: [1] },
                    ]);
                }
                if (route === "/web/dataset/call_kw/turtle/read") {
                    return Promise.resolve([{ id: 1, type_id: [12, "gold"] }]);
                }
                if (route === "/web/dataset/call_kw/partner_type/get_formview_id") {
                    return Promise.resolve(false);
                }
                if (route === "/web/dataset/call_kw/partner_type/read") {
                    return Promise.resolve([{ id: 12, partner_ids: [1, 2], display_name: "gold" }]);
                }
                if (route === "/web/dataset/call_kw/partner_type/write") {
                    assert.step("partner_type write");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$(".o_data_cell"));
        await testUtils.dom.click(form.$(".o_external_button"));

        var $modal = $(".modal");
        assert.equal($modal.length, 1, "There should be 1 modal opened");

        var $handles = $modal.find(".ui-sortable-handle");
        assert.equal($handles.length, 2, "There should be 2 sequence handlers");

        await testUtils.dom.dragAndDrop($handles.eq(1), $modal.find("tbody tr").first(), {
            position: "top",
        });

        // Saving the modal and then the original model
        await testUtils.dom.click($modal.find(".modal-footer .btn-primary"));
        await testUtils.form.clickSave(form);

        assert.verifySteps(["onchange sequence", "partner_type write"]);

        form.destroy();
    });

    QUnit.skip("autocompletion in a many2one, in form view with a domain", async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: "<form>" + '<field name="product_id"/>' + "</form>",
            res_id: 1,
            viewOptions: {
                domain: [["trululu", "=", 4]],
            },
            mockRPC: function (route, args) {
                if (args.method === "name_search") {
                    assert.deepEqual(args.kwargs.args, [], "should not have a domain");
                }
                return this._super(route, args);
            },
        });
        await testUtils.form.clickEdit(form);

        testUtils.dom.click(form.$(".o_field_widget[name=product_id] input"));
        form.destroy();
    });

    QUnit.skip(
        "autocompletion in a many2one, in form view with a date field",
        async function (assert) {
            assert.expect(1);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="bar"/>' +
                    '<field name="date"/>' +
                    "<field name=\"trululu\" domain=\"[('bar','=',True)]\"/>" +
                    "</form>",
                res_id: 2,
                mockRPC: function (route, args) {
                    if (args.method === "name_search") {
                        assert.deepEqual(
                            args.kwargs.args,
                            [["bar", "=", true]],
                            "should not have a domain"
                        );
                    }
                    return this._super(route, args);
                },
            });
            await testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$(".o_field_widget[name=trululu] input"));
            form.destroy();
        }
    );

    QUnit.skip("creating record with many2one with option always_reload", async function (assert) {
        assert.expect(2);

        this.data.partner.fields.trululu.default = 1;
        this.data.partner.onchanges = {
            trululu: function (obj) {
                obj.trululu = 2; //[2, "second record"];
            },
        };

        var count = 0;

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="trululu" options="{\'always_reload\': True}"/>' +
                "</form>",
            mockRPC: function (route, args) {
                count++;
                if (args.method === "name_get" && args.args[0] === 2) {
                    return Promise.resolve([[2, "hello world\nso much noise"]]);
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(count, 2, "should have done 2 rpcs (onchange and name_get)");
        assert.strictEqual(
            form.$(".o_field_widget[name=trululu] input").val(),
            "hello world",
            "should have taken the correct display name"
        );
        form.destroy();
    });

    QUnit.skip("selecting a many2one, then discarding", async function (assert) {
        assert.expect(3);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners">' + '<field name="product_id"/>' + "</form>",
            res_id: 1,
        });
        assert.strictEqual(form.$("a[name=product_id]").text(), "", "the tag a should be empty");
        await testUtils.form.clickEdit(form);

        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickItem("product_id", "xphone");
        assert.strictEqual(
            form.$(".o_field_widget[name=product_id] input").val(),
            "xphone",
            "should have selected xphone"
        );

        await testUtils.form.clickDiscard(form);
        assert.strictEqual(form.$("a[name=product_id]").text(), "", "the tag a should be empty");
        form.destroy();
    });

    QUnit.skip(
        "domain and context are correctly used when doing a name_search in a m2o",
        async function (assert) {
            assert.expect(4);

            this.data.partner.records[0].timmy = [12];

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="product_id" ' +
                    "domain=\"[['foo', '=', 'bar'], ['foo', '=', foo]]\" " +
                    "context=\"{'hello': 'world', 'test': foo}\"/>" +
                    '<field name="foo"/>' +
                    "<field name=\"trululu\" context=\"{'timmy': timmy}\" domain=\"[['id', 'in', timmy]]\"/>" +
                    '<field name="timmy" widget="many2many_tags" invisible="1"/>' +
                    "</form>",
                res_id: 1,
                session: { user_context: { hey: "ho" } },
                mockRPC: function (route, args) {
                    if (args.method === "name_search" && args.model === "product") {
                        assert.deepEqual(
                            args.kwargs.args,
                            [
                                ["foo", "=", "bar"],
                                ["foo", "=", "yop"],
                            ],
                            "the field attr domain should have been used for the RPC (and evaluated)"
                        );
                        assert.deepEqual(
                            args.kwargs.context,
                            { hey: "ho", hello: "world", test: "yop" },
                            "the field attr context should have been used for the " +
                                "RPC (evaluated and merged with the session one)"
                        );
                        return Promise.resolve([]);
                    }
                    if (args.method === "name_search" && args.model === "partner") {
                        assert.deepEqual(
                            args.kwargs.args,
                            [["id", "in", [12]]],
                            "the field attr domain should have been used for the RPC (and evaluated)"
                        );
                        assert.deepEqual(
                            args.kwargs.context,
                            { hey: "ho", timmy: [[6, false, [12]]] },
                            "the field attr context should have been used for the RPC (and evaluated)"
                        );
                        return Promise.resolve([]);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$(".o_field_widget[name=product_id] input"));

            testUtils.dom.click(form.$(".o_field_widget[name=trululu] input"));

            form.destroy();
        }
    );

    QUnit.skip("quick create on a many2one", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="product_id"/>' +
                "</sheet>" +
                "</form>",
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/product/name_create") {
                    assert.strictEqual(
                        args.args[0],
                        "new partner",
                        "should name create a new product"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.triggerEvent(form.$(".o_field_many2one input"), "focus");
        await testUtils.fields.editAndTrigger(form.$(".o_field_many2one input"), "new partner", [
            "keyup",
            "blur",
        ]);
        await testUtils.dom.click($(".modal .modal-footer .btn-primary").first());
        assert.strictEqual(
            $(".modal .modal-body").text().trim(),
            "Create new partner as a new Product?"
        );

        form.destroy();
    });

    QUnit.skip("failing quick create on a many2one", async function (assert) {
        assert.expect(4);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="product_id"/></form>',
            archs: {
                "product,false,form": '<form><field name="name"/></form>',
            },
            mockRPC(route, args) {
                if (args.method === "name_create") {
                    return Promise.reject();
                }
                if (args.method === "create") {
                    assert.deepEqual(args.args[0], { name: "xyz" });
                }
                return this._super(...arguments);
            },
        });

        await testUtils.fields.many2one.searchAndClickItem("product_id", {
            search: "abcd",
            item: 'Create "abcd"',
        });
        assert.containsOnce(document.body, ".modal .o_form_view");
        assert.strictEqual($(".o_field_widget[name=name]").val(), "abcd");

        await testUtils.fields.editInput($(".modal .o_field_widget[name=name]"), "xyz");
        await testUtils.dom.click($(".modal .modal-footer .btn-primary"));
        assert.strictEqual(form.$(".o_field_widget[name=product_id] input").val(), "xyz");

        form.destroy();
    });

    QUnit.skip("failing quick create on a many2one inside a one2many", async function (assert) {
        assert.expect(4);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="p"/></form>',
            archs: {
                "partner,false,list": '<tree editable="bottom"><field name="product_id"/></tree>',
                "product,false,form": '<form><field name="name"/></form>',
            },
            mockRPC(route, args) {
                if (args.method === "name_create") {
                    return Promise.reject();
                }
                if (args.method === "create") {
                    assert.deepEqual(args.args[0], { name: "xyz" });
                }
                return this._super(...arguments);
            },
        });

        await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
        await testUtils.fields.many2one.searchAndClickItem("product_id", {
            search: "abcd",
            item: 'Create "abcd"',
        });
        assert.containsOnce(document.body, ".modal .o_form_view");
        assert.strictEqual($(".o_field_widget[name=name]").val(), "abcd");

        await testUtils.fields.editInput($(".modal .o_field_widget[name=name]"), "xyz");
        await testUtils.dom.click($(".modal .modal-footer .btn-primary"));
        assert.strictEqual(form.$(".o_field_widget[name=product_id] input").val(), "xyz");

        form.destroy();
    });

    QUnit.skip("slow create on a many2one", async function (assert) {
        assert.expect(11);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                "<sheet>" +
                '<field name="product_id" options="{\'quick_create\': False}"/>' +
                "</sheet>" +
                "</form>",
            archs: {
                "product,false,form": "<form>" + '<field name="name"/>' + "</form>",
            },
        });

        // cancel the many2one creation with Discard button
        form.$(".o_field_many2one input")
            .focus()
            .val("new product")
            .trigger("input")
            .trigger("keyup");
        await testUtils.nextTick();
        form.$(".o_field_many2one input").trigger("blur");
        await testUtils.nextTick();
        assert.strictEqual($(".modal").length, 1, "there should be one opened modal");

        await testUtils.dom.click($(".modal .modal-footer .btn:contains(Discard)"));
        assert.strictEqual($(".modal").length, 0, "the modal should be closed");
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "",
            "the many2one should not set a value as its creation has been cancelled (with Cancel button)"
        );

        // cancel the many2one creation with Close button
        form.$(".o_field_many2one input")
            .focus()
            .val("new product")
            .trigger("input")
            .trigger("keyup");
        await testUtils.nextTick();
        form.$(".o_field_many2one input").trigger("blur");
        await testUtils.nextTick();
        assert.strictEqual($(".modal").length, 1, "there should be one opened modal");
        await testUtils.dom.click($(".modal .modal-header button"));
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "",
            "the many2one should not set a value as its creation has been cancelled (with Close button)"
        );
        assert.strictEqual($(".modal").length, 0, "the modal should be closed");

        // select a new value then cancel the creation of the new one --> restore the previous
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickItem("product_id", "o");
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "xphone",
            "should have selected xphone"
        );

        form.$(".o_field_many2one input")
            .focus()
            .val("new product")
            .trigger("input")
            .trigger("keyup");
        await testUtils.nextTick();
        form.$(".o_field_many2one input").trigger("blur");
        await testUtils.nextTick();
        assert.strictEqual($(".modal").length, 1, "there should be one opened modal");

        await testUtils.dom.click($(".modal .modal-footer .btn:contains(Discard)"));
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "xphone",
            "should have restored the many2one with its previous selected value (xphone)"
        );

        // confirm the many2one creation
        form.$(".o_field_many2one input")
            .focus()
            .val("new product")
            .trigger("input")
            .trigger("keyup");
        await testUtils.nextTick();
        form.$(".o_field_many2one input").trigger("blur");
        await testUtils.nextTick();
        assert.strictEqual($(".modal").length, 1, "there should be one opened modal");

        await testUtils.dom.click($(".modal .modal-footer .btn-primary:contains(Create)"));
        assert.strictEqual(
            $(".modal .o_form_view").length,
            1,
            "a new modal should be opened and contain a form view"
        );

        await testUtils.dom.click($(".modal .o_form_button_cancel"));

        form.destroy();
    });

    QUnit.skip("select a many2one value by focusing out", async function (assert) {
        assert.expect(3);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form><field name="product_id"/></form>`,
        });

        form.$(".o_field_many2one input").focus().val("xph").trigger("input").trigger("keyup");
        await testUtils.nextTick();
        form.$(".o_field_many2one input").trigger("blur");
        await testUtils.nextTick();

        assert.containsNone(document.body, ".modal");
        assert.strictEqual(form.$(".o_field_many2one input").val(), "xphone");
        assert.containsOnce(form, ".o_external_button");

        form.destroy();
    });

    QUnit.skip("no_create option on a many2one", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="product_id" options="{\'no_create\': True}"/>' +
                "</sheet>" +
                "</form>",
        });

        await testUtils.fields.editInput(form.$(".o_field_many2one input"), "new partner");
        form.$(".o_field_many2one input").trigger("keyup").trigger("focusout");
        assert.strictEqual($(".modal").length, 0, "should not display the create modal");
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "",
            "many2one value should cleared on focusout if many2one is no_create"
        );
        form.destroy();
    });

    QUnit.skip("can_create and can_write option on a many2one", async function (assert) {
        assert.expect(5);

        this.data.product.options = {
            can_create: "false",
            can_write: "false",
        };

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                '<field name="product_id" can_create="false" can_write="false"/>' +
                "</sheet>" +
                "</form>",
            archs: {
                "product,false,form": '<form string="Products"><field name="display_name"/></form>',
            },
            mockRPC: function (route) {
                if (route === "/web/dataset/call_kw/product/get_formview_id") {
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(form.$(".o_field_many2one input"));
        assert.strictEqual(
            $(".ui-autocomplete .o_m2o_dropdown_option:contains(Create)").length,
            0,
            "there shouldn't be any option to search and create"
        );

        await testUtils.dom.click($(".ui-autocomplete li:contains(xpad)").mouseenter());
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "xpad",
            "the correct record should be selected"
        );
        assert.containsOnce(
            form,
            ".o_field_many2one .o_external_button",
            "there should be an external button displayed"
        );

        await testUtils.dom.click(form.$(".o_field_many2one .o_external_button"));
        assert.strictEqual(
            $(".modal .o_form_view.o_form_readonly").length,
            1,
            "there should be a readonly form view opened"
        );

        await testUtils.dom.click($(".modal .o_form_button_cancel"));

        await testUtils.fields.editAndTrigger(form.$(".o_field_many2one input"), "new product", [
            "keyup",
            "focusout",
        ]);
        assert.strictEqual($(".modal").length, 0, "should not display the create modal");
        form.destroy();
    });

    QUnit.skip(
        "many2one with can_create=false shows no result item when searched something that doesn't exist",
        async function (assert) {
            assert.expect(2);

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `<form string="Partners">
                <sheet>
                    <field name="product_id" can_create="false" can_write="false"/>
                </sheet>
            </form>`,
            });

            await testUtils.dom.click(form.$(".o_field_many2one input"));
            await testUtils.fields.editAndTrigger(
                form.$('.o_field_many2one[name="product_id"] input'),
                "abc",
                "keydown"
            );
            await testUtils.nextTick();
            assert.strictEqual(
                $(".ui-autocomplete .o_m2o_dropdown_option:contains(Create)").length,
                0,
                "there shouldn't be any option to search and create"
            );
            assert.strictEqual(
                $(".ui-autocomplete .ui-menu-item a:contains(No records)").length,
                1,
                "there should be option for 'No records'"
            );

            form.destroy();
        }
    );

    QUnit.skip("pressing enter in a m2o in an editable list", async function (assert) {
        assert.expect(8);
        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom"><field name="product_id"/></tree>',
        });

        await testUtils.dom.click(list.$("td.o_data_cell:first"));
        assert.containsOnce(list, ".o_selected_row", "should have a row in edit mode");

        // we now write 'a' and press enter to check that the selection is
        // working, and prevent the navigation
        await testUtils.fields.editInput(list.$("td.o_data_cell input:first"), "a");
        var $input = list.$("td.o_data_cell input:first");
        var $dropdown = $input.autocomplete("widget");
        assert.ok($dropdown.is(":visible"), "autocomplete dropdown should be visible");

        // we now trigger ENTER to select first choice
        await testUtils.fields.triggerKeydown($input, "enter");
        assert.strictEqual($input[0], document.activeElement, "input should still be focused");

        // we now trigger again ENTER to make sure we can move to next line
        await testUtils.fields.triggerKeydown($input, "enter");

        assert.notOk(document.contains($input[0]), "input should no longer be in dom");
        assert.hasClass(
            list.$("tr.o_data_row:eq(1)"),
            "o_selected_row",
            "second row should now be selected"
        );

        // we now write again 'a' in the cell to select xpad. We will now
        // test with the tab key
        await testUtils.fields.editInput(list.$("td.o_data_cell input:first"), "a");
        var $input = list.$("td.o_data_cell input:first");
        var $dropdown = $input.autocomplete("widget");
        assert.ok($dropdown.is(":visible"), "autocomplete dropdown should be visible");
        await testUtils.fields.triggerKeydown($input, "tab");

        assert.notOk(document.contains($input[0]), "input should no longer be in dom");
        assert.hasClass(
            list.$("tr.o_data_row:eq(2)"),
            "o_selected_row",
            "third row should now be selected"
        );
        list.destroy();
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
    });

    QUnit.skip(
        "pressing ENTER on a 'no_quick_create' many2one should open a M2ODialog",
        async function (assert) {
            assert.expect(2);

            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="trululu" options="{\'no_quick_create\': True}"/>' +
                    '<field name="foo"/>' +
                    "</form>",
                archs: {
                    "partner,false,form":
                        '<form string="Partners"><field name="display_name"/></form>',
                },
            });

            var $input = form.$(".o_field_many2one input");
            await testUtils.fields.editInput($input, "Something that does not exist");
            $(".ui-autocomplete .ui-menu-item a:contains(Create and)").trigger("mouseenter");
            await testUtils.nextTick();
            await testUtils.fields.triggerKey("down", $input, "enter");
            await testUtils.fields.triggerKey("press", $input, "enter");
            await testUtils.fields.triggerKey("up", $input, "enter");
            $input.blur();
            assert.strictEqual($(".modal").length, 1, "should have one modal in body");
            // Check that discarding clears $input
            await testUtils.dom.click($(".modal .o_form_button_cancel"));
            assert.strictEqual($input.val(), "", "the field should be empty");
            form.destroy();
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        }
    );

    QUnit.skip(
        "select a value by pressing TAB on a many2one with onchange",
        async function (assert) {
            assert.expect(3);

            this.data.partner.onchanges.trululu = function () {};

            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;
            var prom = testUtils.makeTestPromise();

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="trululu"/>' +
                    '<field name="display_name"/>' +
                    "</form>",
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === "onchange") {
                        return prom.then(_.constant(result));
                    }
                    return result;
                },
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            var $input = form.$(".o_field_many2one input");
            await testUtils.fields.editAndTrigger($input, "first", ["keydown", "keyup"]);
            await testUtils.fields.triggerKey("down", $input, "tab");
            await testUtils.fields.triggerKey("press", $input, "tab");
            await testUtils.fields.triggerKey("up", $input, "tab");

            // simulate a focusout (e.g. because the user clicks outside)
            // before the onchange returns
            form.$(".o_field_char").focus();

            assert.strictEqual($(".modal").length, 0, "there shouldn't be any modal in body");

            // unlock the onchange
            prom.resolve();
            await testUtils.nextTick();

            assert.strictEqual(
                $input.val(),
                "first record",
                "first record should have been selected"
            );
            assert.strictEqual($(".modal").length, 0, "there shouldn't be any modal in body");
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
        }
    );

    QUnit.skip("leaving a many2one by pressing tab", async function (assert) {
        assert.expect(3);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form>
                    <field name="trululu"/>
                    <field name="display_name"/>
                </form>`,
        });

        const $input = form.$(".o_field_many2one input");
        await testUtils.dom.click($input);
        await testUtils.fields.triggerKeydown($input, "tab");
        assert.strictEqual($input.val(), "", "no record should have been selected");

        // open autocomplete dropdown and manually select item by UP/DOWN key and press TAB
        await testUtils.dom.click($input);
        await testUtils.fields.triggerKeydown($input, "down");
        await testUtils.fields.triggerKeydown($input, "tab");
        assert.strictEqual(
            $input.val(),
            "second record",
            "second record should have been selected"
        );

        // clear many2one and then open autocomplete, write something and press TAB
        await testUtils.fields.editAndTrigger(form.$(".o_field_many2one input"), "", [
            "keyup",
            "blur",
        ]);
        await testUtils.dom.triggerEvent($input, "focus");
        await testUtils.fields.editInput($input, "se");
        await testUtils.fields.triggerKeydown($input, "tab");
        assert.strictEqual($input.val(), "second record", "first record should have been selected");

        form.destroy();
    });

    QUnit.skip(
        "leaving an empty many2one by pressing tab (after backspace or delete)",
        async function (assert) {
            assert.expect(4);

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `<form>
                    <field name="trululu"/>
                    <field name="display_name"/>
                </form>`,
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            const $input = form.$(".o_field_many2one input");
            assert.ok($input.val(), "many2one should have value");

            // simulate backspace to remove values and press TAB
            await testUtils.fields.editInput($input, "");
            await testUtils.fields.triggerKeyup($input, "backspace");
            await testUtils.fields.triggerKeydown($input, "tab");
            assert.strictEqual($input.val(), "", "no record should have been selected");

            // reset a value
            await testUtils.fields.many2one.clickOpenDropdown("trululu");
            await testUtils.fields.many2one.clickItem("trululu", "first record");
            assert.ok($input.val(), "many2one should have value");

            // simulate delete to remove values and press TAB
            await testUtils.fields.editInput($input, "");
            await testUtils.fields.triggerKeyup($input, "delete");
            await testUtils.fields.triggerKeydown($input, "tab");
            assert.strictEqual($input.val(), "", "no record should have been selected");

            form.destroy();
        }
    );

    QUnit.skip(
        "many2one in editable list + onchange, with enter [REQUIRE FOCUS]",
        async function (assert) {
            assert.expect(6);
            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

            this.data.partner.onchanges.product_id = function (obj) {
                obj.int_field = obj.product_id || 0;
            };

            var prom = testUtils.makeTestPromise();

            var list = await createView({
                View: ListView,
                model: "partner",
                data: this.data,
                arch:
                    '<tree editable="bottom"><field name="product_id"/><field name="int_field"/></tree>',
                mockRPC: function (route, args) {
                    if (args.method) {
                        assert.step(args.method);
                    }
                    var result = this._super.apply(this, arguments);
                    if (args.method === "onchange") {
                        return prom.then(_.constant(result));
                    }
                    return result;
                },
            });

            await testUtils.dom.click(list.$("td.o_data_cell:first"));
            await testUtils.fields.editInput(list.$("td.o_data_cell input:first"), "a");
            var $input = list.$("td.o_data_cell input:first");
            await testUtils.fields.triggerKeydown($input, "enter");
            await testUtils.fields.triggerKey("up", $input, "enter");
            prom.resolve();
            await testUtils.nextTick();
            await testUtils.fields.triggerKeydown($input, "enter");
            assert.strictEqual($(".modal").length, 0, "should not have any modal in DOM");
            assert.verifySteps(["name_search", "onchange", "write", "read"]);
            list.destroy();
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        }
    );

    QUnit.skip(
        "many2one in editable list + onchange, with enter, part 2 [REQUIRE FOCUS]",
        async function (assert) {
            // this is the same test as the previous one, but the onchange is just
            // resolved slightly later
            assert.expect(6);
            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

            this.data.partner.onchanges.product_id = function (obj) {
                obj.int_field = obj.product_id || 0;
            };

            var prom = testUtils.makeTestPromise();

            var list = await createView({
                View: ListView,
                model: "partner",
                data: this.data,
                arch:
                    '<tree editable="bottom"><field name="product_id"/><field name="int_field"/></tree>',
                mockRPC: function (route, args) {
                    if (args.method) {
                        assert.step(args.method);
                    }
                    var result = this._super.apply(this, arguments);
                    if (args.method === "onchange") {
                        return prom.then(_.constant(result));
                    }
                    return result;
                },
            });

            await testUtils.dom.click(list.$("td.o_data_cell:first"));
            await testUtils.fields.editInput(list.$("td.o_data_cell input:first"), "a");
            var $input = list.$("td.o_data_cell input:first");
            await testUtils.fields.triggerKeydown($input, "enter");
            await testUtils.fields.triggerKey("up", $input, "enter");
            await testUtils.fields.triggerKeydown($input, "enter");
            prom.resolve();
            await testUtils.nextTick();
            assert.strictEqual($(".modal").length, 0, "should not have any modal in DOM");
            assert.verifySteps(["name_search", "onchange", "write", "read"]);
            list.destroy();
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        }
    );

    QUnit.skip("many2one: domain updated by an onchange", async function (assert) {
        assert.expect(2);

        this.data.partner.onchanges = {
            int_field: function () {},
        };

        var domain = [];
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: "<form>" + '<field name="int_field"/>' + '<field name="trululu"/>' + "</form>",
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "onchange") {
                    domain = [["id", "in", [10]]];
                    return Promise.resolve({
                        domain: {
                            trululu: domain,
                            unexisting_field: domain,
                        },
                    });
                }
                if (args.method === "name_search") {
                    assert.deepEqual(args.kwargs.args, domain, "sent domain should be correct");
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: "edit",
            },
        });

        // trigger a name_search (domain should be [])
        await testUtils.dom.click(form.$(".o_field_widget[name=trululu] input"));
        // close the dropdown
        await testUtils.dom.click(form.$(".o_field_widget[name=trululu] input"));
        // trigger an onchange that will update the domain
        await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), 2);
        // trigger a name_search (domain should be [['id', 'in', [10]]])
        await testUtils.dom.click(form.$(".o_field_widget[name=trululu] input"));

        form.destroy();
    });

    QUnit.skip("many2one in one2many: domain updated by an onchange", async function (assert) {
        assert.expect(3);

        this.data.partner.onchanges = {
            trululu: function () {},
        };

        var domain = [];
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="p">' +
                '<tree editable="bottom">' +
                '<field name="foo"/>' +
                '<field name="trululu"/>' +
                "</tree>" +
                "</field>" +
                "</form>",
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        domain: {
                            trululu: domain,
                        },
                    });
                }
                if (args.method === "name_search") {
                    assert.deepEqual(args.kwargs.args, domain, "sent domain should be correct");
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: "edit",
            },
        });

        // add a first row with a specific domain for the m2o
        domain = [["id", "in", [10]]]; // domain for subrecord 1
        await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
        await testUtils.dom.click(form.$(".o_field_widget[name=trululu] input"));
        // add some value to foo field to make record dirty
        await testUtils.fields.editInput(
            form.$('tr.o_selected_row input[name="foo"]'),
            "new value"
        );

        // add a second row with another domain for the m2o
        domain = [["id", "in", [5]]]; // domain for subrecord 2
        await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
        await testUtils.dom.click(form.$(".o_field_widget[name=trululu] input"));

        // check again the first row to ensure that the domain hasn't change
        domain = [["id", "in", [10]]]; // domain for subrecord 1 should have been kept
        await testUtils.dom.click(form.$(".o_data_row:first .o_data_cell:eq(1)"));
        await testUtils.dom.click(form.$(".o_field_widget[name=trululu] input"));

        form.destroy();
    });

    QUnit.skip("search more in many2one: no text in input", async function (assert) {
        // when the user clicks on 'Search More...' in a many2one dropdown, and there is no text
        // in the input (i.e. no value to search on), we bypass the name_search that is meant to
        // return a list of preselected ids to filter on in the list view (opened in a dialog)
        assert.expect(6);

        for (var i = 0; i < 8; i++) {
            this.data.partner.records.push({ id: 100 + i, display_name: "test_" + i });
        }

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="trululu"/></form>',
            archs: {
                "partner,false,list": '<list><field name="display_name"/></list>',
                "partner,false,search": "<search></search>",
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === "/web/dataset/search_read") {
                    assert.deepEqual(
                        args.domain,
                        [],
                        "should not preselect ids as there as nothing in the m2o input"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.fields.many2one.searchAndClickItem("trululu", {
            item: "Search More",
            search: "",
        });

        assert.verifySteps([
            "onchange",
            "name_search", // to display results in the dropdown
            "load_views", // list view in dialog
            "/web/dataset/search_read", // to display results in the dialog
        ]);

        form.destroy();
    });

    QUnit.skip("search more in many2one: text in input", async function (assert) {
        // when the user clicks on 'Search More...' in a many2one dropdown, and there is some
        // text in the input, we perform a name_search to get a (limited) list of preselected
        // ids and we add a dynamic filter (with those ids) to the search view in the dialog, so
        // that the user can remove this filter to bypass the limit
        assert.expect(12);

        for (var i = 0; i < 8; i++) {
            this.data.partner.records.push({ id: 100 + i, display_name: "test_" + i });
        }

        var expectedDomain;
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="trululu"/></form>',
            archs: {
                "partner,false,list": '<list><field name="display_name"/></list>',
                "partner,false,search": "<search></search>",
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === "/web/dataset/search_read") {
                    assert.deepEqual(args.domain, expectedDomain);
                }
                return this._super.apply(this, arguments);
            },
        });

        expectedDomain = [["id", "in", [100, 101, 102, 103, 104, 105, 106, 107]]];
        await testUtils.fields.many2one.searchAndClickItem("trululu", {
            item: "Search More",
            search: "test",
        });

        assert.containsOnce(document.body, ".modal .o_list_view");
        assert.containsOnce(
            document.body,
            ".modal .o_cp_searchview .o_facet_values",
            "should have a special facet for the pre-selected ids"
        );

        // remove the filter on ids
        expectedDomain = [];
        await testUtils.dom.click($(".modal .o_cp_searchview .o_facet_remove"));

        assert.verifySteps([
            "onchange",
            "name_search", // empty search, triggered when the user clicks in the input
            "name_search", // to display results in the dropdown
            "name_search", // to get preselected ids matching the search
            "load_views", // list view in dialog
            "/web/dataset/search_read", // to display results in the dialog
            "/web/dataset/search_read", // after removal of dynamic filter
        ]);

        form.destroy();
    });

    QUnit.skip("search more in many2one: dropdown click", async function (assert) {
        assert.expect(8);

        for (let i = 0; i < 8; i++) {
            this.data.partner.records.push({ id: 100 + i, display_name: "test_" + i });
        }

        // simulate modal-like element rendered by the field html
        const $fakeDialog = $(`<div>
            <div class="pouet">
                <div class="modal"></div>
            </div>
        </div>`);
        $("body").append($fakeDialog);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="trululu"/></form>',
            archs: {
                "partner,false,list": '<list><field name="display_name"/></list>',
                "partner,false,search": "<search></search>",
            },
        });
        await testUtils.fields.many2one.searchAndClickItem("trululu", {
            item: "Search More",
            search: "test",
        });

        // dropdown selector
        let filterMenuCss = ".o_search_options > .o_filter_menu";
        let groupByMenuCss = ".o_search_options > .o_group_by_menu";

        await testUtils.dom.click(document.querySelector(`${filterMenuCss} > .dropdown-toggle`));

        assert.hasClass(document.querySelector(filterMenuCss), "show");
        assert.isVisible(
            document.querySelector(`${filterMenuCss} > .dropdown-menu`),
            "the filter dropdown menu should be visible"
        );
        assert.doesNotHaveClass(document.querySelector(groupByMenuCss), "show");
        assert.isNotVisible(
            document.querySelector(`${groupByMenuCss} > .dropdown-menu`),
            "the Group by dropdown menu should be not visible"
        );

        await testUtils.dom.click(document.querySelector(`${groupByMenuCss} > .dropdown-toggle`));
        assert.hasClass(document.querySelector(groupByMenuCss), "show");
        assert.isVisible(
            document.querySelector(`${groupByMenuCss} > .dropdown-menu`),
            "the group by dropdown menu should be visible"
        );
        assert.doesNotHaveClass(document.querySelector(filterMenuCss), "show");
        assert.isNotVisible(
            document.querySelector(`${filterMenuCss} > .dropdown-menu`),
            "the filter dropdown menu should be not visible"
        );

        $fakeDialog.remove();
        form.destroy();
    });

    QUnit.skip("updating a many2one from a many2many", async function (assert) {
        assert.expect(4);

        this.data.turtle.records[1].turtle_trululu = 1;

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<group>" +
                '<field name="turtles">' +
                '<tree editable="bottom">' +
                '<field name="display_name"/>' +
                '<field name="turtle_trululu"/>' +
                "</tree>" +
                "</field>" +
                "</group>" +
                "</form>",
            res_id: 1,
            archs: {
                "partner,false,form": '<form string="Trululu"><field name="display_name"/></form>',
            },
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    assert.deepEqual(
                        args.args[0],
                        [1],
                        "should call get_formview_id with correct id"
                    );
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },
        });

        // Opening the modal
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$(".o_data_row td:contains(first record)"));
        await testUtils.dom.click(form.$(".o_external_button"));
        assert.strictEqual($(".modal").length, 1, "should have one modal in body");

        // Changing the 'trululu' value
        await testUtils.fields.editInput($('.modal input[name="display_name"]'), "test");
        await testUtils.dom.click($(".modal button.btn-primary"));

        // Test whether the value has changed
        assert.strictEqual($(".modal").length, 0, "the modal should be closed");
        assert.equal(
            form.$(".o_data_cell:contains(test)").text(),
            "test",
            "the partner name should have been updated to 'test'"
        );

        form.destroy();
    });

    QUnit.skip("search more in many2one: resequence inside dialog", async function (assert) {
        // when the user clicks on 'Search More...' in a many2one dropdown, resequencing inside
        // the dialog works
        assert.expect(10);

        this.data.partner.fields.sequence = { string: "Sequence", type: "integer" };
        for (var i = 0; i < 8; i++) {
            this.data.partner.records.push({ id: 100 + i, display_name: "test_" + i });
        }

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="trululu"/></form>',
            archs: {
                "partner,false,list":
                    "<list>" +
                    '<field name="sequence" widget="handle"/>' +
                    '<field name="display_name"/>' +
                    "</list>",
                "partner,false,search": "<search></search>",
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === "/web/dataset/search_read") {
                    assert.deepEqual(
                        args.domain,
                        [],
                        "should not preselect ids as there as nothing in the m2o input"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.fields.many2one.searchAndClickItem("trululu", {
            item: "Search More",
            search: "",
        });

        var $modal = $(".modal");
        assert.equal($modal.length, 1, "There should be 1 modal opened");

        var $handles = $modal.find(".ui-sortable-handle");
        assert.equal($handles.length, 11, "There should be 11 sequence handlers");

        await testUtils.dom.dragAndDrop($handles.eq(1), $modal.find("tbody tr").first(), {
            position: "top",
        });

        assert.verifySteps([
            "onchange",
            "name_search", // to display results in the dropdown
            "load_views", // list view in dialog
            "/web/dataset/search_read", // to display results in the dialog
            "/web/dataset/resequence", // resequencing lines
            "read",
        ]);

        form.destroy();
    });

    QUnit.skip("many2one dropdown disappears on scroll", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<div style="height: 2000px;">' +
                '<field name="trululu"/>' +
                "</div>" +
                "</form>",
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        var $input = form.$(".o_field_many2one input");

        await testUtils.dom.click($input);
        assert.isVisible($input.autocomplete("widget"), "dropdown should be opened");

        form.el.dispatchEvent(new Event("scroll"));
        assert.isNotVisible($input.autocomplete("widget"), "dropdown should be closed");

        form.destroy();
    });

    QUnit.skip("x2many list sorted by many2one", async function (assert) {
        assert.expect(3);

        this.data.partner.records[0].p = [1, 2, 4];
        this.data.partner.fields.trululu.sortable = true;

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="p">' +
                "<tree>" +
                '<field name="id"/>' +
                '<field name="trululu"/>' +
                "</tree>" +
                "</field>" +
                "</form>",
            res_id: 1,
        });

        assert.strictEqual(
            form.$(".o_data_row .o_list_number").text(),
            "124",
            "should have correct order initially"
        );

        await testUtils.dom.click(form.$(".o_list_view thead th:nth(1)"));

        assert.strictEqual(
            form.$(".o_data_row .o_list_number").text(),
            "412",
            "should have correct order (ASC)"
        );

        await testUtils.dom.click(form.$(".o_list_view thead th:nth(1)"));

        assert.strictEqual(
            form.$(".o_data_row .o_list_number").text(),
            "214",
            "should have correct order (DESC)"
        );

        form.destroy();
    });

    QUnit.skip("one2many with extra field from server not in form", async function (assert) {
        assert.expect(6);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="p" >' +
                "<tree>" +
                '<field name="datetime"/>' +
                '<field name="display_name"/>' +
                "</tree>" +
                "</field>" +
                "</form>",
            res_id: 1,
            archs: {
                "partner,false,form": "<form>" + '<field name="display_name"/>' + "</form>",
            },
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    args.args[1].p[0][2].datetime = "2018-04-05 12:00:00";
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.form.clickEdit(form);

        var x2mList = form.$(".o_field_x2many_list[name=p]");

        // Add a record in the list
        await testUtils.dom.click(x2mList.find(".o_field_x2many_list_row_add a"));

        var modal = $(".modal-lg");

        var nameInput = modal.find("input.o_input[name=display_name]");
        await testUtils.fields.editInput(nameInput, "michelangelo");

        // Save the record in the modal (though it is still virtual)
        await testUtils.dom.click(modal.find(".btn-primary").first());

        assert.equal(
            x2mList.find(".o_data_row").length,
            1,
            "There should be 1 records in the x2m list"
        );

        var newlyAdded = x2mList.find(".o_data_row").eq(0);

        assert.equal(
            newlyAdded.find(".o_data_cell").first().text(),
            "",
            "The create_date field should be empty"
        );
        assert.equal(
            newlyAdded.find(".o_data_cell").eq(1).text(),
            "michelangelo",
            "The display name field should have the right value"
        );

        // Save the whole thing
        await testUtils.form.clickSave(form);

        x2mList = form.$(".o_field_x2many_list[name=p]");

        // Redo asserts in RO mode after saving
        assert.equal(
            x2mList.find(".o_data_row").length,
            1,
            "There should be 1 records in the x2m list"
        );

        newlyAdded = x2mList.find(".o_data_row").eq(0);

        assert.equal(
            newlyAdded.find(".o_data_cell").first().text(),
            "04/05/2018 12:00:00",
            "The create_date field should have the right value"
        );
        assert.equal(
            newlyAdded.find(".o_data_cell").eq(1).text(),
            "michelangelo",
            "The display name field should have the right value"
        );

        form.destroy();
    });

    QUnit.skip(
        "one2many with extra field from server not in (inline) form",
        async function (assert) {
            assert.expect(1);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="p" >' +
                    "<tree>" +
                    '<field name="datetime"/>' +
                    '<field name="display_name"/>' +
                    "</tree>" +
                    "<form>" +
                    '<field name="display_name"/>' +
                    "</form>" +
                    "</field>" +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            var x2mList = form.$(".o_field_x2many_list[name=p]");

            // Add a record in the list
            await testUtils.dom.click(x2mList.find(".o_field_x2many_list_row_add a"));

            var modal = $(".modal-lg");

            var nameInput = modal.find("input.o_input[name=display_name]");
            await testUtils.fields.editInput(nameInput, "michelangelo");

            // Save the record in the modal (though it is still virtual)
            await testUtils.dom.click(modal.find(".btn-primary").first());

            assert.equal(
                x2mList.find(".o_data_row").length,
                1,
                "There should be 1 records in the x2m list"
            );

            form.destroy();
        }
    );

    QUnit.skip(
        "one2many with extra X2many field from server not in inline form",
        async function (assert) {
            assert.expect(1);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="p" >' +
                    "<tree>" +
                    '<field name="turtles"/>' +
                    '<field name="display_name"/>' +
                    "</tree>" +
                    "<form>" +
                    '<field name="display_name"/>' +
                    "</form>" +
                    "</field>" +
                    "</form>",
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            var x2mList = form.$(".o_field_x2many_list[name=p]");

            // Add a first record in the list
            await testUtils.dom.click(x2mList.find(".o_field_x2many_list_row_add a"));

            // Save & New
            await testUtils.dom.click($(".modal-lg").find(".btn-primary").eq(1));

            // Save & Close
            await testUtils.dom.click($(".modal-lg").find(".btn-primary").eq(0));

            assert.equal(
                x2mList.find(".o_data_row").length,
                2,
                "There should be 2 records in the x2m list"
            );

            form.destroy();
        }
    );

    QUnit.skip("one2many invisible depends on parent field", async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].p = [2];
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="product_id"/>' +
                "</group>" +
                "<notebook>" +
                '<page string="Partner page">' +
                '<field name="bar"/>' +
                '<field name="p">' +
                "<tree>" +
                "<field name=\"foo\" attrs=\"{'column_invisible': [('parent.product_id', '!=', False)]}\"/>" +
                "<field name=\"bar\" attrs=\"{'column_invisible': [('parent.bar', '=', False)]}\"/>" +
                "</tree>" +
                "</field>" +
                "</page>" +
                "</notebook>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many"
        );
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.o_field_many2one[name="product_id"] input'));
        await testUtils.dom.click($("li.ui-menu-item a:contains(xpad)").trigger("mouseenter"));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column when the product_id is set"
        );
        await testUtils.fields.editAndTrigger(
            form.$('.o_field_many2one[name="product_id"] input'),
            "",
            "keyup"
        );
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many when product_id is not set"
        );
        await testUtils.dom.click(form.$('.o_field_boolean[name="bar"] input'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column after the value change"
        );
        form.destroy();
    });

    QUnit.skip(
        "one2many column visiblity depends on onchange of parent field",
        async function (assert) {
            assert.expect(3);

            this.data.partner.records[0].p = [2];
            this.data.partner.records[0].bar = false;

            this.data.partner.onchanges.p = function (obj) {
                // set bar to true when line is added
                if (obj.p.length > 1 && obj.p[1][2].foo === "New line") {
                    obj.bar = true;
                }
            };

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    "<form>" +
                    '<field name="bar"/>' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    "<field name=\"int_field\" attrs=\"{'column_invisible': [('parent.bar', '=', False)]}\"/>" +
                    "</tree>" +
                    "</field>" +
                    "</form>",
                res_id: 1,
            });

            // bar is false so there should be 1 column
            assert.containsOnce(
                form,
                "th:not(.o_list_record_remove_header)",
                "should be only 1 column ('foo') in the one2many"
            );
            assert.containsOnce(form, ".o_list_view .o_data_row", "should contain one row");

            await testUtils.form.clickEdit(form);

            // add a new o2m record
            await testUtils.dom.click(form.$(".o_field_x2many_list_row_add a"));
            form.$(".o_field_one2many input:first").focus();
            await testUtils.fields.editInput(form.$(".o_field_one2many input:first"), "New line");
            await testUtils.dom.click(form.$el);

            assert.containsN(
                form,
                "th:not(.o_list_record_remove_header)",
                2,
                "should be 2 columns('foo' + 'int_field')"
            );

            form.destroy();
        }
    );

    QUnit.skip("one2many column_invisible on view not inline", async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].p = [2];
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="product_id"/>' +
                "</group>" +
                "<notebook>" +
                '<page string="Partner page">' +
                '<field name="bar"/>' +
                '<field name="p"/>' +
                "</page>" +
                "</notebook>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
            archs: {
                "partner,false,list":
                    "<tree>" +
                    "<field name=\"foo\" attrs=\"{'column_invisible': [('parent.product_id', '!=', False)]}\"/>" +
                    "<field name=\"bar\" attrs=\"{'column_invisible': [('parent.bar', '=', False)]}\"/>" +
                    "</tree>",
            },
        });
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many"
        );
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.o_field_many2one[name="product_id"] input'));
        await testUtils.dom.click($("li.ui-menu-item a:contains(xpad)").trigger("mouseenter"));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column when the product_id is set"
        );
        await testUtils.fields.editAndTrigger(
            form.$('.o_field_many2one[name="product_id"] input'),
            "",
            "keyup"
        );
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many when product_id is not set"
        );
        await testUtils.dom.click(form.$('.o_field_boolean[name="bar"] input'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column after the value change"
        );
        form.destroy();
    });

    QUnit.module("Many2OneAvatar");

    QUnit.skip("many2one_avatar widget in form view", async function (assert) {
        assert.expect(17);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="user_id" widget="many2one_avatar"/></form>',
            res_id: 1,
        });

        assert.hasClass(form.$(".o_form_view"), "o_form_readonly");
        assert.strictEqual(form.$(".o_field_widget[name=user_id]").text().trim(), "Aline");
        assert.containsOnce(form, '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]');

        await testUtils.form.clickEdit(form);

        assert.hasClass(form.$(".o_form_view"), "o_form_editable");
        assert.containsOnce(form, ".o_input_dropdown");
        assert.strictEqual(form.$(".o_input_dropdown input").val(), "Aline");
        assert.containsOnce(form, ".o_external_button");
        assert.containsOnce(form, '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]');

        await testUtils.fields.many2one.clickOpenDropdown("user_id");
        await testUtils.fields.many2one.clickItem("user_id", "Christine");
        assert.containsOnce(form, '.o_m2o_avatar > img[data-src="/web/image/user/19/avatar_128"]');
        await testUtils.form.clickSave(form);

        assert.hasClass(form.$(".o_form_view"), "o_form_readonly");
        assert.strictEqual(form.$(".o_field_widget[name=user_id]").text().trim(), "Christine");
        assert.containsOnce(form, '.o_m2o_avatar > img[data-src="/web/image/user/19/avatar_128"]');

        await testUtils.form.clickEdit(form);
        await testUtils.fields.editAndTrigger(
            form.$('.o_field_many2one[name="user_id"] input'),
            "",
            ["keyup", "blur"]
        );
        assert.containsNone(form, ".o_m2o_avatar > img");
        assert.containsOnce(form, ".o_m2o_avatar > .o_m2o_avatar_empty");
        await testUtils.form.clickSave(form);

        assert.hasClass(form.$(".o_form_view"), "o_form_readonly");
        assert.containsNone(form, ".o_m2o_avatar > img");
        assert.containsNone(form, ".o_m2o_avatar > .o_m2o_avatar_empty");

        form.destroy();
    });

    QUnit.skip("many2one_avatar widget in form view, with onchange", async function (assert) {
        assert.expect(7);

        this.data.partner.onchanges = {
            int_field: function (obj) {
                if (obj.int_field === 1) {
                    obj.user_id = [19, "Christine"];
                } else if (obj.int_field === 2) {
                    obj.user_id = false;
                } else {
                    obj.user_id = [17, "Aline"]; // default value
                }
            },
        };
        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="user_id" widget="many2one_avatar" readonly="1"/>
                </form>`,
        });

        assert.hasClass(form.$(".o_form_view"), "o_form_editable");
        assert.strictEqual(form.$(".o_field_widget[name=user_id]").text().trim(), "Aline");
        assert.containsOnce(form, '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]');

        await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), 1);

        assert.strictEqual(form.$(".o_field_widget[name=user_id]").text().trim(), "Christine");
        assert.containsOnce(form, '.o_m2o_avatar > img[data-src="/web/image/user/19/avatar_128"]');

        await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), 2);

        assert.strictEqual(form.$(".o_field_widget[name=user_id]").text().trim(), "");
        assert.containsNone(form, ".o_m2o_avatar > img");

        form.destroy();
    });

    QUnit.skip("many2one_avatar widget in list view", async function (assert) {
        assert.expect(5);

        this.data.partner.records = [
            { id: 1, user_id: 17 },
            { id: 2, user_id: 19 },
            { id: 3, user_id: 17 },
            { id: 4, user_id: false },
        ];
        const list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree><field name="user_id" widget="many2one_avatar"/></tree>',
        });

        assert.strictEqual(list.$(".o_data_cell span").text(), "AlineChristineAline");
        assert.containsOnce(
            list.$(".o_data_cell:nth(0)"),
            '.o_m2o_avatar >img[data-src="/web/image/user/17/avatar_128"]'
        );
        assert.containsOnce(
            list.$(".o_data_cell:nth(1)"),
            '.o_m2o_avatar > img[data-src="/web/image/user/19/avatar_128"]'
        );
        assert.containsOnce(
            list.$(".o_data_cell:nth(2)"),
            '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]'
        );
        assert.containsNone(list.$(".o_data_cell:nth(3)"), ".o_m2o_avatar > img");

        list.destroy();
    });

    QUnit.skip("many2one_avatar widget in editable list view", async function (assert) {
        assert.expect(3);

        this.data.partner.records = [
            { id: 1, user_id: 17 },
            { id: 2, user_id: 19 },
            { id: 3, user_id: 17 },
            { id: 4, user_id: false },
        ];
        const list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="top"><field name="user_id" widget="many2one_avatar"/></tree>',
        });

        assert.strictEqual(list.$(".o_data_cell span").text(), "AlineChristineAline");
        assert.containsOnce(
            list.$(".o_data_cell:nth(0)"),
            '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]'
        );

        await testUtils.dom.click(list.$(".o_data_row:first() .o_data_cell:first()"));
        assert.containsOnce(
            list.$(".o_data_cell:nth(0)"),
            '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]'
        );

        list.destroy();
    });
});
