/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import {
    click,
    clickSave,
    clickOpenedDropdownItem,
    editInput,
    editSelect,
    getFixture,
    getNodesTextContent,
    nextTick,
    patchWithCleanup,
    addRow,
} from "@web/../tests/helpers/utils";
import { editSearch, validateSearch } from "@web/../tests/search/helpers";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { session } from "@web/session";
import { companyService } from "@web/webclient/company_service";
import { registry } from "@web/core/registry";

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

        setupViewRegistries();
    });

    QUnit.module("Many2ManyField");

    QUnit.test("many2many kanban: edition", async function (assert) {
        assert.expect(31);

        serverData.views = {
            "partner_type,false,form": '<form><field name="display_name"/></form>',
            "partner_type,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,search": '<search><field name="name" string="Name"/></search>',
        };

        serverData.models.partner.records[0].timmy = [12, 14];
        serverData.models.partner_type.records.push({ id: 15, display_name: "red", color: 6 });
        serverData.models.partner_type.records.push({ id: 18, display_name: "yellow", color: 4 });
        serverData.models.partner_type.records.push({ id: 21, display_name: "blue", color: 1 });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                        <span><t t-esc="record.display_name.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner_type/write") {
                    assert.strictEqual(
                        args.args[1].display_name,
                        "new name",
                        "should write 'new_name'"
                    );
                }
                if (route === "/web/dataset/call_kw/partner_type/create") {
                    assert.strictEqual(
                        args.args[0].display_name,
                        "A new type",
                        "should create 'A new type'"
                    );
                }
                if (route === "/web/dataset/call_kw/partner/write") {
                    var commands = args.args[1].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(
                        commands[0][0],
                        6,
                        "generated command should be REPLACE WITH"
                    );
                    // get the created type's id
                    var createdType = _.findWhere(serverData.models.partner_type.records, {
                        display_name: "A new type",
                    });
                    var ids = _.sortBy([12, 15, 18].concat(createdType.id), _.identity.bind(_));
                    assert.ok(
                        _.isEqual(_.sortBy(commands[0][2], _.identity.bind(_)), ids),
                        "new value should be " + ids
                    );
                }
            },
        });

        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            2,
            "should contain 2 records"
        );
        assert.strictEqual(
            $(target).find(".o_kanban_record:first() span").text(),
            "gold",
            "display_name of subrecord should be the one in DB"
        );
        assert.ok(
            $(target).find(".o_kanban_renderer .delete_icon").length,
            "delete icon should be visible in edit"
        );
        assert.ok(
            $(target).find(".o_field_many2many .o-kanban-button-new").length,
            '"Add" button should be visible in edit'
        );
        assert.strictEqual(
            $(target).find(".o_field_many2many .o-kanban-button-new").text().trim(),
            "Add",
            'Create button should have "Add" label'
        );

        // edit existing subrecord
        await click($(target).find(".oe_kanban_global_click:first()")[0]);

        await editInput(target, ".modal .o_form_view input", "new name");
        await click($(".modal .modal-footer .btn-primary")[0]);
        assert.strictEqual(
            $(target).find(".o_kanban_record:first() span").text(),
            "new name",
            "value of subrecord should have been updated"
        );

        // add subrecords
        // -> single select
        await click($(target).find(".o_field_many2many .o-kanban-button-new")[0]);
        assert.ok($(".modal .o_list_view").length, "should have opened a list view in a modal");
        assert.strictEqual(
            $(".modal .o_list_view tbody .o_list_record_selector").length,
            3,
            "list view should contain 3 records"
        );
        await click($(".modal .o_list_view tbody tr:contains(red) .o_data_cell")[0]);
        assert.ok(!$(".modal .o_list_view").length, "should have closed the modal");
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            3,
            "kanban should now contain 3 records"
        );
        assert.ok(
            $(target).find(".o_kanban_record:contains(red)").length,
            'record "red" should be in the kanban'
        );

        // -> multiple select
        await click($(target).find(".o_field_many2many .o-kanban-button-new")[0]);
        assert.ok(
            $(".modal .o_select_button").prop("disabled"),
            "select button should be disabled"
        );
        assert.strictEqual(
            $(".modal .o_list_view tbody .o_list_record_selector").length,
            2,
            "list view should contain 2 records"
        );
        await click($(".modal .o_list_view thead .o_list_record_selector input")[0]);
        await nextTick();
        await click($(".modal .o_select_button")[0]);
        assert.ok(
            !$(".modal .o_select_button").prop("disabled"),
            "select button should be enabled"
        );
        assert.ok(!$(".modal .o_list_view").length, "should have closed the modal");
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            5,
            "kanban should now contain 5 records"
        );
        // -> created record
        await click($(target).find(".o_field_many2many .o-kanban-button-new")[0]);
        await click($(".modal .modal-footer .btn-primary:nth(1)")[0]);
        assert.ok(
            $(".modal .o_form_view .o_form_editable").length,
            "should have opened a form view in edit mode, in a modal"
        );
        await editInput(target, ".modal .o_form_view input", "A new type");
        await click($(".modal:not(.o_inactive_modal) footer .btn-primary:first()")[0]);
        assert.ok(!$(".modal").length, "should have closed both modals");
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            6,
            "kanban should now contain 6 records"
        );
        assert.ok(
            $(target).find(".o_kanban_record:contains(A new type)").length,
            "the newly created type should be in the kanban"
        );

        // delete subrecords
        await click($(target).find(".o_kanban_record:contains(silver)")[0]);
        assert.strictEqual(
            $(".modal .modal-footer .o_btn_remove").length,
            1,
            "There should be a modal having Remove Button"
        );
        await click($(".modal .modal-footer .o_btn_remove")[0]);
        assert.containsNone($(".o_modal"), "modal should have been closed");
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            5,
            "should contain 5 records"
        );
        assert.ok(
            !$(target).find(".o_kanban_record:contains(silver)").length,
            "the removed record should not be in kanban anymore"
        );

        await click($(target).find(".o_kanban_record:contains(blue) .delete_icon")[0]);
        assert.strictEqual(
            $(target).find(".o_kanban_record:not(.o_kanban_ghost)").length,
            4,
            "should contain 4 records"
        );
        assert.ok(
            !$(target).find(".o_kanban_record:contains(blue)").length,
            "the removed record should not be in kanban anymore"
        );

        // save the record
        await clickSave(target);
    });

    QUnit.test(
        "many2many kanban(editable): properly handle add-label node attribute",
        async function (assert) {
            serverData.models.partner.records[0].timmy = [12];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="timmy" add-label="Add timmy" mode="kanban">
                            <kanban>
                                <templates>
                                    <t t-name="kanban-box">
                                        <div class="oe_kanban_details">
                                            <field name="display_name"/>
                                        </div>
                                    </t>
                                </templates>
                            </kanban>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.strictEqual(
                target
                    .querySelector(".o_field_many2many[name=timmy] .o-kanban-button-new")
                    .innerText.trim()
                    .toUpperCase(), // for community/enterprise compatibility
                "ADD TIMMY",
                "In M2M Kanban, Add button should have 'Add timmy' label"
            );
        }
    );

    QUnit.test("field string is used in the SelectCreateDialog", async function (assert) {
        serverData.views = {
            "partner_type,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,search": '<search><field name="display_name"/></search>',
            "turtle,false,list": '<tree><field name="display_name"/></tree>',
            "turtle,false,search": '<search><field name="display_name"/></search>',
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                    <field name="turtles" widget="many2many" string="Abcde">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
        });

        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[0]);
        assert.containsOnce(target, ".modal");
        assert.strictEqual(target.querySelector(".modal .modal-title").innerText, "Add: pokemon");

        await click(target.querySelector(".modal .o_form_button_cancel"));
        assert.containsNone(target, ".modal");

        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[1]);
        assert.containsOnce(target, ".modal");
        assert.strictEqual(target.querySelector(".modal .modal-title").innerText, "Add: Abcde");
    });

    QUnit.test("many2many kanban: create action disabled", async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];

        serverData.views = {
            "partner_type,false,list": '<tree><field name="name"/></tree>',
            "partner_type,false,search":
                "<search>" + '<field name="display_name" string="Name"/>' + "</search>",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <kanban create="0">
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                        <span><t t-esc="record.display_name.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.ok(
            $(target).find(".o-kanban-button-new").length,
            '"Add" button should be available in edit'
        );
        assert.ok(
            $(target).find(".o_kanban_renderer .delete_icon").length,
            "delete icon should be visible in edit"
        );

        await click($(target).find(".o-kanban-button-new")[0]);
        assert.strictEqual(
            $(".modal .modal-footer .btn-primary").length,
            1, // only button 'Select'
            '"Create" button should not be available in the modal'
        );
    });

    QUnit.test("many2many kanban: conditional create/delete actions", async function (assert) {
        serverData.views = {
            "partner_type,false,form": '<form><field name="name"/></form>',
            "partner_type,false,list": '<tree><field name="name"/></tree>',
            "partner_type,false,search": "<search/>",
        };
        serverData.models.partner.records[0].timmy = [12, 14];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="color"/>
                    <field name="timmy" options="{'create': [('color', '=', 'red')], 'delete': [('color', '=', 'red')]}">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <span><t t-esc="record.display_name.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        // color is red
        assert.containsOnce(target, ".o-kanban-button-new", '"Add" button should be available');

        await click($(target).find(".o_kanban_record:contains(silver)")[0]);
        assert.containsOnce(
            document.body,
            ".modal .modal-footer .o_btn_remove",
            "remove button should be visible in modal"
        );
        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        await click($(target).find(".o-kanban-button-new")[0]);
        assert.containsN(
            document.body,
            ".modal .modal-footer button",
            3,
            "there should be 3 buttons available in the modal"
        );
        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        // set color to black
        await editSelect(target, 'div[name="color"] select', '"black"');
        assert.containsOnce(
            target,
            ".o-kanban-button-new",
            '"Add" button should still be available even after color field changed'
        );

        await click($(target).find(".o-kanban-button-new")[0]);
        // only select and cancel button should be available, create
        // button should be removed based on color field condition
        assert.containsN(
            document.body,
            ".modal .modal-footer button",
            2,
            '"Create" button should not be available in the modal after color field changed'
        );
        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        await click($(target).find(".o_kanban_record:contains(silver)")[0]);
        assert.containsNone(
            document.body,
            ".modal .modal-footer .o_btn_remove",
            "remove button should not be visible in modal"
        );
    });

    QUnit.test("many2many list (non editable): edition", async function (assert) {
        assert.expect(32);

        serverData.models.partner.records[0].timmy = [12, 14];
        serverData.models.partner_type.records.push({ id: 15, display_name: "bronze", color: 6 });
        serverData.models.partner_type.fields.float_field = { string: "Float", type: "float" };

        serverData.views = {
            "partner_type,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,search": '<search><field name="display_name"/></search>',
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <tree>
                            <field name="display_name"/><field name="float_field"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method !== "get_views") {
                    assert.step(_.last(route.split("/")));
                }
                if (args.method === "write" && args.model === "partner") {
                    assert.deepEqual(args.args[1].timmy, [[6, false, [12, 15]]]);
                }
            },
        });

        assert.verifySteps([
            "read", // main record
            "read", // relational field
        ]);

        assert.containsN(
            target,
            ".o_list_renderer td.o_list_number",
            2,
            "should contain 2 records"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody td").innerText,
            "gold",
            "display_name of first subrecord should be the one in DB"
        );
        assert.containsN(
            target,
            ".o_list_record_remove",
            2,
            "delete icon should be visible in edit"
        );
        assert.containsOnce(
            target,
            ".o_field_x2many_list_row_add",
            '"Add an item" should be visible in edit'
        );

        // edit existing subrecord
        await click(target.querySelector(".o_list_renderer tbody tr .o_data_cell"));
        assert.verifySteps([]); // No further read: all fields were fetched at the first read

        assert.containsNone(
            target,
            ".modal .modal-footer .o_btn_remove",
            'there should not be a "Remove" button in the modal footer'
        );

        await editInput(target, ".modal .o_form_view input", "new name");
        await click(target.querySelector(".modal .modal-footer .btn-primary"));
        assert.verifySteps(["write", "read"]); // save relational record from dialog then read it
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody td").innerText,
            "new name",
            "value of subrecord should have been updated"
        );

        // add new subrecords
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.verifySteps(["web_search_read"]);
        assert.containsNone(
            target,
            ".modal .modal-footer .o_btn_remove",
            'there should not be a "Remove" button in the modal footer'
        );
        assert.containsOnce(target, ".modal", "a modal should be open");
        assert.containsOnce(
            target,
            ".modal .o_list_view .o_data_row",
            "the list should contain one row"
        );
        await click(target.querySelector(".modal .o_list_view .o_data_row .o_data_cell"));
        assert.verifySteps(["read"]); // relational model (udpated)
        assert.containsNone(target, ".modal", "the modal should be closed");
        assert.containsN(
            target,
            ".o_list_renderer td.o_list_number",
            3,
            "should contain 3 subrecords"
        );

        // remove subrecords
        await click(target.querySelectorAll(".o_list_record_remove")[1]);
        assert.verifySteps([]);
        assert.containsN(
            target,
            ".o_list_renderer td.o_list_number",
            2,
            "should contain 2 subrecords"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer .o_data_row td").innerText,
            "new name",
            "the updated row still has the correct values"
        );

        // save
        await clickSave(target);
        assert.verifySteps(["write", "read", "read"]); // save main record then re-reads it
        assert.containsN(
            target,
            ".o_list_renderer td.o_list_number",
            2,
            "should contain 2 subrecords"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer .o_data_row td").innerText,
            "new name",
            "the updated row still has the correct values"
        );
    });

    QUnit.test("add record in a many2many non editable list with context", async function (assert) {
        assert.expect(1);

        serverData.views = {
            "partner_type,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,search": '<search><field name="display_name"/></search>',
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="timmy" context="{'abc': int_field}">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    // done by the SelectCreateDialog
                    assert.deepEqual(args.kwargs.context, {
                        abc: 2,
                        bin_size: true, // not sure it should be there, but was in legacy
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    });
                }
            },
        });

        await editInput(target, ".o_field_widget[name=int_field] input", "2");
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
    });

    QUnit.test("many2many list (editable): edition", async function (assert) {
        assert.expect(29);

        serverData.models.partner.records[0].timmy = [12, 14];
        serverData.models.partner_type.records.push({ id: 15, display_name: "bronze", color: 6 });
        serverData.models.partner_type.fields.float_field = { string: "Float", type: "float" };

        serverData.views = {
            "partner_type,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,search": '<search><field name="display_name"/></search>',
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <tree editable="top">
                            <field name="display_name"/>
                            <field name="float_field"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method !== "get_views") {
                    assert.step(_.last(route.split("/")));
                }
                if (args.method === "write") {
                    assert.deepEqual(args.args[1].timmy, [
                        [6, false, [12, 15]],
                        [1, 12, { display_name: "new name" }],
                    ]);
                }
            },
            resId: 1,
        });

        assert.containsN(
            target,
            ".o_list_renderer td.o_list_number",
            2,
            "should contain 2 records"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody td").innerText,
            "gold",
            "display_name of first subrecord should be the one in DB"
        );
        assert.containsN(
            target,
            ".o_list_record_remove",
            2,
            "delete icon should be visible in edit"
        );
        assert.hasClass(
            target.querySelector("td.o_list_record_remove button"),
            "fa fa-times",
            "should have X icons to remove (unlink) records"
        );
        assert.containsOnce(
            target,
            ".o_field_x2many_list_row_add",
            '"Add an item" should not visible in edit'
        );

        // edit existing subrecord
        await click(target.querySelector(".o_list_renderer tbody td"));
        assert.containsNone(
            target,
            ".modal",
            "in edit, clicking on a subrecord should not open a dialog"
        );
        assert.hasClass(
            target.querySelector(".o_list_renderer tbody tr"),
            "o_selected_row",
            "first row should be in edition"
        );
        await editInput(target, ".o_selected_row div[name=display_name] input", "new name");
        assert.hasClass(
            target.querySelector(".o_list_renderer .o_data_row"),
            "o_selected_row",
            "first row should still be in edition"
        );
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_list_renderer div[name=display_name] input"),
            "edited field should still have the focus"
        );
        await click(target.querySelector(".o_form_view"));
        assert.doesNotHaveClass(
            target.querySelector(".o_list_renderer tbody tr"),
            "o_selected_row",
            "first row should not be in edition anymore"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody td").innerText,
            "new name",
            "value of subrecord should have been updated"
        );
        assert.verifySteps(["read", "read"]);

        // add new subrecords
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.containsOnce(target, ".modal", "a modal should be open");
        assert.containsOnce(
            target,
            ".modal .o_list_view .o_data_row",
            "the list should contain one row"
        );
        await click(target.querySelector(".modal .o_list_view .o_data_row .o_data_cell"));
        assert.containsNone(target, ".modal .o_list_view", "the modal should be closed");
        assert.containsN(
            target,
            ".o_list_renderer td.o_list_number",
            3,
            "should contain 3 subrecords"
        );

        // remove subrecords
        await click(target.querySelectorAll(".o_list_record_remove")[1]);
        assert.containsN(
            target,
            ".o_list_renderer td.o_list_number",
            2,
            "should contain 2 subrecord"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody .o_data_row td").innerText,
            "new name",
            "the updated row still has the correct values"
        );

        // save
        await clickSave(target);
        assert.containsN(
            target,
            ".o_list_renderer td.o_list_number",
            2,
            "should contain 2 subrecords"
        );
        assert.strictEqual(
            target.querySelector(".o_list_renderer .o_data_row td").innerText,
            "new name",
            "the updated row still has the correct values"
        );

        assert.verifySteps([
            "web_search_read", // list view in dialog
            "read", // relational field (updated)
            "write", // save main record
            "read", // main record
            "read", // relational field
        ]);
    });

    QUnit.test("many2many: create & delete attributes (both true)", async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <tree create="true" delete="true">
                            <field name="color"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_field_x2many_list_row_add",
            "should have the 'Add an item' link"
        );
        assert.containsN(target, ".o_list_record_remove", 2, "should have the 'Add an item' link");
    });

    QUnit.test("many2many: create & delete attributes (both false)", async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <tree create="false" delete="false">
                            <field name="color"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_field_x2many_list_row_add",
            "should have the 'Add an item' link"
        );
        assert.containsN(
            target,
            ".o_list_record_remove",
            2,
            "each record should have the 'Remove Item' link"
        );
    });

    QUnit.test("many2many list: create action disabled", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <tree create="0">
                            <field name="name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_field_x2many_list_row_add");
    });

    QUnit.test("fieldmany2many list comodel not writable", async function (assert) {
        /**
         * Many2Many List should behave as the m2m_tags
         * that is, the relation can be altered even if the comodel itself is not CRUD-able
         * This can happen when someone has read access alone on the comodel
         * and full CRUD on the current model
         */
        assert.expect(12);

        serverData.views = {
            "partner_type,false,list": `
                <tree create="false" delete="false" edit="false">
                    <field name="display_name"/>
                </tree>`,
            "partner_type,false,search": '<search><field name="display_name"/></search>',
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many" can_create="false" can_write="false"/>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/create") {
                    assert.deepEqual(args.args[0], { timmy: [[6, false, [12]]] });
                }
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.deepEqual(args.args[1], { timmy: [[6, false, []]] });
                }
            },
        });

        assert.containsOnce(target, ".o_field_many2many .o_field_x2many_list_row_add");
        await click(target.querySelector(".o_field_many2many .o_field_x2many_list_row_add a"));
        assert.containsOnce(target, ".modal");

        assert.containsN(target.querySelector(".modal-footer"), "button", 2);
        assert.containsOnce(target.querySelector(".modal-footer"), "button.o_select_button");
        assert.containsOnce(target.querySelector(".modal-footer"), "button.o_form_button_cancel");

        await click(target.querySelector(".modal .o_list_view .o_data_cell"));
        assert.containsNone(target, ".modal");

        assert.containsOnce(target, ".o_field_many2many .o_data_row");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_field_many2many .o_data_row")),
            ["gold"]
        );
        assert.containsOnce(target, ".o_field_many2many .o_field_x2many_list_row_add");

        await clickSave(target);

        assert.containsOnce(target, ".o_field_many2many .o_data_row .o_list_record_remove");
        await click(target.querySelector(".o_field_many2many .o_data_row .o_list_record_remove"));
        await clickSave(target);
    });

    QUnit.test("many2many list: conditional create/delete actions", async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];

        serverData.views = {
            "partner_type,false,list": '<tree><field name="name"/></tree>',
            "partner_type,false,search": "<search/>",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="color"/>
                    <field name="timmy" options="{'create': [('color', '=', 'red')], 'delete': [('color', '=', 'red')]}">
                        <tree>
                            <field name="name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // color is red -> create and delete actions are available
        assert.containsOnce(
            target,
            ".o_field_x2many_list_row_add",
            "should have the 'Add an item' link"
        );
        assert.containsN(target, ".o_list_record_remove", 2, "should have two remove icons");

        await click($(target).find(".o_field_x2many_list_row_add a")[0]);

        assert.containsN(
            target,
            ".modal .modal-footer button",
            3,
            "there should be 3 buttons available in the modal"
        );

        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        // set color to black -> create and delete actions are no longer available
        await editSelect(target, 'div[name="color"] select', '"black"');

        // add a line and remove icon should still be there as they don't create/delete records,
        // but rather add/remove links
        assert.containsOnce(
            target,
            ".o_field_x2many_list_row_add",
            '"Add a line" button should still be available even after color field changed'
        );
        assert.containsN(
            target,
            ".o_list_record_remove",
            2,
            "should still have remove icon even after color field changed"
        );

        await click($(target).find(".o_field_x2many_list_row_add a")[0]);
        assert.containsN(
            target,
            ".modal .modal-footer button",
            2,
            '"Create" button should not be available in the modal after color field changed'
        );
    });

    QUnit.test("many2many field with link/unlink options (list)", async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];
        serverData.views = {
            "partner_type,false,list": '<tree><field name="name"/></tree>',
            "partner_type,false,search": "<search/>",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="color"/>
                    <field name="timmy" options="{'link': [('color', '=', 'red')], 'unlink': [('color', '=', 'red')]}">
                        <tree>
                            <field name="name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // color is red -> link and unlink actions are available
        assert.containsOnce(
            target,
            ".o_field_x2many_list_row_add",
            "should have the 'Add an item' link"
        );
        assert.containsN(target, ".o_list_record_remove", 2, "should have two remove icons");

        await click($(target).find(".o_field_x2many_list_row_add a")[0]);

        assert.containsN(
            target,
            ".modal .modal-footer button",
            3,
            "there should be 3 buttons available in the modal (Create action is available)"
        );

        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        // set color to black -> link and unlink actions are no longer available
        await editSelect(target, 'div[name="color"] select', '"black"');

        assert.containsNone(
            target,
            ".o_field_x2many_list_row_add",
            '"Add a line" should no longer be available after color field changed'
        );
        assert.containsNone(
            target,
            ".o_list_record_remove",
            "should no longer have remove icon after color field changed"
        );
    });

    QUnit.test(
        'many2many field with link/unlink options (list, create="0")',
        async function (assert) {
            serverData.models.partner.records[0].timmy = [12, 14];
            serverData.views = {
                "partner_type,false,list": '<tree><field name="name"/></tree>',
                "partner_type,false,search": "<search/>",
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="color"/>
                    <field name="timmy" options="{'link': [('color', '=', 'red')], 'unlink': [('color', '=', 'red')]}">
                        <tree create="0">
                            <field name="name"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
            });

            // color is red -> link and unlink actions are available
            assert.containsOnce(
                target,
                ".o_field_x2many_list_row_add",
                "should have the 'Add an item' link"
            );
            assert.containsN(target, ".o_list_record_remove", 2, "should have two remove icons");

            await click($(target).find(".o_field_x2many_list_row_add a")[0]);

            assert.containsN(
                document.body,
                ".modal .modal-footer button",
                2,
                "there should be 2 buttons available in the modal (Create action is not available)"
            );

            await click($(".modal .modal-footer .o_form_button_cancel")[0]);

            // set color to black -> link and unlink actions are no longer available
            await editSelect(target, 'div[name="color"] select', '"black"');

            assert.containsNone(
                target,
                ".o_field_x2many_list_row_add",
                '"Add a line" should no longer be available after color field changed'
            );
            assert.containsNone(
                target,
                ".o_list_record_remove",
                "should no longer have remove icon after color field changed"
            );
        }
    );

    QUnit.test("many2many field with link option (kanban)", async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];

        serverData.views = {
            "partner_type,false,list": '<tree><field name="name"/></tree>',
            "partner_type,false,search": "<search/>",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="color"/>
                    <field name="timmy" options="{'link': [('color', '=', 'red')]}">
                        <kanban>
                            <templates>
                                <t t-name="kanban-box">
                                    <div><field name="name"/></div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        // color is red -> link and unlink actions are available
        assert.containsOnce(target, ".o-kanban-button-new", "should have the 'Add' button");

        await click(target.querySelector(".o-kanban-button-new"));

        assert.containsN(
            document.body,
            ".modal .modal-footer button",
            3,
            "there should be 3 buttons available in the modal (Create action is available"
        );

        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        // set color to black -> link and unlink actions are no longer available
        await editSelect(target, 'div[name="color"] select', '"black"');

        assert.containsNone(
            target,
            ".o-kanban-button-new",
            '"Add" should no longer be available after color field changed'
        );
    });

    QUnit.test('many2many field with link option (kanban, create="0")', async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];
        serverData.views = {
            "partner_type,false,list": '<tree><field name="name"/></tree>',
            "partner_type,false,search": "<search/>",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="color"/>
                    <field name="timmy" options="{'link': [('color', '=', 'red')]}">
                        <kanban create="0">
                            <templates>
                                <t t-name="kanban-box">
                                    <div><field name="name"/></div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        // color is red -> link and unlink actions are available
        assert.containsOnce(target, ".o-kanban-button-new", "should have the 'Add' button");

        await click(target.querySelector(".o-kanban-button-new"));

        assert.containsN(
            document.body,
            ".modal .modal-footer button",
            2,
            "there should be 2 buttons available in the modal (Create action is not available"
        );

        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        // set color to black -> link and unlink actions are no longer available
        await editSelect(target, 'div[name="color"] select', '"black"');

        assert.containsNone(
            target,
            ".o-kanban-button-new",
            '"Add" should no longer be available after color field changed'
        );
    });

    QUnit.test("many2many list: list of id as default value", async function (assert) {
        serverData.models.partner.fields.turtles.default = [2, 3];
        serverData.models.partner.fields.turtles.type = "many2many";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                "<form>" +
                '<field name="turtles">' +
                "<tree>" +
                '<field name="turtle_foo"/>' +
                "</tree>" +
                "</field>" +
                "</form>",
        });

        assert.strictEqual(
            $(target).find("td.o_data_cell").text(),
            "blipkawa",
            "should have loaded default data"
        );
    });

    QUnit.test("many2many list with x2many: add a record", async function (assert) {
        serverData.models.partner_type.fields.m2m = {
            string: "M2M",
            type: "many2many",
            relation: "turtle",
        };
        serverData.models.partner_type.records[0].m2m = [1, 2];
        serverData.models.partner_type.records[1].m2m = [2, 3];

        serverData.views = {
            "partner_type,false,list": `
                <tree>
                    <field name="display_name"/>
                    <field name="m2m" widget="many2many_tags"/>
                </tree>`,
            "partner_type,false,search":
                '<search><field name="display_name" string="Name"/></search>',
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy"/></form>',
            resId: 1,
            mockRPC(route, args) {
                if (args.method !== "get_views") {
                    assert.step(_.last(route.split("/")) + " on " + args.model);
                }
                if (args.model === "turtle") {
                    assert.step(JSON.stringify(args.args[0])); // the read ids
                }
            },
        });

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await click($(target).find(".modal .o_data_row:first .o_data_cell")[0]);

        assert.containsOnce(
            target,
            ".o_data_row",
            "the record should have been added to the relation"
        );
        assert.strictEqual(
            $(target).find(".o_data_row:first .o_tag_badge_text").text(),
            "leonardodonatello",
            "inner m2m should have been fetched and correctly displayed"
        );

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await click(target.querySelector(".modal .o_data_row:nth-child(1) .o_data_cell"));

        assert.containsN(
            target,
            ".o_data_row",
            2,
            "the second record should have been added to the relation"
        );
        assert.strictEqual(
            $(target).find(".o_data_row:nth(1) .o_tag_badge_text").text(),
            "donatelloraphael",
            "inner m2m should have been fetched and correctly displayed"
        );

        assert.verifySteps([
            "read on partner",
            "web_search_read on partner_type",
            "read on turtle",
            "[1,2,3]",
            "read on partner_type",
            "read on turtle",
            "[1,2]",
            "web_search_read on partner_type",
            "read on turtle",
            "[2,3]",
            "read on partner_type",
            "read on turtle",
            "[2,3]",
        ]);
    });

    QUnit.test("many2many with a domain", async function (assert) {
        // The domain specified on the field should not be replaced by the potential
        // domain the user writes in the dialog, they should rather be concatenated
        serverData.views = {
            "partner_type,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,search":
                '<search><field name="display_name" string="Name"/></search>',
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" domain="[['display_name', '=', 'gold']]"/>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.strictEqual($(".modal .o_data_row").length, 1, "should contain only one row (gold)");

        const modal = document.body.querySelector(".modal");
        await editSearch(modal, "s");
        await validateSearch(modal);

        assert.strictEqual($(".modal .o_data_row").length, 0, "should contain no row");
    });

    QUnit.test("many2many list with onchange and edition of a record", async function (assert) {
        serverData.models.partner.fields.turtles.type = "many2many";
        serverData.models.partner.onchanges.turtles = function () {};

        serverData.views = {
            "turtle,false,form": '<form string="Turtle Power"><field name="turtle_bar"/></form>',
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        assert.verifySteps(["get_views", "read", "read"]);

        await click($(target).find("td.o_data_cell:first")[0]);
        assert.verifySteps(["get_views", "read"]);

        await click($('.modal-body input[type="checkbox"]')[0]);
        await click($(".modal .modal-footer .btn-primary").first()[0]);
        assert.verifySteps(["write", "onchange", "read"]);

        // there is nothing left to save -> should not do a 'write' RPC
        await clickSave(target);
        assert.verifySteps([]);
    });

    QUnit.test(
        "many2many widget: creates a new record with a context containing the parentID",
        async function (assert) {
            serverData.views = {
                "turtle,false,list": '<tree><field name="display_name"/></tree>',
                "turtle,false,search": '<search><field name="display_name"/></search>',
                "turtle,false,form":
                    '<form string="Turtle Power"><field name="turtle_trululu"/></form>',
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="turtles" widget="many2many" context="{'default_turtle_trululu': id}" >
                        <tree>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
                mockRPC(route, args) {
                    const { method, kwargs } = args;
                    assert.step(method);
                    if (method === "onchange") {
                        assert.strictEqual(kwargs.context.default_turtle_trululu, 1);
                        assert.deepEqual(args.args, [
                            [],
                            {},
                            [],
                            {
                                turtle_trululu: "",
                            },
                        ]);
                    }
                },
            });
            assert.verifySteps(["get_views", "read", "read"]);

            await addRow(target);
            assert.verifySteps(["get_views", "web_search_read"]);

            await click(target, ".o_create_button");
            assert.strictEqual(
                target.querySelector("[name='turtle_trululu'] input").value,
                "first record"
            );
            assert.verifySteps(["get_views", "onchange"]);
        }
    );

    QUnit.test("onchange with 40+ commands for a many2many", async function (assert) {
        // this test ensures that the basic_model correctly handles more LINK_TO
        // commands than the limit of the dataPoint (40 for x2many kanban)
        assert.expect(25);

        // create a lot of partner_types that will be linked by the onchange
        var commands = [[5]];
        for (var i = 0; i < 45; i++) {
            var id = 100 + i;
            serverData.models.partner_type.records.push({ id: id, display_name: "type " + id });
            commands.push([4, id]);
        }
        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.timmy = commands;
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="timmy">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div><t t-esc="record.display_name.value"/></div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "write") {
                    assert.strictEqual(args.args[1].timmy[0][0], 6, "should send a command 6");
                    assert.strictEqual(
                        args.args[1].timmy[0][2].length,
                        45,
                        "should replace with 45 ids"
                    );
                }
            },
        });

        assert.verifySteps(["get_views", "read"]);

        await editInput(target, ".o_field_widget[name=foo] input", "trigger onchange");

        assert.verifySteps(["onchange", "read"]);
        assert.strictEqual(
            $(target).find(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "1-40 / 45",
            "pager should be correct"
        );
        assert.strictEqual(
            $(target).find('.o_kanban_record:not(".o_kanban_ghost")').length,
            40,
            "there should be 40 records displayed on page 1"
        );

        await click($(target).find(".o_field_widget[name=timmy] .o_pager_next")[0]);
        assert.verifySteps(["read"]);
        assert.strictEqual(
            $(target).find(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "41-45 / 45",
            "pager should be correct"
        );
        assert.strictEqual(
            $(target).find('.o_kanban_record:not(".o_kanban_ghost")').length,
            5,
            "there should be 5 records displayed on page 2"
        );

        await clickSave(target);

        assert.strictEqual(
            $(target).find(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "1-40 / 45",
            "pager should be correct"
        );
        assert.strictEqual(
            $(target).find('.o_kanban_record:not(".o_kanban_ghost")').length,
            40,
            "there should be 40 records displayed on page 1"
        );

        await click($(target).find(".o_field_widget[name=timmy] .o_pager_next")[0]);
        assert.strictEqual(
            $(target).find(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "41-45 / 45",
            "pager should be correct"
        );
        assert.strictEqual(
            $(target).find('.o_kanban_record:not(".o_kanban_ghost")').length,
            5,
            "there should be 5 records displayed on page 2"
        );

        await click($(target).find(".o_field_widget[name=timmy] .o_pager_next")[0]);
        assert.strictEqual(
            $(target).find(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "1-40 / 45",
            "pager should be correct"
        );
        assert.strictEqual(
            $(target).find('.o_kanban_record:not(".o_kanban_ghost")').length,
            40,
            "there should be 40 records displayed on page 1"
        );

        assert.verifySteps(["write", "read", "read", "read"]);
    });

    QUnit.test("default_get, onchange, onchange on m2m", async function (assert) {
        assert.expect(1);

        serverData.models.partner.onchanges.int_field = function (obj) {
            if (obj.int_field === 2) {
                assert.deepEqual(obj.timmy, [
                    [6, false, [12]],
                    [1, 12, { display_name: "gold" }],
                ]);
            }
            obj.timmy = [[5], [1, 12, { display_name: "gold" }]];
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="timmy">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                        </field>
                        <field name="int_field"/>
                    </sheet>
                </form>`,
        });

        await editInput(target, ".o_field_widget[name=int_field] input", 2);
    });

    QUnit.test("many2many list add *many* records, remove, re-add", async function (assert) {
        assert.expect(5);

        serverData.models.partner.fields.timmy.domain = [["color", "=", 2]];
        serverData.models.partner.fields.timmy.onChange = true;
        serverData.models.partner_type.fields.product_ids = {
            string: "Product",
            type: "many2many",
            relation: "product",
        };

        for (var i = 0; i < 50; i++) {
            var new_record_partner_type = { id: 100 + i, display_name: "batch" + i, color: 2 };
            serverData.models.partner_type.records.push(new_record_partner_type);
        }

        serverData.views = {
            "partner_type,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,search":
                '<search><field name="display_name"/><field name="color"/></search>',
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many">
                        <tree>
                            <field name="display_name"/>
                            <field name="product_ids" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "get_formview_id") {
                    assert.deepEqual(
                        args.args[0],
                        [1],
                        "should call get_formview_id with correct id"
                    );
                }
            },
        });

        // First round: add 51 records in batch
        await click(target.querySelector(".o_field_x2many_list_row_add a"));

        var $modal = $(".modal-lg");

        assert.equal($modal.length, 1, "There should be one modal");

        await click($modal.find("thead input[type=checkbox]")[0]);
        await nextTick();

        await click($modal.find(".btn.btn-primary.o_select_button")[0]);

        assert.strictEqual(
            $(target).find(".o_data_row").length,
            51,
            "We should have added all the records present in the search view to the m2m field"
        ); // the 50 in batch + 'gold'

        await clickSave(target);

        // Secound round: remove one record
        var trash_buttons = $(target).find(
            ".o_field_many2many.o_field_widget .o_field_x2many.o_field_x2many_list .o_list_record_remove"
        );

        await click(trash_buttons.first()[0]);

        var pager_limit = $(target).find(
            ".o_field_many2many.o_field_widget .o_field_x2many.o_field_x2many_list .o_pager_limit"
        );
        assert.equal(pager_limit.text(), "50", "We should have 50 records in the m2m field");

        // Third round: re-add 1 records
        await click($(target).find(".o_field_x2many_list_row_add a")[0]);

        $modal = $(".modal-lg");

        assert.equal($modal.length, 1, "There should be one modal");

        await click($modal.find("thead input[type=checkbox]")[0]);
        await nextTick();

        await click($modal.find(".btn.btn-primary.o_select_button")[0]);

        assert.strictEqual(
            $(target).find(".o_data_row").length,
            51,
            "We should have 51 records in the m2m field"
        );
    });

    QUnit.test("many2many kanban: action/type attribute", async function (assert) {
        serverData.models.partner.records[0].timmy = [12];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <kanban action="a1" type="object">
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <field name="display_name"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });
        patchWithCleanup(form.env.services.action, {
            doActionButton(params) {
                assert.step(`doActionButton type ${params.type} name ${params.name}`);
                params.onClose();
            },
        });
        await click(target.querySelector(".oe_kanban_global_click"));
        assert.verifySteps(["doActionButton type object name a1"]);
    });

    QUnit.test("select create with _view_ref as text", async (assert) => {
        serverData.views = {
            "partner_type,my.little.string,list": `<tree><field name="display_name"/></tree>`,
            "partner_type,false,search": `<search />`,
        };

        patchWithCleanup(browser, {
            setTimeout: (fn) => Promise.resolve().then(fn),
        });

        patchWithCleanup(Many2XAutocomplete.defaultProps, {
            searchLimit: 1,
        });

        let checkGetViews = false;
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" context="{ 'tree_view_ref': 'my.little.string' }"/>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "get_views" && checkGetViews) {
                    assert.step("get_views");
                    assert.deepEqual(args.kwargs.views, [
                        [false, "list"],
                        [false, "search"],
                    ]);
                    assert.strictEqual(args.kwargs.context.tree_view_ref, "my.little.string");
                }
            },
        });
        await click(target, ".o_field_many2many_selection input");
        checkGetViews = true;
        await clickOpenedDropdownItem(target, "timmy", "Search More...");
        assert.verifySteps([`get_views`]);

        assert.containsOnce(target, ".modal");
        assert.strictEqual(target.querySelector(".modal-title").textContent, "Search: pokemon");
    });

    QUnit.test("many2many basic keys in field evalcontext -- in list", async (assert) => {
        assert.expect(6);
        serverData.models.partner_type.fields.partner_id = {
            string: "Partners",
            type: "many2one",
            relation: "partner",
        };
        serverData.views = {
            "partner_type,false,form": `<form><field name="partner_id" /></form>`,
        };

        patchWithCleanup(session, {
            user_companies: {
                allowed_companies: {
                    3: { id: 3, name: "Hermit", sequence: 1 },
                    2: { id: 2, name: "Herman's", sequence: 2 },
                    1: { id: 1, name: "Heroes TM", sequence: 3 },
                },
                current_company: 3,
            },
        });

        registry.category("services").add("company", companyService, { force: true });

        patchWithCleanup(browser, {
            setTimeout: (fn) => Promise.resolve().then(fn),
        });

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="timmy" widget="many2many_tags" context="{ 'default_partner_id': active_id, 'ids': active_ids, 'model': active_model, 'company_id': current_company_id}"/>
                </tree>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.strictEqual(args.kwargs.context.default_partner_id, 1);
                    assert.strictEqual(args.kwargs.context.model, "partner");
                    assert.deepEqual(args.kwargs.context.ids, [1]);
                    assert.strictEqual(args.kwargs.context.company_id, 3);
                }
            },
        });

        await click(target.querySelector(".o_data_cell"));
        await editInput(target, ".o_field_many2many_selection input", "indianapolis");
        await nextTick();
        await clickOpenedDropdownItem(target, "timmy", "Create and edit...");
        assert.containsOnce(target, ".modal .o_field_many2one");
        assert.strictEqual(
            target.querySelector(".modal .o_field_many2one input").value,
            "first record"
        );
    });

    QUnit.test("many2many basic keys in field evalcontext -- in form", async (assert) => {
        assert.expect(6);
        serverData.models.partner_type.fields.partner_id = {
            string: "Partners",
            type: "many2one",
            relation: "partner",
        };
        serverData.views = {
            "partner_type,false,form": `<form><field name="partner_id" /></form>`,
        };

        patchWithCleanup(session, {
            user_companies: {
                allowed_companies: {
                    3: { id: 3, name: "Hermit", sequence: 1 },
                    2: { id: 2, name: "Herman's", sequence: 2 },
                    1: { id: 1, name: "Heroes TM", sequence: 3 },
                },
                current_company: 3,
            },
        });

        registry.category("services").add("company", companyService, { force: true });

        patchWithCleanup(browser, {
            setTimeout: (fn) => Promise.resolve().then(fn),
        });

        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" context="{ 'default_partner_id': active_id, 'ids': active_ids, 'model': active_model, 'company_id': current_company_id}"/>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.strictEqual(args.kwargs.context.default_partner_id, 1);
                    assert.strictEqual(args.kwargs.context.model, "partner");
                    assert.deepEqual(args.kwargs.context.ids, [1]);
                    assert.strictEqual(args.kwargs.context.company_id, 3);
                }
            },
        });

        await editInput(target, ".o_field_many2many_selection input", "indianapolis");
        await nextTick();
        await clickOpenedDropdownItem(target, "timmy", "Create and edit...");
        assert.containsOnce(target, ".modal .o_field_many2one");
        assert.strictEqual(
            target.querySelector(".modal .o_field_many2one input").value,
            "first record"
        );
    });

    QUnit.test(
        "many2many basic keys in field evalcontext -- in a x2many in form",
        async (assert) => {
            assert.expect(6);
            serverData.models.partner_type.fields.partner_id = {
                string: "Partners",
                type: "many2one",
                relation: "partner",
            };
            serverData.views = {
                "partner_type,false,form": `<form><field name="partner_id" /></form>`,
            };

            const rec = serverData.models.partner.records.find(({ id }) => id === 2);
            rec.p = [1];

            patchWithCleanup(session, {
                user_companies: {
                    allowed_companies: {
                        3: { id: 3, name: "Hermit", sequence: 1 },
                        2: { id: 2, name: "Herman's", sequence: 2 },
                        1: { id: 1, name: "Heroes TM", sequence: 3 },
                    },
                    current_company: 3,
                },
            });
            registry.category("services").add("company", companyService, { force: true });

            patchWithCleanup(browser, {
                setTimeout: (fn) => Promise.resolve().then(fn),
            });

            await makeView({
                type: "form",
                resId: 2,
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="timmy" widget="many2many_tags" context="{ 'default_partner_id': active_id, 'ids': active_ids, 'model': active_model, 'company_id': current_company_id}"/>
                        </tree>
                    </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.strictEqual(args.kwargs.context.default_partner_id, 1);
                        assert.strictEqual(args.kwargs.context.model, "partner");
                        assert.deepEqual(args.kwargs.context.ids, [1]);
                        assert.strictEqual(args.kwargs.context.company_id, 3);
                    }
                },
            });

            await click(target, ".o_data_cell");
            await editInput(target, ".o_field_many2many_selection input", "indianapolis");
            await clickOpenedDropdownItem(target, "timmy", "Create and edit...");
            assert.containsOnce(target, ".modal .o_field_many2one");
            assert.strictEqual(
                target.querySelector(".modal .o_field_many2one input").value,
                "first record"
            );
        }
    );
});
