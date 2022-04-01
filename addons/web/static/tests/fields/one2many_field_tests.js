/** @odoo-module **/

import {
    click,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { ListRenderer } from "@web/views/list/list_renderer";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

let serverData;
let target;

// WOWL remove after adapting tests
let testUtils,
    delay,
    AbstractField,
    BasicModel,
    fieldRegistry,
    clickFirst,
    KanbanRecord,
    fieldUtils,
    relationalFields,
    makeLegacyDialogMappingTestEnv,
    AbstractStorageService,
    RamStorage,
    patch,
    unpatch,
    ControlPanel,
    FieldOne2Many,
    AbstractFieldOwl,
    fieldRegistryOwl,
    cpHelpers;

async function clickDiscard(target) {
    await click(target.querySelector(".o_form_button_cancel"));
}

async function clickEdit(target) {
    await click(target.querySelector(".o_form_button_edit"));
}

async function clickSave(target) {
    await click(target.querySelector(".o_form_button_save"));
}

async function addRow(target) {
    await click(target.querySelector(".o_field_x2many_list_row_add a"));
}

async function removeRow(target, index) {
    await click(target.querySelectorAll(".o_list_record_remove")[index]);
}

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
                        qux: { string: "Qux", type: "float", digits: [16, 1] },
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
                        turtle_description: { string: "Description", type: "text" },
                        turtle_int: { string: "int", type: "integer", sortable: true },
                        turtle_qux: {
                            string: "Qux",
                            type: "float",
                            digits: [16, 1],
                            required: true,
                            default: 1.5,
                        },
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

        // patchWithCleanup(AutoComplete, {
        //     delay: 0,
        // });
        // patchWithCleanup(browser, {
        //     setTimeout: (fn) => fn(),
        // });
    });

    QUnit.module("One2ManyField");

    QUnit.skipWOWL(
        "New record with a o2m also with 2 new records, ordered, and resequenced",
        async function (assert) {
            assert.expect(2);

            // Needed to have two new records in a single stroke
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.p = [[5], [0, 0, { trululu: false }], [0, 0, { trululu: false }]];
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree editable="bottom" default_order="int_field">
                                <field name="int_field" widget="handle"/>
                                <field name="trululu"/>
                            </tree>
                        </field>
                    </form>`,
                viewOptions: {
                    mode: "create",
                },
                mockRPC(route, args) {
                    assert.step(args.method + " " + args.model);
                    return this._super(route, args);
                },
            });

            // change the int_field through drag and drop
            // that way, we'll trigger the sorting and the name_get
            // of the lines of "p"
            await testUtils.dom.dragAndDrop(
                form.$(".ui-sortable-handle").eq(1),
                form.$("tbody tr").first(),
                { position: "top" }
            );

            assert.verifySteps(["onchange partner"]);
        }
    );

    QUnit.skipWOWL(
        "O2M List with pager, decoration and default_order: add and cancel adding",
        async function (assert) {
            assert.expect(3);

            // The decoration on the list implies that its condition will be evaluated
            // against the data of the field (actual records *displayed*)
            // If one data is wrongly formed, it will crash
            // This test adds then cancels a record in a paged, ordered, and decorated list
            // That implies prefetching of records for sorting
            // and evaluation of the decoration against *visible records*

            serverData.models.partner.records[0].p = [2, 4];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom" limit="1" decoration-muted="foo != False" default_order="display_name">
                                <field name="foo" invisible="1"/>
                                <field name="display_name" />
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            await click(target, ".o_form_button_edit");

            await click(
                target.querySelector(".o_field_x2many_list .o_field_x2many_list_row_add a")
            );

            assert.containsN(
                target,
                ".o_field_x2many_list .o_data_row",
                2,
                "There should be 2 rows"
            );

            const expectedSelectedRow = target.querySelectorAll(
                ".o_field_x2many_list .o_data_row"
            )[1];
            const actualSelectedRow = target.querySelector(".o_selected_row");
            assert.equal(
                actualSelectedRow[0],
                expectedSelectedRow[0],
                "The selected row should be the new one"
            );

            // Cancel Creation
            await actualSelectedRow
                .querySelector("input")
                .dispatchEvent(new KeyboardEvent("keydown"));
            await nextTick();
            assert.containsOnce(
                target,
                ".o_field_x2many_list .o_data_row",
                "There should be 1 row"
            );
        }
    );

    QUnit.skipWOWL("O2M with parented m2o and domain on parent.m2o", async function (assert) {
        assert.expect(4);

        /* records in an o2m can have a m2o pointing to themselves
         * in that case, a domain evaluation on that field followed by name_search
         * shouldn't send virtual_ids to the server
         */

        serverData.models.turtle.fields.parent_id = {
            string: "Parent",
            type: "many2one",
            relation: "turtle",
        };
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="parent_id"/>
                        </tree>
                    </field>
                </form>`,
            archs: {
                "turtle,false,form": `<form><field name="parent_id" domain="[('id', 'in', parent.turtles)]"/></form>`,
            },
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/turtle/name_search") {
                    // We are going to pass twice here
                    // First time, we really have nothing
                    // Second time, a virtual_id has been created
                    assert.deepEqual(args.kwargs.args, [["id", "in", []]]);
                }
                return this._super(route, args);
            },
        });

        await click(form.$(".o_field_x2many_list[name=turtles] .o_field_x2many_list_row_add a"));

        await testUtils.fields.many2one.createAndEdit("parent_id");

        var $modal = $(".modal-content");

        await click($modal.eq(1).find(".modal-footer .btn-primary").eq(0));
        await click($modal.eq(0).find(".modal-footer .btn-primary").eq(1));

        assert.containsOnce(
            form,
            ".o_data_row",
            "The main record should have the new record in its o2m"
        );

        $modal = $(".modal-content");
        await click($modal.find(".o_field_many2one input"));
    });

    QUnit.skipWOWL("one2many list editable with cell readonly modifier", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].turtles = [1, 2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="turtles" invisible="1"/>
                            <field name="foo" attrs="{&quot;readonly&quot; : [(&quot;turtles&quot;, &quot;!=&quot;, [])] }"/>
                            <field name="qux" attrs="{&quot;readonly&quot; : [(&quot;turtles&quot;, &quot;!=&quot;, [])] }"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.deepEqual(
                        args.args[1].p[1][2],
                        { foo: "ff", qux: 99 },
                        "The right values should be written"
                    );
                }
                return this._super(route, args);
            },
        });

        await clickEdit(target);
        await addRow(target);

        var $targetInput = $(".o_selected_row .o_input[name=foo]");
        assert.equal(
            $targetInput[0],
            document.activeElement,
            "The first input of the line should have the focus"
        );

        // Simulating hitting the 'f' key twice
        await testUtils.fields.editInput($targetInput, "f");
        await testUtils.fields.editInput($targetInput, $targetInput.val() + "f");

        assert.equal(
            $targetInput[0],
            document.activeElement,
            "The first input of the line should still have the focus"
        );

        // Simulating a TAB key
        await testUtils.fields.triggerKeydown($targetInput, "tab");

        var $secondTarget = $(".o_selected_row .o_input[name=qux]");

        assert.equal(
            $secondTarget[0],
            document.activeElement,
            "The second input of the line should have the focus after the TAB press"
        );

        await testUtils.fields.editInput($secondTarget, 9);
        await testUtils.fields.editInput($secondTarget, $secondTarget.val() + 9);

        await clickSave(target);
    });

    QUnit.test("one2many basic properties", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="Partner page">
                                <field name="p">
                                    <tree>
                                        <field name="foo"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method !== "read") {
                    throw new Error("No rpc apart from read");
                }
            },
        });

        assert.containsNone(target, "td.o_list_record_selector");
        assert.containsOnce(target, ".o_field_x2many_list_row_add");
        assert.containsOnce(target, "td.o_list_record_remove", 1);

        await clickEdit(target);

        assert.containsOnce(target, ".o_field_x2many_list_row_add");
        assert.hasAttrValue(target.querySelector(".o_field_x2many_list_row_add"), "colspan", "2");

        assert.containsOnce(target, "td.o_list_record_remove", 1);
    });

    QUnit.test("transferring class attributes in one2many sub fields", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_foo" class="hey"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.containsOnce(target, "td.hey");

        await clickEdit(target);
        assert.containsOnce(target, "td.hey");

        await click(target.querySelector("td.o_data_cell"));
        assert.containsOnce(target, 'td.hey div[name="turtle_foo"] input'); // WOWL to check! hey on input?
    });

    QUnit.test("one2many with date and datetime", async function (assert) {
        const originalZone = luxon.Settings.defaultZone;
        luxon.Settings.defaultZone = new luxon.FixedOffsetZone.instance(120);
        registerCleanup(() => {
            luxon.Settings.defaultZone = originalZone;
        });
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="Partner page">
                                <field name="p">
                                    <tree>
                                        <field name="date"/>
                                        <field name="datetime"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });
        assert.strictEqual(target.querySelector("td").innerText, "01/25/2017");
        assert.strictEqual(target.querySelectorAll("td")[1].innerText, "12/12/2016 12:55:05");
    });

    QUnit.test("rendering with embedded one2many", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="P page">
                                <field name="p">
                                    <tree>
                                        <field name="foo"/>
                                        <field name="bar"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });
        const firstHeader = target.querySelector("thead th");
        assert.strictEqual(firstHeader.innerText, "Foo");
        const firstValue = target.querySelector("tbody td");
        assert.strictEqual(firstValue.innerText, "blip");
    });

    QUnit.test(
        "use the limit attribute in arch (in field o2m inline tree view)",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [1, 2, 3];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.model === "turtle") {
                        assert.deepEqual(args.args[0], [1, 2]);
                    }
                },
            });
            assert.containsN(target, ".o_data_row", 2);
        }
    );

    QUnit.skipNotInline(
        "use the limit attribute in arch (in field o2m non inline tree view)",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].turtles = [1, 2, 3];
            serverData.views = {
                "turtle,false,list": `
                    <tree limit="2">
                        <field name="turtle_foo"/>
                    </tree>
                `,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="turtles"/></form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.model === "turtle" && args.method === "read") {
                        assert.deepEqual(args.args[0], [1, 2]);
                    }
                },
            });
            assert.containsN(target, ".o_data_row", 2);
        }
    );

    QUnit.skipNotInline("one2many with default_order on view not inline", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records[0].turtles = [1, 2, 3];
        serverData.views = {
            "turtle,false,list": `
                <tree default_order="turtle_foo">
                    <field name="turtle_int"/>
                    <field name="turtle_foo"/>
                </tree>
            `,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="Turtles">
                                <field name="turtles"/>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_one2many .o_data_cell")].map(
                (el) => el.innerText
            ),
            ["9", "blip", "21", "kawa", "0", "yop"]
        );
    });

    QUnit.test("embedded one2many with widget", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="P page">
                                <field name="p">
                                    <tree>
                                        <field name="int_field" widget="handle"/>
                                        <field name="foo"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, "span.o_row_handle");
    });

    QUnit.skipWOWL("embedded one2many with handle widget", async function (assert) {
        assert.expect(10);

        let nbConfirmChange = 0;
        patchWithCleanup(ListRenderer.prototype, {
            confirmChange: () => {
                nbConfirmChange++;
                return this._super(...arguments);
            },
        });

        serverData.models.partner.records[0].turtles = [1, 2, 3];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="P page">
                                <field name="turtles">
                                    <tree default_order="turtle_int">
                                        <field name="turtle_int" widget="handle"/>
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });

        testUtils.mock.intercept(
            form,
            "field_changed",
            function (event) {
                assert.step(event.data.changes.turtles.data.turtle_int.toString());
            },
            true
        );

        assert.strictEqual(
            form.$("td.o_data_cell:not(.o_handle_cell)").text(),
            "yopblipkawa",
            "should have the 3 rows in the correct order"
        );

        await clickEdit(target);

        assert.strictEqual(
            form.$("td.o_data_cell:not(.o_handle_cell)").text(),
            "yopblipkawa",
            "should still have the 3 rows in the correct order"
        );
        assert.strictEqual(nbConfirmChange, 0, "should not have confirmed any change yet");

        // Drag and drop the second line in first position
        await testUtils.dom.dragAndDrop(
            form.$(".ui-sortable-handle").eq(1),
            form.$("tbody tr").first(),
            { position: "top" }
        );

        assert.strictEqual(nbConfirmChange, 1, "should have confirmed changes only once");
        assert.verifySteps(
            ["0", "1"],
            "sequences values should be incremental starting from the previous minimum one"
        );

        assert.strictEqual(
            form.$("td.o_data_cell:not(.o_handle_cell)").text(),
            "blipyopkawa",
            "should have the 3 rows in the new order"
        );

        await clickSave(target);

        assert.deepEqual(
            _.map(serverData.models.turtle.records, function (turtle) {
                return _.pick(turtle, "id", "turtle_foo", "turtle_int");
            }),
            [
                { id: 1, turtle_foo: "yop", turtle_int: 1 },
                { id: 2, turtle_foo: "blip", turtle_int: 0 },
                { id: 3, turtle_foo: "kawa", turtle_int: 21 },
            ],
            "should have save the changed sequence"
        );

        assert.strictEqual(
            form.$("td.o_data_cell:not(.o_handle_cell)").text(),
            "blipyopkawa",
            "should still have the 3 rows in the new order"
        );

        testUtils.mock.unpatch(ListRenderer);
    });

    QUnit.test("onchange for embedded one2many in a one2many", async function (assert) {
        serverData.models.turtle.fields.partner_ids.type = "one2many";
        serverData.models.turtle.records[0].partner_ids = [1];
        serverData.models.partner.records[0].turtles = [1];

        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [
                    [5, false, false],
                    [
                        1,
                        1,
                        {
                            turtle_foo: "hop",
                            partner_ids: [
                                [5, false, false],
                                [4, 1, false],
                            ],
                        },
                    ],
                ];
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "write") {
                    const expectedResultTurtles = [[1, 1, { turtle_foo: "hop" }]];
                    assert.deepEqual(args.args[1].turtles, expectedResultTurtles);
                }
            },
        });

        await clickEdit(target);
        await click(target.querySelectorAll(".o_data_cell")[1]);
        await editInput(target, ".o_selected_row .o_field_widget[name=turtle_foo] input", "hop");
        await clickSave(target);
    });

    // TODO (DAM)
    QUnit.skipWOWL(
        "onchange for embedded one2many in a one2many with a second page",
        async function (assert) {
            serverData.models.turtle.fields.partner_ids.type = "one2many";
            serverData.models.turtle.records[0].partner_ids = [1];
            // we need a second page, so we set two records and only display one per page
            serverData.models.partner.records[0].turtles = [1];
            // serverData.models.partner.records[0].turtles = [1, 2];

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [5, false, false],
                        [
                            1,
                            1,
                            {
                                turtle_foo: "hop",
                                partner_ids: [
                                    [5, false, false],
                                    [4, 1, false],
                                ],
                            },
                        ],
                        // [1, 2, {
                        //     turtle_foo: "blip",
                        //     partner_ids: [[5, false, false], [4, 2, false], [4, 4, false]],
                        // }],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom" limit="1">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "write") {
                        const expectedResultTurtles = [
                            [1, 1, { turtle_foo: "hop" }],
                            // [1, 2, {
                            //     partner_ids: [[4, 2, false], [4, 4, false]],
                            //     turtle_foo: "blip",
                            // }],
                        ];
                        assert.deepEqual(args.args[1].turtles, expectedResultTurtles);
                    }
                },
            });

            await clickEdit(target);
            await click(target.querySelectorAll(".o_data_cell")[1]);
            await editInput(
                target,
                ".o_selected_row .o_field_widget[name=turtle_foo] input",
                "hop"
            );
            await clickSave(target);
        }
    );

    QUnit.skipWOWL(
        "onchange for embedded one2many in a one2many updated by server",
        async function (assert) {
            // here we test that after an onchange, the embedded one2many field has
            // been updated by a new list of ids by the server response, to this new
            // list should be correctly sent back at save time
            assert.expect(3);

            serverData.models.turtle.fields.partner_ids.type = "one2many";
            serverData.models.partner.records[0].turtles = [2];
            serverData.models.turtle.records[1].partner_ids = [2];

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [5],
                        [
                            1,
                            2,
                            {
                                turtle_foo: "hop",
                                partner_ids: [[5], [4, 2], [4, 4]],
                            },
                        ],
                    ];
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (route === "/web/dataset/call_kw/partner/write") {
                        var expectedResultTurtles = [
                            [
                                1,
                                2,
                                {
                                    partner_ids: [
                                        [4, 2, false],
                                        [4, 4, false],
                                    ],
                                    turtle_foo: "hop",
                                },
                            ],
                        ];
                        assert.deepEqual(
                            args.args[1].turtles,
                            expectedResultTurtles,
                            "The right values should be written"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.deepEqual(
                form.$(".o_data_cell.o_many2many_tags_cell").text().trim(),
                "second record",
                "the partner_ids should be as specified at initialization"
            );

            await clickEdit(target);
            await click(form.$(".o_data_cell").eq(1));
            var $cell = form.$(".o_selected_row .o_input[name=turtle_foo]");
            await testUtils.fields.editSelect($cell, "hop");
            await clickSave(target);

            assert.deepEqual(
                form.$(".o_data_cell.o_many2many_tags_cell").text().trim().split(/\s+/),
                ["second", "record", "aaa"],
                "The partner_ids should have been updated"
            );
        }
    );

    QUnit.skipWOWL("onchange for embedded one2many with handle widget", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].turtles = [1, 2, 3];
        var partnerOnchange = 0;
        serverData.models.partner.onchanges = {
            turtles: function () {
                partnerOnchange++;
            },
        };
        var turtleOnchange = 0;
        serverData.models.turtle.onchanges = {
            turtle_int: function () {
                turtleOnchange++;
            },
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="P page">
                                <field name="turtles">
                                    <tree default_order="turtle_int">
                                        <field name="turtle_int" widget="handle"/>
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });

        await clickEdit(target);

        // Drag and drop the second line in first position
        await testUtils.dom.dragAndDrop(
            form.$(".ui-sortable-handle").eq(1),
            form.$("tbody tr").first(),
            { position: "top" }
        );

        assert.strictEqual(turtleOnchange, 2, "should trigger one onchange per line updated");
        assert.strictEqual(partnerOnchange, 1, "should trigger only one onchange on the parent");
    });

    QUnit.skipWOWL(
        "onchange for embedded one2many with handle widget using same sequence",
        async function (assert) {
            assert.expect(4);

            serverData.models.turtle.records[0].turtle_int = 1;
            serverData.models.turtle.records[1].turtle_int = 1;
            serverData.models.turtle.records[2].turtle_int = 1;
            serverData.models.partner.records[0].turtles = [1, 2, 3];
            var turtleOnchange = 0;
            serverData.models.turtle.onchanges = {
                turtle_int: function () {
                    turtleOnchange++;
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <notebook>
                                <page string="P page">
                                    <field name="turtles">
                                        <tree default_order="turtle_int">
                                            <field name="turtle_int" widget="handle"/>
                                            <field name="turtle_foo"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(
                            args.args[1].turtles,
                            [
                                [1, 2, { turtle_int: 1 }],
                                [1, 1, { turtle_int: 2 }],
                                [1, 3, { turtle_int: 3 }],
                            ],
                            "should change all lines that have changed (the first one doesn't change because it has the same sequence)"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await clickEdit(target);

            assert.strictEqual(
                form.$("td.o_data_cell:not(.o_handle_cell)").text(),
                "yopblipkawa",
                "should have the 3 rows in the correct order"
            );

            // Drag and drop the second line in first position
            await testUtils.dom.dragAndDrop(
                form.$(".ui-sortable-handle").eq(1),
                form.$("tbody tr").first(),
                { position: "top" }
            );

            assert.strictEqual(
                form.$("td.o_data_cell:not(.o_handle_cell)").text(),
                "blipyopkawa",
                "should still have the 3 rows in the correct order"
            );
            assert.strictEqual(turtleOnchange, 3, "should update all lines");

            await clickSave(target);
        }
    );

    QUnit.skipWOWL(
        "onchange (with command 5) for embedded one2many with handle widget",
        async function (assert) {
            assert.expect(3);

            var ids = [];
            for (var i = 10; i < 50; i++) {
                var id = 10 + i;
                ids.push(id);
                serverData.models.turtle.records.push({
                    id: id,
                    turtle_int: 0,
                    turtle_foo: "#" + id,
                });
            }
            ids.push(1, 2, 3);
            serverData.models.partner.records[0].turtles = ids;
            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [[5]].concat(obj.turtles);
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="turtles">
                                    <tree editable="bottom" default_order="turtle_int">
                                        <field name="turtle_int" widget="handle"/>
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            await click(form.$(".o_field_widget[name=turtles] .o_pager_next"));
            assert.strictEqual(
                form.$("td.o_data_cell:not(.o_handle_cell)").text(),
                "yopblipkawa",
                "should have the 3 rows in the correct order"
            );

            await clickEdit(target);
            await click(form.$(".o_field_one2many .o_list_view tbody tr:first td:first"));
            await testUtils.fields.editInput(
                form.$(".o_field_one2many .o_list_view tbody tr:first input:first"),
                "blurp"
            );

            // Drag and drop the third line in second position
            await testUtils.dom.dragAndDrop(
                form.$(".ui-sortable-handle").eq(2),
                form.$(".o_field_one2many tbody tr").eq(1),
                { position: "top" }
            );

            assert.strictEqual(
                form.$(".o_data_cell").text(),
                "blurpkawablip",
                "should display to record in 'turtle_int' order"
            );

            await clickSave(target);
            await click(form.$(".o_field_widget[name=turtles] .o_pager_next"));

            assert.strictEqual(
                form.$(".o_data_cell:not(.o_handle_cell)").text(),
                "blurpkawablip",
                "should display to record in 'turtle_int' order"
            );
        }
    );

    QUnit.skipWOWL(
        "onchange with modifiers for embedded one2many on the second page",
        async function (assert) {
            assert.expect(9);

            var data = this.data;
            var ids = [];
            for (var i = 10; i < 60; i++) {
                var id = 10 + i;
                ids.push(id);
                data.turtle.records.push({
                    id: id,
                    turtle_int: 0,
                    turtle_foo: "#" + id,
                });
            }
            ids.push(1, 2, 3);
            data.partner.records[0].turtles = ids;
            data.partner.onchanges = {
                turtles: function (obj) {
                    // TODO: make this test more 'difficult'
                    // For now, the server only returns UPDATE commands (no LINK TO)
                    // even though it should do it (for performance reasons)
                    // var turtles = obj.turtles.splice(0, 20);

                    var turtles = [];
                    turtles.unshift([5]);
                    // create UPDATE commands for each records (this is the server
                    // usual answer for onchange)
                    for (var k in obj.turtles) {
                        var change = obj.turtles[k];
                        var record = _.findWhere(data.turtle.records, { id: change[1] });
                        if (change[0] === 1) {
                            _.extend(record, change[2]);
                        }
                        turtles.push([1, record.id, record]);
                    }
                    obj.turtles = turtles;
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                data: data,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="turtles">
                                    <tree editable="bottom" default_order="turtle_int" limit="10">
                                        <field name="turtle_int" widget="handle"/>
                                        <field name="turtle_foo"/>
                                        <field name="turtle_qux" attrs="{'readonly': [('turtle_foo', '=', False)]}"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });
            await clickEdit(target);

            assert.equal(
                form.$(".o_field_one2many .o_list_char").text(),
                "#20#21#22#23#24#25#26#27#28#29",
                "should display the records in order"
            );

            await click(form.$(".o_field_one2many .o_list_view tbody tr:first td:first"));
            await testUtils.fields.editInput(
                form.$(".o_field_one2many .o_list_view tbody tr:first input:first"),
                "blurp"
            );

            // click on the label to unselect the row
            await click(form.$(".o_form_label"));

            assert.equal(
                form.$(".o_field_one2many .o_list_char").text(),
                "blurp#21#22#23#24#25#26#27#28#29",
                "should display the records in order with the changes"
            );

            // the domain fail if the widget does not use the already loaded data.
            await clickDiscard(target);
            assert.containsNone(document.body, ".modal", "should not open modal");

            assert.equal(
                form.$(".o_field_one2many .o_list_char").text(),
                "#20#21#22#23#24#25#26#27#28#29",
                "should cancel changes and display the records in order"
            );

            await clickEdit(target);

            // Drag and drop the third line in second position
            await testUtils.dom.dragAndDrop(
                form.$(".ui-sortable-handle").eq(2),
                form.$(".o_field_one2many tbody tr").eq(1),
                { position: "top" }
            );

            assert.equal(
                form.$(".o_field_one2many .o_list_char").text(),
                "#20#30#31#32#33#34#35#36#37#38",
                "should display the records in order after resequence (display record with turtle_int=0)"
            );

            // Drag and drop the third line in second position
            await testUtils.dom.dragAndDrop(
                form.$(".ui-sortable-handle").eq(2),
                form.$(".o_field_one2many tbody tr").eq(1),
                { position: "top" }
            );

            assert.equal(
                form.$(".o_field_one2many .o_list_char").text(),
                "#20#39#40#41#42#43#44#45#46#47",
                "should display the records in order after resequence (display record with turtle_int=0)"
            );

            await click(form.$(".o_form_label"));
            assert.equal(
                form.$(".o_field_one2many .o_list_char").text(),
                "#20#39#40#41#42#43#44#45#46#47",
                "should display the records in order after resequence"
            );

            await clickDiscard(target);
            assert.containsNone(document.body, ".modal", "should not open modal");

            assert.equal(
                form.$(".o_field_one2many .o_list_char").text(),
                "#20#21#22#23#24#25#26#27#28#29",
                "should cancel changes and display the records in order"
            );
        }
    );

    QUnit.skipWOWL("onchange followed by edition on the second page", async function (assert) {
        assert.expect(12);

        var ids = [];
        for (var i = 1; i < 85; i++) {
            var id = 10 + i;
            ids.push(id);
            serverData.models.turtle.records.push({
                id: id,
                turtle_int: (id / 3) | 0,
                turtle_foo: "#" + i,
            });
        }
        ids.splice(41, 0, 1, 2, 3);
        serverData.models.partner.records[0].turtles = ids;
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [[5]].concat(obj.turtles);
            },
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="turtles">
                                <tree editable="top" default_order="turtle_int">
                                    <field name="turtle_int" widget="handle"/>
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        await clickEdit(target);
        await click(form.$(".o_field_widget[name=turtles] .o_pager_next"));

        await click(form.$(".o_field_one2many .o_list_view tbody tr:eq(1) td:first"));
        await testUtils.fields.editInput(
            form.$(".o_field_one2many .o_list_view tbody tr:eq(1) input:first"),
            "value 1"
        );
        await click(form.$(".o_field_one2many .o_list_view tbody tr:eq(2) td:first"));
        await testUtils.fields.editInput(
            form.$(".o_field_one2many .o_list_view tbody tr:eq(2) input:first"),
            "value 2"
        );

        assert.containsN(form, ".o_data_row", 40, "should display 40 records");
        assert.strictEqual(
            form.$(".o_data_row:has(.o_data_cell:contains(#39))").index(),
            0,
            "should display '#39' at the first line"
        );

        await addRow(target);

        assert.containsN(form, ".o_data_row", 40, "should display 39 records and the create line");
        assert.containsOnce(
            form,
            ".o_data_row:first .o_field_char",
            "should display the create line in first position"
        );
        assert.strictEqual(
            form.$(".o_data_row:first .o_field_char").val(),
            "",
            "should an empty input"
        );
        assert.strictEqual(
            form.$(".o_data_row:has(.o_data_cell:contains(#39))").index(),
            1,
            "should display '#39' at the second line"
        );

        await testUtils.fields.editInput(form.$(".o_data_row input:first"), "value 3");

        assert.containsOnce(
            form,
            ".o_data_row:first .o_field_char",
            "should display the create line in first position after onchange"
        );
        assert.strictEqual(
            form.$(".o_data_row:has(.o_data_cell:contains(#39))").index(),
            1,
            "should display '#39' at the second line after onchange"
        );

        await addRow(target);

        assert.containsN(form, ".o_data_row", 40, "should display 39 records and the create line");
        assert.containsOnce(
            form,
            ".o_data_row:first .o_field_char",
            "should display the create line in first position"
        );
        assert.strictEqual(
            form.$(".o_data_row:has(.o_data_cell:contains(value 3))").index(),
            1,
            "should display the created line at the second position"
        );
        assert.strictEqual(
            form.$(".o_data_row:has(.o_data_cell:contains(#39))").index(),
            2,
            "should display '#39' at the third line"
        );
    });

    QUnit.skipWOWL(
        "onchange followed by edition on the second page (part 2)",
        async function (assert) {
            assert.expect(8);

            var ids = [];
            for (var i = 1; i < 85; i++) {
                var id = 10 + i;
                ids.push(id);
                serverData.models.turtle.records.push({
                    id: id,
                    turtle_int: (id / 3) | 0,
                    turtle_foo: "#" + i,
                });
            }
            ids.splice(41, 0, 1, 2, 3);
            serverData.models.partner.records[0].turtles = ids;
            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [[5]].concat(obj.turtles);
                },
            };

            // bottom order

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="turtles">
                                    <tree editable="bottom" default_order="turtle_int">
                                        <field name="turtle_int" widget="handle"/>
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            await clickEdit(target);
            await click(form.$(".o_field_widget[name=turtles] .o_pager_next"));

            await click(form.$(".o_field_one2many .o_list_view tbody tr:eq(1) td:first"));
            await testUtils.fields.editInput(
                form.$(".o_field_one2many .o_list_view tbody tr:eq(1) input:first"),
                "value 1"
            );
            await click(form.$(".o_field_one2many .o_list_view tbody tr:eq(2) td:first"));
            await testUtils.fields.editInput(
                form.$(".o_field_one2many .o_list_view tbody tr:eq(2) input:first"),
                "value 2"
            );

            assert.containsN(form, ".o_data_row", 40, "should display 40 records");
            assert.strictEqual(
                form.$(".o_data_row:has(.o_data_cell:contains(#77))").index(),
                39,
                "should display '#77' at the last line"
            );

            await addRow(target);

            assert.containsN(
                form,
                ".o_data_row",
                41,
                "should display 41 records and the create line"
            );
            assert.strictEqual(
                form.$(".o_data_row:has(.o_data_cell:contains(#76))").index(),
                38,
                "should display '#76' at the penultimate line"
            );
            assert.strictEqual(
                form.$(".o_data_row:has(.o_field_char)").index(),
                40,
                "should display the create line at the last position"
            );

            await testUtils.fields.editInput(form.$(".o_data_row input:first"), "value 3");
            await addRow(target);

            assert.containsN(
                form,
                ".o_data_row",
                42,
                "should display 42 records and the create line"
            );
            assert.strictEqual(
                form.$(".o_data_row:has(.o_data_cell:contains(#76))").index(),
                38,
                "should display '#76' at the penultimate line"
            );
            assert.strictEqual(
                form.$(".o_data_row:has(.o_field_char)").index(),
                41,
                "should display the create line at the last position"
            );
        }
    );

    QUnit.skipWOWL("onchange returning a command 6 for an x2many", async function (assert) {
        serverData.models.partner.onchanges = {
            foo(obj) {
                obj.turtles = [[6, false, [1, 2, 3]]];
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                        <tree>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await clickEdit(target);

        assert.containsOnce(target, ".o_data_row");

        // change the value of foo to trigger the onchange
        await editInput(target, ".o_field_widget[name=foo] input", "some value");

        assert.containsN(target, ".o_data_row", 3);
    });

    QUnit.test(
        "x2many fields inside x2manys are fetched after an onchange",
        async function (assert) {
            assert.expect(6);

            serverData.models.turtle.records[0].partner_ids = [1];
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [[5], [4, 1], [4, 2], [4, 3]];
                },
            };

            let checkRPC = false;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="foo"/>
                                <field name="turtles">
                                    <tree>
                                        <field name="turtle_foo"/>
                                        <field name="partner_ids" widget="many2many_tags"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                mockRPC(route, args) {
                    if (checkRPC && args.method === "read" && args.model === "partner") {
                        assert.deepEqual(
                            args.args[1],
                            ["display_name"],
                            "should only read the display_name for the m2m tags"
                        );
                        assert.deepEqual(
                            args.args[0],
                            [1],
                            "should only read the display_name of the unknown record"
                        );
                    }
                },
                resId: 1,
            });

            await clickEdit(target);
            assert.containsOnce(
                target,
                ".o_data_row",
                "there should be one record in the relation"
            );
            assert.strictEqual(
                target
                    .querySelector(".o_data_row .o_field_widget[name=partner_ids]")
                    .innerText.replace(/\s/g, ""),
                "secondrecordaaa",
                "many2many_tags should be correctly displayed"
            );

            // change the value of foo to trigger the onchange
            checkRPC = true; // enable flag to check read RPC for the m2m field
            await editInput(target, ".o_field_widget[name=foo] input", "some value");

            assert.containsN(
                target,
                ".o_data_row",
                3,
                "there should be three records in the relation"
            );
            assert.strictEqual(
                target
                    .querySelector(".o_data_row .o_field_widget[name=partner_ids]")
                    .innerText.trim(),
                "first record",
                "many2many_tags should be correctly displayed"
            );
        }
    );

    QUnit.skipWOWL(
        "reference fields inside x2manys are fetched after an onchange",
        async function (assert) {
            assert.expect(5);

            serverData.models.turtle.records[1].turtle_ref = "product,41";
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [[5], [4, 1], [4, 2], [4, 3]];
                },
            };

            var checkRPC = false;
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="foo"/>
                                <field name="turtles">
                                    <tree>
                                        <field name="turtle_foo"/>
                                        <field name="turtle_ref" class="ref_field"/>
                                        </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                mockRPC(route, args) {
                    if (checkRPC && args.method === "name_get") {
                        assert.deepEqual(
                            args.args[0],
                            [37],
                            "should only fetch the name_get of the unknown record"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.containsOnce(form, ".o_data_row", "there should be one record in the relation");
            assert.strictEqual(
                form.$(".ref_field").text().trim(),
                "xpad",
                "reference field should be correctly displayed"
            );

            // change the value of foo to trigger the onchange
            checkRPC = true; // enable flag to check read RPC for reference field
            await testUtils.fields.editInput(form.$(".o_field_widget[name=foo]"), "some value");

            assert.containsN(
                form,
                ".o_data_row",
                3,
                "there should be three records in the relation"
            );
            assert.strictEqual(
                form.$(".ref_field").text().trim(),
                "xpadxphone",
                "reference fields should be correctly displayed"
            );
        }
    );

    QUnit.skipWOWL("onchange on one2many containing x2many in form view", async function (assert) {
        assert.expect(16);

        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.turtles = [[0, false, { turtle_foo: "new record" }]];
            },
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                        <tree>
                            <field name="turtle_foo"/>
                        </tree>
                        <form>
                            <field name="partner_ids">
                                <tree editable="top">
                                    <field name="foo"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
            archs: {
                "partner,false,list": '<tree><field name="foo"/></tree>',
                "partner,false,search": "<search></search>",
            },
        });

        assert.containsOnce(
            form,
            ".o_data_row",
            "the onchange should have created one record in the relation"
        );

        // open the created o2m record in a form view, and add a m2m subrecord
        // in its relation
        await click(form.$(".o_data_row"));

        assert.strictEqual($(".modal").length, 1, "should have opened a dialog");
        assert.strictEqual(
            $(".modal .o_data_row").length,
            0,
            "there should be no record in the one2many in the dialog"
        );

        // add a many2many subrecord
        await click($(".modal .o_field_x2many_list_row_add a"));

        assert.strictEqual($(".modal").length, 2, "should have opened a second dialog");

        // select a many2many subrecord
        await click($(".modal:nth(1) .o_list_view .o_data_cell:first"));

        assert.strictEqual($(".modal").length, 1, "second dialog should be closed");
        assert.strictEqual(
            $(".modal .o_data_row").length,
            1,
            "there should be one record in the one2many in the dialog"
        );
        assert.containsNone(
            $(".modal"),
            ".o_x2m_control_panel .o_pager",
            "m2m pager should be hidden"
        );

        // click on 'Save & Close'
        await click($(".modal-footer .btn-primary:first"));

        assert.strictEqual($(".modal").length, 0, "dialog should be closed");

        // reopen o2m record, and another m2m subrecord in its relation, but
        // discard the changes
        await click(form.$(".o_data_row"));

        assert.strictEqual($(".modal").length, 1, "should have opened a dialog");
        assert.strictEqual(
            $(".modal .o_data_row").length,
            1,
            "there should be one record in the one2many in the dialog"
        );

        // add another m2m subrecord
        await click($(".modal .o_field_x2many_list_row_add a"));

        assert.strictEqual($(".modal").length, 2, "should have opened a second dialog");

        await click($(".modal:nth(1) .o_list_view .o_data_cell:first"));

        assert.strictEqual($(".modal").length, 1, "second dialog should be closed");
        assert.strictEqual(
            $(".modal .o_data_row").length,
            2,
            "there should be two records in the one2many in the dialog"
        );

        // click on 'Discard'
        await click($(".modal-footer .btn-secondary"));

        assert.strictEqual($(".modal").length, 0, "dialog should be closed");

        // reopen o2m record to check that second changes have properly been discarded
        await click(form.$(".o_data_row"));

        assert.strictEqual($(".modal").length, 1, "should have opened a dialog");
        assert.strictEqual(
            $(".modal .o_data_row").length,
            1,
            "there should be one record in the one2many in the dialog"
        );
    });

    QUnit.test(
        "onchange on one2many with x2many in list (no widget) and form view (list)",
        async function (assert) {
            serverData.models.turtle.fields.turtle_foo.default = "a default value";
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.p = [[0, false, { turtles: [[0, false, { turtle_foo: "hello" }]] }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree>
                                <field name="turtles"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="top">
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
            });

            assert.containsOnce(
                target,
                ".o_data_row",
                "the onchange should have created one record in the relation"
            );

            // open the created o2m record in a form view
            await click(target.querySelector(".o_data_row .o_data_cell"));

            assert.containsOnce(document.body, ".modal", "should have opened a dialog");
            assert.containsOnce(document.body, ".modal .o_data_row");
            assert.strictEqual(
                document.querySelector(".modal .o_data_row").innerText.trim(),
                "hello"
            );

            // add a one2many subrecord and check if the default value is correctly applied
            await click(document.querySelector(".modal .o_field_x2many_list_row_add a"));

            assert.containsN(document.body, ".modal .o_data_row", 2);
            assert.strictEqual(
                document.querySelector(".modal .o_data_row .o_field_widget[name=turtle_foo] input")
                    .value,
                "a default value"
            );
        }
    );

    QUnit.test(
        "onchange on one2many with x2many in list (many2many_tags) and form view (list)",
        async function (assert) {
            serverData.models.turtle.fields.turtle_foo.default = "a default value";
            serverData.models.partner.onchanges = {
                foo: function (obj) {
                    obj.p = [[0, false, { turtles: [[0, false, { turtle_foo: "hello" }]] }]];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree>
                             <field name="turtles" widget="many2many_tags"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="top">
                                        <field name="turtle_foo"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
            });

            assert.containsOnce(
                target,
                ".o_data_row",
                "the onchange should have created one record in the relation"
            );

            // open the created o2m record in a form view
            await click(target.querySelector(".o_data_row .o_data_cell"));

            assert.containsOnce(document.body, ".modal", "should have opened a dialog");
            assert.containsOnce(document.body, ".modal .o_data_row");
            assert.strictEqual(
                document.querySelector(".modal .o_data_row").innerText.trim(),
                "hello"
            );

            // add a one2many subrecord and check if the default value is correctly applied
            await click(document.querySelector(".modal .o_field_x2many_list_row_add a"));

            assert.containsN(document.body, ".modal .o_data_row", 2);
            assert.strictEqual(
                document.querySelector(".modal .o_data_row .o_field_widget[name=turtle_foo] input")
                    .value,
                "a default value"
            );
        }
    );

    QUnit.skipWOWL(
        "embedded one2many with handle widget with minimum setValue calls",
        async function (assert) {
            assert.expect(20);

            serverData.models.turtle.records[0].turtle_int = 6;
            serverData.models.turtle.records.push(
                {
                    id: 4,
                    turtle_int: 20,
                    turtle_foo: "a1",
                },
                {
                    id: 5,
                    turtle_int: 9,
                    turtle_foo: "a2",
                },
                {
                    id: 6,
                    turtle_int: 2,
                    turtle_foo: "a3",
                },
                {
                    id: 7,
                    turtle_int: 11,
                    turtle_foo: "a4",
                }
            );
            serverData.models.partner.records[0].turtles = [1, 2, 3, 4, 5, 6, 7];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree default_order="turtle_int">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            testUtils.mock.intercept(
                form,
                "field_changed",
                function (event) {
                    assert.step(String(form.model.get(event.data.changes.turtles.id)));
                },
                true
            );

            await clickEdit(target);

            var positions = [
                [6, 0, "top", ["3", "6", "1", "2", "5", "7", "4"]], // move the last to the first line
                [5, 1, "top", ["7", "6", "1", "2", "5"]], // move the penultimate to the second line
                [2, 5, "bottom", ["1", "2", "5", "6"]], // move the third to the penultimate line
            ];
            for (const [source, target, position, steps] of positions) {
                await testUtils.dom.dragAndDrop(
                    form.$(".ui-sortable-handle").eq(source),
                    form.$("tbody tr").eq(target),
                    { position: position }
                );

                await delay(10);

                assert.verifySteps(
                    steps,
                    "sequences values should be apply from the begin index to the drop index"
                );
            }
            assert.deepEqual(
                _.pluck(form.model.get(form.handle).data.turtles.data, "data"),
                [
                    { id: 3, turtle_foo: "kawa", turtle_int: 2 },
                    { id: 7, turtle_foo: "a4", turtle_int: 3 },
                    { id: 1, turtle_foo: "yop", turtle_int: 4 },
                    { id: 2, turtle_foo: "blip", turtle_int: 5 },
                    { id: 5, turtle_foo: "a2", turtle_int: 6 },
                    { id: 6, turtle_foo: "a3", turtle_int: 7 },
                    { id: 4, turtle_foo: "a1", turtle_int: 8 },
                ],
                "sequences must be apply correctly"
            );
        }
    );

    QUnit.skipWOWL("embedded one2many (editable list) with handle widget", async function (assert) {
        assert.expect(8);

        serverData.models.partner.records[0].p = [1, 2, 4];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="P page">
                                <field name="p">
                                    <tree editable="top">
                                        <field name="int_field" widget="handle"/>
                                        <field name="foo"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });

        testUtils.mock.intercept(
            form,
            "field_changed",
            function (event) {
                assert.step(event.data.changes.p.data.int_field.toString());
            },
            true
        );

        assert.strictEqual(
            form.$("td.o_data_cell:not(.o_handle_cell)").text(),
            "My little Foo Valueblipyop",
            "should have the 3 rows in the correct order"
        );

        await clickEdit(target);
        assert.strictEqual(
            form.$("td.o_data_cell:not(.o_handle_cell)").text(),
            "My little Foo Valueblipyop",
            "should still have the 3 rows in the correct order"
        );

        // Drag and drop the second line in first position
        await testUtils.dom.dragAndDrop(
            form.$(".ui-sortable-handle").eq(1),
            form.$("tbody tr").first(),
            { position: "top" }
        );

        assert.verifySteps(
            ["0", "1"],
            "sequences values should be incremental starting from the previous minimum one"
        );

        assert.strictEqual(
            form.$("td.o_data_cell:not(.o_handle_cell)").text(),
            "blipMy little Foo Valueyop",
            "should have the 3 rows in the new order"
        );

        await click(form.$("tbody tr:first td:first"));

        assert.strictEqual(
            form.$("tbody tr:first td.o_data_cell:not(.o_handle_cell) input").val(),
            "blip",
            "should edit the correct row"
        );

        await clickSave(target);
        assert.strictEqual(
            form.$("td.o_data_cell:not(.o_handle_cell)").text(),
            "blipMy little Foo Valueyop",
            "should still have the 3 rows in the new order"
        );
    });

    QUnit.test("one2many field when using the pager", async function (assert) {
        const ids = [];
        for (let i = 0; i < 45; i++) {
            const id = 10 + i;
            ids.push(id);
            serverData.models.partner.records.push({
                id,
                display_name: `relational record ${id}`,
            });
        }
        serverData.models.partner.records[0].p = ids.slice(0, 42);
        serverData.models.partner.records[1].p = ids.slice(42);

        let count = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div><t t-esc="record.display_name"/></div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            mockRPC() {
                count++;
            },
            resId: 1,
            resIds: [1, 2],
        });

        // we are on record 1, which has 90 related record (first 40 should be
        // displayed), 2 RPCs (read) should have been done, one on the main record
        // and one for the O2M
        assert.strictEqual(count, 2);
        assert.containsN(target, '.o_kanban_record:not(".o_kanban_ghost")', 40);

        // move to record 2, which has 3 related records (and shouldn't contain the
        // related records of record 1 anymore). Two additional RPCs should have
        // been done
        await click(target.querySelector(".o_form_view .o_control_panel .o_pager_next"));
        assert.strictEqual(count, 4);
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            3,
            "one2many kanban should contain 3 cards for record 2"
        );

        // move back to record 1, which should contain again its first 40 related
        // records
        await click(target.querySelector(".o_form_view .o_control_panel .o_pager_previous"));
        assert.strictEqual(count, 6);
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            40,
            "one2many kanban should contain 40 cards for record 1"
        );

        // move to the second page of the o2m: 1 RPC should have been done to fetch
        // the 2 subrecords of page 2, and those records should now be displayed
        await click(target.querySelector(".o_x2m_control_panel .o_pager_next"));
        assert.strictEqual(count, 7, "one RPC should have been done");
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            2,
            "one2many kanban should contain 2 cards for record 1 at page 2"
        );

        // move to record 2 again and check that everything is correctly updated
        await click(target.querySelector(".o_form_view .o_control_panel .o_pager_next"));
        assert.strictEqual(count, 9);
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            3,
            "one2many kanban should contain 3 cards for record 2"
        );

        // move back to record 1 and move to page 2 again: all data should have
        // been correctly reloaded
        await click(target.querySelector(".o_form_view .o_control_panel .o_pager_previous"));
        assert.strictEqual(count, 11);
        await click(target.querySelector(".o_x2m_control_panel .o_pager_next"));
        assert.strictEqual(count, 12, "one RPC should have been done");
        assert.containsN(
            target,
            '.o_kanban_record:not(".o_kanban_ghost")',
            2,
            "one2many kanban should contain 2 cards for record 1 at page 2"
        );
    });

    QUnit.skipWOWL("edition of one2many field with pager", async function (assert) {
        assert.expect(31);

        var ids = [];
        for (var i = 0; i < 45; i++) {
            var id = 10 + i;
            ids.push(id);
            serverData.models.partner.records.push({
                id: id,
                display_name: "relational record " + id,
            });
        }
        serverData.models.partner.records[0].p = ids;

        var saveCount = 0;
        var checkRead = false;
        var readIDs;
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <a t-if="!read_only_mode" type="delete" class="fa fa-times float-right delete_icon"/>
                                        <span><t t-esc="record.display_name.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            archs: {
                "partner,false,form": '<form><field name="display_name"/></form>',
            },
            mockRPC(route, args) {
                if (args.method === "read" && checkRead) {
                    readIDs = args.args[0];
                    checkRead = false;
                }
                if (args.method === "write") {
                    saveCount++;
                    var nbCommands = args.args[1].p.length;
                    var nbLinkCommands = _.filter(args.args[1].p, function (command) {
                        return command[0] === 4;
                    }).length;
                    switch (saveCount) {
                        case 1:
                            assert.strictEqual(
                                nbCommands,
                                46,
                                "should send 46 commands (one for each record)"
                            );
                            assert.strictEqual(
                                nbLinkCommands,
                                45,
                                "should send a LINK_TO command for each existing record"
                            );
                            assert.deepEqual(
                                args.args[1].p[45],
                                [
                                    0,
                                    args.args[1].p[45][1],
                                    {
                                        display_name: "new record",
                                    },
                                ],
                                "should sent a CREATE command for the new record"
                            );
                            break;
                        case 2:
                            assert.strictEqual(nbCommands, 46, "should send 46 commands");
                            assert.strictEqual(
                                nbLinkCommands,
                                45,
                                "should send a LINK_TO command for each existing record"
                            );
                            assert.deepEqual(
                                args.args[1].p[45],
                                [2, 10, false],
                                "should sent a DELETE command for the deleted record"
                            );
                            break;
                        case 3:
                            assert.strictEqual(nbCommands, 47, "should send 47 commands");
                            assert.strictEqual(
                                nbLinkCommands,
                                43,
                                "should send a LINK_TO command for each existing record"
                            );
                            assert.deepEqual(
                                args.args[1].p[43],
                                [0, args.args[1].p[43][1], { display_name: "new record page 1" }],
                                "should sent correct CREATE command"
                            );
                            assert.deepEqual(
                                args.args[1].p[44],
                                [0, args.args[1].p[44][1], { display_name: "new record page 2" }],
                                "should sent correct CREATE command"
                            );
                            assert.deepEqual(
                                args.args[1].p[45],
                                [2, 11, false],
                                "should sent correct DELETE command"
                            );
                            assert.deepEqual(
                                args.args[1].p[46],
                                [2, 52, false],
                                "should sent correct DELETE command"
                            );
                            break;
                    }
                }
                return this._super.apply(this, arguments);
            },
            resId: 1,
        });

        assert.strictEqual(
            form.$('.o_kanban_record:not(".o_kanban_ghost")').length,
            40,
            "there should be 40 records on page 1"
        );
        assert.strictEqual(
            form.$(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "1-40 / 45",
            "pager range should be correct"
        );

        // add a record on page one
        checkRead = true;
        await clickEdit(target);
        await click(form.$(".o-kanban-button-new"));
        await testUtils.fields.editInput($(".modal input"), "new record");
        await click($(".modal .modal-footer .btn-primary:first"));
        // checks
        assert.strictEqual(readIDs, undefined, "should not have read any record");
        assert.strictEqual(
            form.$("span:contains(new record)").length,
            0,
            "new record should be on page 2"
        );
        assert.strictEqual(
            form.$('.o_kanban_record:not(".o_kanban_ghost")').length,
            40,
            "there should be 40 records on page 1"
        );
        assert.strictEqual(
            form.$(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "1-40 / 46",
            "pager range should be correct"
        );
        assert.strictEqual(
            form.$(".o_kanban_record:first span:contains(new record)").length,
            0,
            "new record should not be on page 1"
        );
        // save
        await clickSave(target);

        // delete a record on page one
        checkRead = true;
        await clickEdit(target);
        assert.strictEqual(
            form.$(".o_kanban_record:first span:contains(relational record 10)").length,
            1,
            "first record should be the one with id 10 (next checks rely on that)"
        );
        await click(form.$(".delete_icon:first"));
        // checks
        assert.deepEqual(
            readIDs,
            [50],
            "should have read a record (to display 40 records on page 1)"
        );
        assert.strictEqual(
            form.$('.o_kanban_record:not(".o_kanban_ghost")').length,
            40,
            "there should be 40 records on page 1"
        );
        assert.strictEqual(
            form.$(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "1-40 / 45",
            "pager range should be correct"
        );
        // save
        await clickSave(target);

        // add and delete records in both pages
        await clickEdit(target);
        checkRead = true;
        readIDs = undefined;
        // add and delete a record in page 1
        await click(form.$(".o-kanban-button-new"));
        await testUtils.fields.editInput($(".modal input"), "new record page 1");
        await click($(".modal .modal-footer .btn-primary:first"));
        assert.strictEqual(
            form.$(".o_kanban_record:first span:contains(relational record 11)").length,
            1,
            "first record should be the one with id 11 (next checks rely on that)"
        );
        await click(form.$(".delete_icon:first"));
        assert.deepEqual(
            readIDs,
            [51],
            "should have read a record (to display 40 records on page 1)"
        );
        // add and delete a record in page 2
        await click(form.$(".o_x2m_control_panel .o_pager_next"));
        assert.strictEqual(
            form.$(".o_kanban_record:first span:contains(relational record 52)").length,
            1,
            "first record should be the one with id 52 (next checks rely on that)"
        );
        checkRead = true;
        readIDs = undefined;
        await click(form.$(".delete_icon:first"));
        await click(form.$(".o-kanban-button-new"));
        await testUtils.fields.editInput($(".modal input"), "new record page 2");
        await click($(".modal .modal-footer .btn-primary:first"));
        assert.strictEqual(readIDs, undefined, "should not have read any record");
        // checks
        assert.strictEqual(
            form.$('.o_kanban_record:not(".o_kanban_ghost")').length,
            5,
            "there should be 5 records on page 2"
        );
        assert.strictEqual(
            form.$(".o_x2m_control_panel .o_pager_counter").text().trim(),
            "41-45 / 45",
            "pager range should be correct"
        );
        assert.strictEqual(
            form.$(".o_kanban_record span:contains(new record page 1)").length,
            1,
            "new records should be on page 2"
        );
        assert.strictEqual(
            form.$(".o_kanban_record span:contains(new record page 2)").length,
            1,
            "new records should be on page 2"
        );
        // save
        await clickSave(target);
    });

    QUnit.skipWOWL(
        "edition of one2many field, with onchange and not inline sub view",
        async function (assert) {
            assert.expect(2);

            serverData.models.turtle.onchanges.turtle_int = function (obj) {
                obj.turtle_foo = String(obj.turtle_int);
            };
            serverData.models.partner.onchanges.turtles = function () {};

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="turtles"/></form>`,
                archs: {
                    "turtle,false,list": '<tree><field name="turtle_foo"/></tree>',
                    "turtle,false,form":
                        '<form><group><field name="turtle_foo"/><field name="turtle_int"/></group></form>',
                },
                mockRPC: function () {
                    return this._super.apply(this, arguments);
                },
                resId: 1,
            });
            await clickEdit(target);
            await addRow(target);
            await testUtils.fields.editInput($('input[name="turtle_int"]'), "5");
            await click($(".modal-footer button.btn-primary").first());
            assert.strictEqual(
                form.$("tbody tr:eq(1) td.o_data_cell").text(),
                "5",
                "should display 5 in the foo field"
            );
            await click(form.$("tbody tr:eq(1) td.o_data_cell"));

            await testUtils.fields.editInput($('input[name="turtle_int"]'), "3");
            await click($(".modal-footer button.btn-primary").first());
            assert.strictEqual(
                form.$("tbody tr:eq(1) td.o_data_cell").text(),
                "3",
                "should now display 3 in the foo field"
            );
        }
    );

    QUnit.test("sorting one2many fields", async function (assert) {
        serverData.models.partner.fields.foo.sortable = true;
        serverData.models.partner.records.push({ id: 23, foo: "abc" });
        serverData.models.partner.records.push({ id: 24, foo: "xyz" });
        serverData.models.partner.records.push({ id: 25, foo: "def" });
        serverData.models.partner.records[0].p = [23, 24, 25];

        let rpcCount = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC() {
                rpcCount++;
            },
        });

        rpcCount = 0;
        assert.strictEqual(
            [...target.querySelectorAll(".o_data_cell")].map((c) => c.innerText).join(" "),
            "abc xyz def"
        );

        await click(target.querySelector("table thead .o_column_sortable"));
        assert.strictEqual(rpcCount, 0, "in memory sort, no RPC should have been done");
        assert.strictEqual(
            [...target.querySelectorAll(".o_data_cell")].map((c) => c.innerText).join(" "),
            "abc def xyz"
        );

        await click(target.querySelector("table thead .o_column_sortable"));
        assert.strictEqual(
            [...target.querySelectorAll(".o_data_cell")].map((c) => c.innerText).join(" "),
            "xyz def abc"
        );
    });

    QUnit.test("one2many list field edition", async function (assert) {
        serverData.models.partner.records.push({
            id: 3,
            display_name: "relational record 1",
        });
        serverData.models.partner.records[1].p = [3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
        });

        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td").innerText,
            "relational record 1"
        );

        await clickEdit(target);
        await click(target.querySelector(".o_field_one2many tbody td"));
        assert.hasClass(
            target.querySelector(".o_field_one2many tbody .o_data_row"),
            "o_selected_row"
        );

        await editInput(target, ".o_field_one2many tbody td input", "new value");
        assert.hasClass(
            target.querySelector(".o_field_one2many tbody .o_data_row"),
            "o_selected_row"
        );
        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td input").value,
            "new value"
        );

        // leave o2m edition
        await click(target.querySelector(".o_form_view"));
        assert.doesNotHaveClass(
            target.querySelector(".o_field_one2many tbody .o_data_row"),
            "o_selected_row"
        );

        // discard changes
        await clickDiscard(target);
        assert.containsNone(target, ".modal");
        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td").innerText,
            "relational record 1"
        );

        // edit again and save
        await clickEdit(target);
        await click(target.querySelector(".o_field_one2many tbody td"));
        await editInput(target, ".o_field_one2many tbody td input", "new value");
        await click(target.querySelector(".o_form_view"));
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_one2many tbody td").innerText,
            "new value",
            "display name of first record in o2m list should be 'new value'"
        );
    });

    QUnit.test("one2many list: create action disabled", async function (assert) {
        assert.expect(2);
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree create="0">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.containsNone(target, ".o_field_x2many_list_row_add");

        await clickEdit(target);
        assert.containsNone(target, ".o_field_x2many_list_row_add");
    });

    QUnit.test("one2many list: conditional create/delete actions", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="p" options="{'create': [('bar', '=', True)], 'delete': [('bar', '=', True)]}">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await clickEdit(target);
        // bar is true -> create and delete action are available
        assert.containsOnce(target, ".o_field_x2many_list_row_add");
        assert.containsN(target, "td.o_list_record_remove button", 2);

        // set bar to false -> create and delete action are no longer available
        await click(target, '.o_field_widget[name="bar"] input');

        assert.containsNone(target, ".o_field_x2many_list_row_add");
        assert.containsNone(target, "td.o_list_record_remove button");
    });

    QUnit.skipWOWL("many2many list: unlink two records", async function (assert) {
        assert.expect(7);
        serverData.models.partner.records[0].p = [1, 2, 4];
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name"/>
                </form>
            `,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" widget="many2many">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    const commands = args.args[1].p;
                    assert.strictEqual(commands.length, 3, "should have generated three commands");
                    assert.ok(
                        commands[0][0] === 4 && commands[0][1] === 2,
                        "should have generated the command 4 (LINK_TO) with id 4"
                    );
                    assert.ok(
                        commands[1][0] === 4 && commands[1][1] === 4,
                        "should have generated the command 4 (LINK_TO) with id 4"
                    );
                    assert.ok(
                        commands[2][0] === 3 && commands[2][1] === 1,
                        "should have generated the command 3 (UNLINK) with id 1"
                    );
                }
            },
        });
        await clickEdit(target);
        assert.containsN(target, "td.o_list_record_remove button", 3);

        await click(target.querySelector("td.o_list_record_remove button"));
        assert.containsN(target, "td.o_list_record_remove button", 2);

        await click(target.querySelector("tr.o_data_row"));
        assert.containsNone(target, ".modal .modal-footer .o_btn_remove");

        await click(target.querySelector(".modal .btn-secondary"));
        await clickSave(target);
    });

    QUnit.test("one2many list: deleting one records", async function (assert) {
        assert.expect(3);
        serverData.models.partner.records[0].p = [1, 2, 4];
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name"/>
                </form>
            `,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    const commands = args.args[1].p;
                    assert.deepEqual(commands, [
                        [4, 2, false],
                        [4, 4, false],
                        [2, 1, false],
                    ]);
                }
            },
        });
        await clickEdit(target);
        assert.containsN(target, "td.o_list_record_remove button", 3);

        await click(target.querySelector("td.o_list_record_remove button"));
        assert.containsN(target, "td.o_list_record_remove button", 2);

        // save and check that the correct command has been generated
        await clickSave(target);

        // FIXME: it would be nice to test that the view is re-rendered correctly,
        // but as the relational data isn't re-fetched, the rendering is ok even
        // if the changes haven't been saved
    });

    QUnit.skipWOWL("one2many kanban: edition", async function (assert) {
        assert.expect(23);

        // wait for more kanban stuff

        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            // color will be in the kanban but not in the form
            // foo will be in the form but not in the kanban
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="color"/>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <a t-if="!read_only_mode" type="delete" class="fa fa-times float-right delete_icon"/>
                                        <span><t t-esc="record.display_name.value"/></span>
                                        <span><t t-esc="record.color.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="display_name"/>
                            <field name="foo"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    const commands = args.args[1].p;
                    assert.deepEqual(commands, []);
                    assert.strictEqual(commands[0][0], 0);
                    assert.strictEqual(commands[0][2].display_name, "new subrecord 3");
                    assert.strictEqual(commands[1][0], 2);
                }
            },
        });

        // assert.containsNone(target, ".delete_icon");
        assert.containsNone(target, ".o_field_one2many .o-kanban-button-new");

        await clickEdit(target);

        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.strictEqual(
            target.querySelector(".o_kanban_record span").innerText,
            "second record"
        );
        assert.strictEqual(target.querySelectorAll(".o_kanban_record span")[1].innerText, "Red");
        assert.containsOnce(target, ".delete_icon");
        assert.containsOnce(target, ".o_field_one2many .o-kanban-button-new");
        assert.hasClass(
            target.querySelector(".o_field_one2many .o-kanban-button-new"),
            "btn-secondary"
        );
        assert.strictEqual(
            target.querySelector(".o_field_one2many .o-kanban-button-new").innerText,
            "Add"
        );

        // // edit existing subrecord
        // await click(form.$(".oe_kanban_global_click"));

        // await testUtils.fields.editInput($(".modal .o_form_view input").first(), "new name");
        // await click($(".modal .modal-footer .btn-primary"));
        // assert.strictEqual(
        //     form.$(".o_kanban_record span:first").text(),
        //     "new name",
        //     "value of subrecord should have been updated"
        // );

        // // create a new subrecord
        // await click(form.$(".o-kanban-button-new"));
        // await testUtils.fields.editInput($(".modal .o_form_view input").first(), "new subrecord 1");
        // await clickFirst($(".modal .modal-footer .btn-primary"));
        // assert.strictEqual(
        //     form.$(".o_kanban_record:not(.o_kanban_ghost)").length,
        //     2,
        //     "should contain 2 records"
        // );
        // assert.strictEqual(
        //     form.$(".o_kanban_record:nth(1) span").text(),
        //     "new subrecord 1Red",
        //     'value of newly created subrecord should be "new subrecord 1"'
        // );

        // // create two new subrecords
        // await click(form.$(".o-kanban-button-new"));
        // await testUtils.fields.editInput($(".modal .o_form_view input").first(), "new subrecord 2");
        // await click($(".modal .modal-footer .btn-primary:nth(1)"));
        // await testUtils.fields.editInput($(".modal .o_form_view input").first(), "new subrecord 3");
        // await clickFirst($(".modal .modal-footer .btn-primary"));
        // assert.strictEqual(
        //     form.$(".o_kanban_record:not(.o_kanban_ghost)").length,
        //     4,
        //     "should contain 4 records"
        // );

        // // delete subrecords
        // await click(form.$(".oe_kanban_global_click").first());
        // assert.strictEqual(
        //     $(".modal .modal-footer .o_btn_remove").length,
        //     1,
        //     "There should be a modal having Remove Button"
        // );
        // await click($(".modal .modal-footer .o_btn_remove"));
        // assert.containsNone($(".o_modal"), "modal should have been closed");
        // assert.strictEqual(
        //     form.$(".o_kanban_record:not(.o_kanban_ghost)").length,
        //     3,
        //     "should contain 3 records"
        // );
        // await click(form.$(".o_kanban_view .delete_icon:first()"));
        // await click(form.$(".o_kanban_view .delete_icon:first()"));
        // assert.strictEqual(
        //     form.$(".o_kanban_record:not(.o_kanban_ghost)").length,
        //     1,
        //     "should contain 1 records"
        // );
        // assert.strictEqual(
        //     form.$(".o_kanban_record span:first").text(),
        //     "new subrecord 3",
        //     'the remaining subrecord should be "new subrecord 3"'
        // );

        // // save and check that the correct command has been generated
        // await clickSave(target);
    });

    QUnit.skipWOWL(
        "one2many kanban (editable): properly handle add-label node attribute",
        async function (assert) {
            assert.expect(1);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles" add-label="Add turtle" mode="kanban">
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

            await clickEdit(target);
            assert.strictEqual(
                form.$('.o_field_one2many[name="turtles"] .o-kanban-button-new').text().trim(),
                "Add turtle",
                "In O2M Kanban, Add button should have 'Add turtle' label"
            );
        }
    );

    QUnit.skipWOWL("one2many kanban: create action disabled", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records[0].p = [4];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban create="0">
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <a t-if="!read_only_mode" type="delete" class="fa fa-times float-right delete_icon"/>
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
            !form.$(".o-kanban-button-new").length,
            '"Add" button should not be available in readonly'
        );

        await clickEdit(target);

        assert.ok(
            !form.$(".o-kanban-button-new").length,
            '"Add" button should not be available in edit'
        );
        assert.ok(
            form.$(".o_kanban_view .delete_icon").length,
            "delete icon should be visible in edit"
        );
    });

    QUnit.skipWOWL("one2many kanban: conditional create/delete actions", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2, 4];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="p" options="{'create': [('bar', '=', True)], 'delete': [('bar', '=', True)]}">
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
                        <form>
                            <field name="display_name"/>
                            <field name="foo"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
            viewOptions: {
                mode: "edit",
            },
        });

        // bar is initially true -> create and delete actions are available
        assert.containsOnce(form, ".o-kanban-button-new", '"Add" button should be available');

        await click(form.$(".oe_kanban_global_click").first());

        assert.containsOnce(
            document.body,
            ".modal .modal-footer .o_btn_remove",
            "There should be a Remove Button inside modal"
        );

        await clickDiscard(target.querySelector(".modal"));

        // set bar false -> create and delete actions are no longer available
        await click(form.$('.o_field_widget[name="bar"] input').first());

        assert.containsNone(
            form,
            ".o-kanban-button-new",
            '"Add" button should not be available as bar is False'
        );

        await click(form.$(".oe_kanban_global_click").first());

        assert.containsNone(
            document.body,
            ".modal .modal-footer .o_btn_remove",
            "There should not be a Remove Button as bar field is False"
        );
    });

    QUnit.test("editable one2many list, pager is updated", async function (assert) {
        serverData.models.turtle.records.push({ id: 4, turtle_foo: "stephen hawking" });
        serverData.models.partner.records[0].turtles = [1, 2, 3, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add a record, add value to turtle_foo then click in form view to confirm it
        await clickEdit(target);
        await click(target, ".o_field_x2many_list_row_add a");

        await editInput(target, 'div[name="turtle_foo"] input', "nora");

        await click(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=turtles] .o_pager").innerText.trim(),
            "1-4 / 5"
        );
    });

    QUnit.test("one2many list (non editable): edition", async function (assert) {
        assert.expect(12);

        let nbWrite = 0;
        serverData.models.partner.records[0].p = [2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                            <field name="qux"/>
                        </tree>
                        <form string="Partners">
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>
            `,
            resId: 1,
            mockRPC: function (route, args) {
                if (args.method === "write") {
                    nbWrite++;
                    assert.deepEqual(args.args[1], {
                        p: [
                            [1, 2, { display_name: "new name" }],
                            [2, 4, false],
                        ],
                    });
                }
            },
        });

        assert.containsN(target, ".o_list_record_remove", 2);
        assert.containsOnce(target, ".o_field_x2many_list_row_add");

        await clickEdit(target);

        assert.containsN(target, "td.o_list_number", 2);
        assert.strictEqual(
            target.querySelector(".o_list_renderer tbody td").innerText,
            "second record"
        );
        assert.containsN(target, ".o_list_record_remove", 2);
        assert.containsOnce(target, ".o_field_x2many_list_row_add");

        // edit existing subrecord
        await click(target.querySelectorAll(".o_list_renderer tbody tr td")[1]); // ?

        await editInput(target, ".modal .o_form_editable input", "new name");

        await click(target, ".modal .modal-footer .btn-primary");
        assert.strictEqual(target.querySelector(".o_list_renderer tbody td").innerText, "new name");
        assert.strictEqual(nbWrite, 0, "should not have write anything in DB");

        // remove subrecords
        await click(target.querySelectorAll(".o_list_record_remove")[1]);
        assert.containsOnce(target, "td.o_list_number");
        assert.strictEqual(target.querySelector(".o_list_renderer tbody td").innerText, "new name");

        await clickSave(target); // save the record
        assert.strictEqual(nbWrite, 1, "should have write the changes in DB");
    });

    // WOWL won't do quick edit
    QUnit.skipWOWL("one2many list (editable): edition", async function (assert) {
        assert.expect(7);

        serverData.models.partner.records[0].p = [2, 4];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name"/>
                            <field name="qux"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_field_x2many_list_row_add");

        await click(target.querySelector(".o_list_renderer tbody td"));

        assert.containsOnce(target, ".o_form_view .o_form_editable"); // not sure about this
        assert.containsOnce(target, ".o_field_x2many_list_row_add");
        assert.containsNone(target, ".modal");
        // WOWL do we want this or another click?
        assert.hasClass(target.querySelector(".o_list_renderer tbody tr"), "o_selected_row");
        await editInput(target, '.o_list_renderer div[name="display_name"] input', "new name");

        const secondRow = target.querySelectorAll(".o_list_renderer tbody tr")[1];
        await click(secondRow.querySelector("td"));
        assert.doesNotHaveClass(target, ".o_list_renderer tbody tr", "o_selected_row");
        assert.strictEqual(target.querySelector(".o_list_renderer tbody td").innerText, "new name");

        // create new subrecords
        // TODO when 'Add an item' will be implemented
    });

    QUnit.test("one2many list (editable): edition, part 2", async function (assert) {
        assert.expect(9);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[1].p, [
                        [0, "virtual_2", { foo: "gemuse" }],
                        [0, "virtual_1", { foo: "kartoffel" }],
                    ]);
                }
            },
        });

        // edit mode, then click on Add an item and enter a value
        await clickEdit(target);
        await addRow(target);
        await editInput(target, ".o_selected_row > td input", "kartoffel");
        assert.strictEqual(target.querySelector("td .o_field_char input").value, "kartoffel");

        // click again on Add an item
        await addRow(target);
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");
        assert.strictEqual(target.querySelectorAll("td .o_field_char")[1].innerText, "kartoffel");
        assert.containsOnce(target, ".o_selected_row > td input");
        assert.containsN(target, "tr.o_data_row", 2);

        // enter another value and save
        await editInput(target, ".o_selected_row > td input", "gemuse");
        await clickSave(target);
        assert.containsN(target, "tr.o_data_row", 2);
        assert.strictEqual(target.querySelector("td .o_field_char").innerText, "gemuse");
        assert.strictEqual(target.querySelectorAll("td .o_field_char")[1].innerText, "kartoffel");
    });

    QUnit.test("one2many list (editable): edition, part 3", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        // edit mode, then click on Add an item, enter value in turtle_foo and Add an item again
        assert.containsOnce(target, "tr.o_data_row");
        await clickEdit(target);
        await addRow(target);
        await editInput(target, 'div[name="turtle_foo"] input', "nora");
        await addRow(target);
        assert.containsN(target, "tr.o_data_row", 3);

        // cancel the edition
        await clickDiscard(target);

        assert.containsNone(target, ".modal");
        assert.containsOnce(target, "tr.o_data_row");
    });

    QUnit.skipWOWL("one2many list (editable): edition, part 4", async function (assert) {
        assert.expect(3);
        let i = 0;
        serverData.models.turtle.onchanges = {
            turtle_trululu: function (obj) {
                if (i) {
                    obj.turtle_description = "Some Description";
                }
                i++;
            },
        };
        serverData["partner,false,"];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_trululu"/>
                                <field name="turtle_description"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 2,
        });

        // edit mode, then click on Add an item
        assert.containsNone(target, "tr.o_data_row");
        await clickEdit(target);
        await addRow(target);
        assert.strictEqual(target.querySelector(".o_data_row textarea").value, "");

        // add a value in the turtle_trululu field to trigger an onchange
        await testUtils.fields.many2one.clickOpenDropdown("turtle_trululu");
        await testUtils.fields.many2one.clickHighlightedItem("turtle_trululu");
        assert.strictEqual(target.querySelector(".o_data_row textarea").value, "Some Description");
    });

    QUnit.test("one2many list (editable): edition, part 5", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        // edit mode, then click on Add an item, enter value in turtle_foo and Add an item again
        assert.containsOnce(target, "tr.o_data_row");
        await clickEdit(target);
        await addRow(target);
        assert.containsN(target, "tr.o_data_row", 2);
        await removeRow(target, 1);
        assert.containsOnce(target, "tr.o_data_row");

        // cancel the edition
        await clickDiscard(target);
        assert.containsOnce(target, "tr.o_data_row");
    });

    QUnit.test("one2many list (editable): discarding required empty data", async function (assert) {
        serverData.models.turtle.fields.turtle_foo.required = true;
        delete serverData.models.turtle.fields.turtle_foo.default;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <group>
                            <field name="turtles">
                                <tree editable="top">
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </group>
                    </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
            },
        });

        // edit mode, then click on Add an item, then click elsewhere
        assert.containsNone(target, "tr.o_data_row");
        await clickEdit(target);
        await addRow(target);
        await click(target.querySelector("label.o_form_label"));
        assert.containsNone(target, "tr.o_data_row");

        // click on Add an item again, then click on save
        await addRow(target);
        await clickSave(target);
        assert.containsNone(target, "tr.o_data_row");

        assert.verifySteps(["read", "onchange", "onchange"]);
    });

    QUnit.test("editable one2many list, adding line when only one page", async function (assert) {
        assert.expect(5);

        serverData.models.partner.records[0].turtles = [1, 2, 3];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom" limit="3">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
            resId: 1,
        });

        // add a record, to reach the page size limit
        await clickEdit(target);
        await addRow(target);
        // the record currently being added should not count in the pager
        assert.containsNone(target, ".o_field_widget[name=turtles] .o_pager");

        // enter value in turtle_foo field and click outside to unselect the row
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "nora");
        await click(target);
        assert.containsNone(target, ".o_selected_row");
        assert.containsNone(target, ".o_field_widget[name=turtles] .o_pager");

        await clickSave(target);
        assert.containsOnce(target, ".o_field_widget[name=turtles] .o_pager");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=turtles] .o_pager").innerText,
            "1-3 / 4"
        );
    });

    QUnit.test("editable one2many list, adding line, then discarding", async function (assert) {
        assert.expect(3);

        serverData.models.turtle.records.push({ id: 4, turtle_foo: "stephen hawking" });
        serverData.models.partner.records[0].turtles = [1, 2, 3, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add a record, then discard
        await clickEdit(target);
        await addRow(target);

        await clickDiscard(target);
        assert.containsNone(target, ".modal");

        assert.isVisible(target.querySelector(".o_field_widget[name=turtles] .o_pager"));
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=turtles] .o_pager").innerText.trim(),
            "1-3 / 4"
        );
    });

    QUnit.test("editable one2many list, required field and pager", async function (assert) {
        assert.expect(1);

        serverData.models.turtle.records.push({ id: 4, turtle_foo: "stephen hawking" });
        serverData.models.turtle.fields.turtle_foo.required = true;
        serverData.models.partner.records[0].turtles = [1, 2, 3, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add a (empty) record
        await clickEdit(target);
        await addRow(target);

        // go on next page. The new record is not valid and should be discarded
        await click(target.querySelector(".o_field_widget[name=turtles] .o_pager_next"));
        assert.containsOnce(target, "tr.o_data_row");
    });

    QUnit.skipWOWL(
        "editable one2many list, required field, pager and confirm discard",
        async function (assert) {
            assert.expect(3);

            serverData.models.turtle.records.push({ id: 4, turtle_foo: "stephen hawking" });
            serverData.models.turtle.fields.turtle_foo.required = true;
            serverData.models.partner.records[0].turtles = [1, 2, 3, 4];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom" limit="3">
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            // add a record with a dirty state, but not valid
            await clickEdit(target);
            await addRow(target);
            await editInput(target, '.o_field_widget[name="turtle_int"] input', 4321);

            // go to next page. The new record is not valid, but dirty. we should
            // see a confirm dialog
            await click(target.querySelector(".o_field_widget[name=turtles] .o_pager_next"));

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=turtles] .o_pager").innerText,
                "1-4 / 5"
            );

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=turtles] .o_pager").innerText,
                "1-4 / 5"
            );
            assert.containsOnce(target, ".o_field_one2many input.o_field_invalid");
        }
    );

    QUnit.test("editable one2many list, adding, discarding, and pager", async function (assert) {
        serverData.models.partner.records[0].turtles = [1];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // add 4 records (to have more records than the limit)
        await clickEdit(target);
        await addRow(target);
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "nora");
        await addRow(target);
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "nora");
        await addRow(target);
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "nora");
        await addRow(target);

        assert.containsN(target, "tr.o_data_row", 5);
        assert.containsNone(target, ".o_field_widget[name=turtles] .o_pager");

        // discard
        await clickDiscard(target);
        assert.containsNone(target, ".modal");

        assert.containsOnce(target, "tr.o_data_row");
        assert.containsNone(target, ".o_field_widget[name=turtles] .o_pager");
    });

    QUnit.test("unselecting a line with missing required data", async function (assert) {
        assert.expect(6);

        serverData.models.turtle.fields.turtle_foo.required = true;
        delete serverData.models.turtle.fields.turtle_foo.default;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 2,
        });

        // edit mode, then click on Add an item, then click elsewhere
        assert.containsNone(target, "tr.o_data_row");
        await clickEdit(target);
        await addRow(target);
        assert.containsOnce(target, "tr.o_data_row");

        // adding a value in the non required field, so it is dirty, but with
        // a missing required field
        await editInput(target, '.o_field_widget[name="turtle_int"] input', "12345");

        // click elsewhere
        await click(target.querySelector("label.o_form_label"));
        assert.containsNone(document.body, ".modal");

        // the line should still be selected
        assert.containsOnce(target, "tr.o_data_row.o_selected_row");

        // click discard
        await clickDiscard(target);
        assert.containsNone(document.body, ".modal");
        assert.containsNone(target, "tr.o_data_row");
    });

    QUnit.skipWOWL("pressing enter in a o2m with a required empty field", async function (assert) {
        assert.expect(4);

        serverData.models.turtle.fields.turtle_foo.required = true;

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        // edit mode, then click on Add an item, then press enter
        await clickEdit(target);
        await addRow(target);
        await testUtils.fields.triggerKeydown(form.$('input[name="turtle_foo"]'), "enter");
        assert.hasClass(
            form.$('input[name="turtle_foo"]'),
            "o_field_invalid",
            "input should be marked invalid"
        );
        assert.verifySteps(["read", "onchange"]);
    });

    QUnit.test("editing a o2m, with required field and onchange", async function (assert) {
        assert.expect(11);

        serverData.models.turtle.fields.turtle_foo.required = true;
        delete serverData.models.turtle.fields.turtle_foo.default;
        serverData.models.turtle.onchanges = {
            turtle_foo: function (obj) {
                obj.turtle_int = obj.turtle_foo.length;
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
            },
        });

        // edit mode, then click on Add an item
        assert.containsNone(target, "tr.o_data_row");
        await clickEdit(target);
        await addRow(target);

        // input some text in required turtle_foo field
        await editInput(target, '.o_field_widget[name="turtle_foo"] input', "aubergine");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="turtle_int"] input').value,
            "9"
        );

        // save and check everything is fine
        await clickSave(target);

        assert.strictEqual(
            target.querySelector('.o_data_row td .o_field_widget[name="turtle_foo"] span')
                .innerText,
            "aubergine"
        );
        assert.strictEqual(
            target.querySelector('.o_data_row td .o_field_widget[name="turtle_int"] span')
                .innerText,
            "9"
        );

        assert.verifySteps(["read", "onchange", "onchange", "write", "read", "read"]);
    });

    QUnit.skipWOWL("editable o2m, pressing ESC discard current changes", async function (assert) {
        assert.expect(5);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        await clickEdit(target);
        await addRow(target);
        assert.containsOnce(form, "tr.o_data_row", "there should be one data row");

        await testUtils.fields.triggerKeydown(form.$('input[name="turtle_foo"]'), "escape");
        assert.containsNone(form, "tr.o_data_row", "data row should have been discarded");
        assert.verifySteps(["read", "onchange"]);
    });

    QUnit.skipWOWL(
        "editable o2m with required field, pressing ESC discard current changes",
        async function (assert) {
            assert.expect(5);

            serverData.models.turtle.fields.turtle_foo.required = true;

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 2,
                mockRPC(route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            await clickEdit(target);
            await addRow(target);
            assert.containsOnce(form, "tr.o_data_row", "there should be one data row");

            await testUtils.fields.triggerKeydown(form.$('input[name="turtle_foo"]'), "escape");
            assert.containsNone(form, "tr.o_data_row", "data row should have been discarded");
            assert.verifySteps(["read", "onchange"]);
        }
    );

    QUnit.skipWOWL("pressing escape in editable o2m list in dialog", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="p">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            archs: {
                "partner,false,form": `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </form>`,
            },
            viewOptions: {
                mode: "edit",
            },
        });

        await addRow(target);
        await click($(".modal .o_field_x2many_list_row_add a"));

        assert.strictEqual(
            $(".modal .o_data_row.o_selected_row").length,
            1,
            "there should be a row in edition in the dialog"
        );

        await testUtils.fields.triggerKeydown($(".modal .o_data_cell input"), "escape");

        assert.strictEqual($(".modal").length, 1, "dialog should still be open");
        assert.strictEqual($(".modal .o_data_row").length, 0, "the row should have been removed");
    });

    QUnit.test(
        "editable o2m with onchange and required field: delete an invalid line",
        async function (assert) {
            assert.expect(5);

            serverData.models.partner.onchanges = {
                turtles: function () {},
            };
            serverData.models.partner.records[0].turtles = [1];
            serverData.models.turtle.records[0].product_id = 37;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="product_id"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            await clickEdit(target);
            await click(target.querySelector(".o_data_cell"));
            await editInput(target, ".o_field_widget[name=product_id] input", "");
            assert.verifySteps(["read", "read"], "no onchange should be done as line is invalid");
            await click(target.querySelector(".o_list_record_remove"));
            assert.verifySteps(["onchange"], "onchange should have been done");
        }
    );

    QUnit.skipWOWL("onchange in a one2many", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records.push({
            id: 3,
            foo: "relational record 1",
        });
        serverData.models.partner.records[1].p = [3];
        serverData.models.partner.onchanges = { p: true };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        value: {
                            p: [
                                [5], // delete all
                                [0, 0, { foo: "from onchange" }], // create new
                            ],
                        },
                    });
                }
                return this._super(route, args);
            },
        });

        await clickEdit(target);
        await click(form.$(".o_field_one2many tbody td").first());
        await testUtils.fields.editInput(
            form.$(".o_field_one2many tbody td").first().find("input"),
            "new value"
        );
        await clickSave(target);

        assert.strictEqual(
            form.$(".o_field_one2many tbody td").first().text(),
            "from onchange",
            "display name of first record in o2m list should be 'new value'"
        );
    });

    QUnit.test("one2many, default_get and onchange (basic)", async function (assert) {
        serverData.models.partner.fields.p.default = [
            [6, 0, []], // replace with zero ids
        ];
        serverData.models.partner.onchanges = { p: true };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return {
                        value: {
                            p: [
                                [5], // delete all
                                [0, 0, { foo: "from onchange" }], // create new
                            ],
                        },
                    };
                }
            },
        });

        assert.strictEqual(target.querySelector("td").innerText, "from onchange");
    });

    QUnit.skipWOWL("one2many and default_get (with date)", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.p.default = [[0, false, { date: "2017-10-08", p: [] }]];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="date"/>
                        </tree>
                    </field>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_data_cell").innerText,
            "10/08/2017",
            "should correctly display the date"
        );
    });

    QUnit.test("one2many and onchange (with integer)", async function (assert) {
        serverData.models.turtle.onchanges = {
            turtle_int: function () {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_int"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        await clickEdit(target);
        const td = target.querySelector("td");
        assert.strictEqual(td.innerText, "9");
        await click(td);
        await editInput(target, 'td [name="turtle_int"] input', "3");
        assert.verifySteps(["read", "read", "onchange"]);
    });

    QUnit.test("one2many and onchange (with date)", async function (assert) {
        serverData.models.partner.onchanges = {
            date: function () {},
        };
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="date"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        await clickEdit(target);
        const td = target.querySelector("td");
        assert.strictEqual(td.innerText, "01/25/2017");

        await click(td);
        await click(target.querySelector(".o_datepicker_input"));
        await nextTick();
        await click(document.body.querySelector(".bootstrap-datetimepicker-widget .picker-switch"));
        await click(
            document.body.querySelectorAll(".bootstrap-datetimepicker-widget .picker-switch")[1]
        );
        await click(
            [...document.body.querySelectorAll(".bootstrap-datetimepicker-widget .year")].filter(
                (el) => el.innerText === "2017"
            )[0]
        );
        await click(document.body.querySelectorAll(".bootstrap-datetimepicker-widget .month")[1]);
        await click(document.body.querySelectorAll(".bootstrap-datetimepicker-widget .day")[22]);
        await clickSave(target);

        assert.verifySteps(["read", "read", "onchange", "write", "read", "read"]);
    });

    QUnit.test("one2many and onchange (with command DELETE_ALL)", async function (assert) {
        assert.expect(5);

        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.p = [[5]];
            },
            p: function () {}, // dummy onchange on the o2m to execute _isX2ManyValid()
        };
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC: function (method, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[1].p, [
                        [0, args.args[1].p[0][1], { display_name: "z" }],
                        [2, 2, false],
                    ]);
                }
            },
            resId: 1,
        });
        await clickEdit(target);
        assert.containsOnce(target, ".o_data_row");

        // empty o2m by triggering the onchange
        await editInput(target, ".o_field_widget[name=foo] input", "trigger onchange");
        assert.containsNone(target, ".o_data_row", "rows of the o2m should have been deleted");

        // add two new subrecords
        await addRow(target);
        await editInput(target, ".o_field_widget[name=display_name] input", "x");
        await addRow(target);
        await editInput(target, ".o_field_widget[name=display_name] input", "y");
        assert.containsN(target, ".o_data_row", 2);

        // empty o2m by triggering the onchange
        await editInput(target, ".o_field_widget[name=foo] input", "trigger onchange again");
        assert.containsNone(target, ".o_data_row", "rows of the o2m should have been deleted");

        await addRow(target);
        await editInput(target, ".o_field_widget[name=display_name] input", "z");

        await clickSave(target);
    });

    QUnit.skipWOWL("one2many and onchange only write modified field", async function (assert) {
        assert.expect(2);

        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [
                    [5], // delete all
                    [
                        1,
                        3,
                        {
                            // the server returns all fields
                            display_name: "coucou",
                            product_id: [37, "xphone"],
                            turtle_bar: false,
                            turtle_foo: "has changed",
                            turtle_int: 42,
                            turtle_qux: 9.8,
                            partner_ids: [],
                            turtle_ref: "product,37",
                        },
                    ],
                ];
            },
        };

        serverData.models.partner.records[0].turtles = [3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                    <tree editable="bottom">
                        <field name="display_name"/>
                        <field name="product_id"/>
                        <field name="turtle_bar"/>
                        <field name="turtle_foo"/>
                        <field name="turtle_int"/>
                        <field name="turtle_qux"/>
                        <field name="turtle_ref"/>
                    </tree>
                    </field>
                </form>`,
            mockRPC: function (method, args) {
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args[1].turtles,
                        [
                            [
                                1,
                                3,
                                {
                                    display_name: "coucou",
                                    turtle_foo: "has changed",
                                    turtle_int: 42,
                                },
                            ],
                        ],
                        "correct commands should be sent (only send changed values)"
                    );
                }
            },
            resId: 1,
        });
        await clickEdit(target);
        assert.containsOnce(target, ".o_data_row");
        await click(target.querySelector(".o_field_one2many td"));
        await editInput(target, ".o_field_widget[name=display_name] input", "blurp");

        await clickSave(target);
    });

    QUnit.skipWOWL("one2many with CREATE onchanges correctly refreshed", async function (assert) {
        assert.expect(5);

        var delta = 0;
        testUtils.mock.patch(AbstractField, {
            init: function () {
                delta++;
                this._super.apply(this, arguments);
            },
            destroy: function () {
                delta--;
                this._super.apply(this, arguments);
            },
        });

        var deactiveOnchange = true;

        serverData.models.partner.records[0].turtles = [];
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                if (deactiveOnchange) {
                    return;
                }
                // the onchange will either:
                //  - create a second line if there is only one line
                //  - edit the second line if there are two lines
                if (obj.turtles.length === 1) {
                    obj.turtles = [
                        [5], // delete all
                        [
                            0,
                            obj.turtles[0][1],
                            {
                                display_name: "first",
                                turtle_int: obj.turtles[0][2].turtle_int,
                            },
                        ],
                        [
                            0,
                            0,
                            {
                                display_name: "second",
                                turtle_int: -obj.turtles[0][2].turtle_int,
                            },
                        ],
                    ];
                } else if (obj.turtles.length === 2) {
                    obj.turtles = [
                        [5], // delete all
                        [
                            0,
                            obj.turtles[0][1],
                            {
                                display_name: "first",
                                turtle_int: obj.turtles[0][2].turtle_int,
                            },
                        ],
                        [
                            0,
                            obj.turtles[1][1],
                            {
                                display_name: "second",
                                turtle_int: -obj.turtles[0][2].turtle_int,
                            },
                        ],
                    ];
                }
            },
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="display_name" widget="char"/>
                            <field name="turtle_int"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            viewOptions: {
                mode: "edit",
            },
        });

        assert.containsNone(form, ".o_data_row", "o2m shouldn't contain any row");

        await addRow(target);
        // trigger the first onchange
        deactiveOnchange = false;
        await testUtils.fields.editInput(form.$('input[name="turtle_int"]'), "10");
        // put the list back in non edit mode
        await click(form.$('input[name="foo"]'));
        assert.strictEqual(
            form.$(".o_data_row").text(),
            "first10second-10",
            "should correctly refresh the records"
        );

        // trigger the second onchange
        await click(form.$(".o_field_x2many_list tbody tr:first td:first"));
        await testUtils.fields.editInput(form.$('input[name="turtle_int"]'), "20");

        await click(form.$('input[name="foo"]'));
        assert.strictEqual(
            form.$(".o_data_row").text(),
            "first20second-20",
            "should correctly refresh the records"
        );

        assert.containsN(
            form,
            ".o_field_widget",
            delta,
            "all (non visible) field widgets should have been destroyed"
        );

        await clickSave(target);

        assert.strictEqual(
            form.$(".o_data_row").text(),
            "first20second-20",
            "should correctly refresh the records after save"
        );

        testUtils.mock.unpatch(AbstractField);
    });

    QUnit.skipWOWL(
        "editable one2many with sub widgets are rendered in readonly",
        async function (assert) {
            assert.expect(2);

            var editableWidgets = 0;
            testUtils.mock.patch(AbstractField, {
                init: function () {
                    this._super.apply(this, arguments);
                    if (this.mode === "edit") {
                        editableWidgets++;
                    }
                },
            });

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo" widget="char" attrs="{'readonly': [('turtle_int', '==', 11111)]}"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.strictEqual(editableWidgets, 1, "o2m is only widget in edit mode");
            await click(form.$("tbody td.o_field_x2many_list_row_add a"));

            assert.strictEqual(editableWidgets, 3, "3 widgets currently in edit mode");

            testUtils.mock.unpatch(AbstractField);
        }
    );

    QUnit.skipWOWL("one2many editable list with onchange keeps the order", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].p = [1, 2, 4];
        serverData.models.partner.onchanges = {
            p: function () {},
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            viewOptions: {
                mode: "edit",
            },
        });

        assert.strictEqual(
            form.$(".o_data_cell").text(),
            "first recordsecond recordaaa",
            "records should be display in the correct order"
        );

        await click(form.$(".o_data_row:first .o_data_cell"));
        await testUtils.fields.editInput(
            form.$(".o_selected_row .o_field_widget[name=display_name]"),
            "new"
        );
        await click(form.$el);

        assert.strictEqual(
            form.$(".o_data_cell").text(),
            "newsecond recordaaa",
            "records should be display in the correct order"
        );
    });

    QUnit.skipWOWL(
        "one2many list (editable): readonly domain is evaluated",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].p = [2, 4];
            serverData.models.partner.records[1].product_id = false;
            serverData.models.partner.records[2].product_id = 37;

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="top">
                                <field name="display_name" attrs='{"readonly": [["product_id", "=", false]]}'/>
                                <field name="product_id"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            await clickEdit(target);

            assert.hasClass(
                form.$(".o_list_view tbody tr:eq(0) td:first"),
                "o_readonly_modifier",
                "first record should have display_name in readonly mode"
            );

            assert.doesNotHaveClass(
                form.$(".o_list_view tbody tr:eq(1) td:first"),
                "o_readonly_modifier",
                "second record should not have display_name in readonly mode"
            );
        }
    );

    QUnit.skipWOWL("pager of one2many field in new record", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records[0].p = [];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
        });

        assert.containsNone(form, ".o_x2m_control_panel .o_pager", "o2m pager should be hidden");

        // click to create a subrecord
        await click(form.$("tbody td.o_field_x2many_list_row_add a"));
        assert.containsOnce(form, "tr.o_data_row");

        assert.containsNone(form, ".o_x2m_control_panel .o_pager", "o2m pager should be hidden");
    });

    QUnit.skipWOWL("one2many list with a many2one", async function (assert) {
        assert.expect(5);

        let checkOnchange = false;
        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].product_id = 37;
        serverData.models.partner.onchanges.p = function (obj) {
            obj.p = [
                [5], // delete all
                [1, 2, { product_id: [37, "xphone"] }], // update existing record
                [0, 0, { product_id: [41, "xpad"] }],
            ];
            //
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="product_id"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            archs: {
                "partner,false,form": '<form><field name="product_id"/></form>',
            },
            mockRPC(route, args) {
                if (args.method === "onchange" && checkOnchange) {
                    assert.deepEqual(
                        args.args[1].p,
                        [
                            [4, 2, false],
                            [0, args.args[1].p[1][1], { product_id: 41 }],
                        ],
                        "should trigger onchange with correct parameters"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(
            form.$("tbody td:contains(xphone)").length,
            1,
            "should have properly fetched the many2one nameget"
        );
        assert.strictEqual(
            form.$("tbody td:contains(xpad)").length,
            0,
            "should not display 'xpad' anywhere"
        );

        await clickEdit(target);

        await click(form.$("tbody td.o_field_x2many_list_row_add a"));

        checkOnchange = true;
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        testUtils.fields.many2one.clickItem("product_id", "xpad");

        await click($(".modal .modal-footer button:eq(0)"));

        assert.strictEqual(
            form.$("tbody td:contains(xpad)").length,
            1,
            "should display 'xpad' on a td"
        );
        assert.strictEqual(
            form.$("tbody td:contains(xphone)").length,
            1,
            "should still display xphone"
        );
    });

    QUnit.skipWOWL("one2many list with inline form view", async function (assert) {
        assert.expect(5);

        serverData.models.partner.records[0].p = [];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            // don't remove foo field in sub tree view, it is useful to make sure
            // the foo fieldwidget does not crash because the foo field is not in the form view
            arch: `
                <form>
                    <field name="p">
                        <form>
                            <field name="product_id"/>
                            <field name="int_field"/>
                        </form>
                        <tree>
                            <field name="product_id"/>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[1].p, [
                        [
                            0,
                            args.args[1].p[0][1],
                            {
                                foo: "My little Foo Value",
                                int_field: 123,
                                product_id: 41,
                            },
                        ],
                    ]);
                }
                return this._super(route, args);
            },
        });

        await clickEdit(target);

        await click(form.$("tbody td.o_field_x2many_list_row_add a"));

        // write in the many2one field, value = 37 (xphone)
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickHighlightedItem("product_id");

        // write in the integer field
        await testUtils.fields.editInput($(".modal .modal-body input.o_field_widget"), "123");

        // save and close
        await click($(".modal .modal-footer button:eq(0)"));

        assert.strictEqual(
            form.$("tbody td:contains(xphone)").length,
            1,
            "should display 'xphone' in a td"
        );

        // reopen the record in form view
        await click(form.$("tbody td:contains(xphone)"));

        assert.strictEqual(
            $(".modal .modal-body input").val(),
            "xphone",
            "should display 'xphone' in an input"
        );

        await testUtils.fields.editInput($(".modal .modal-body input.o_field_widget"), "456");

        // discard
        await click($(".modal .modal-footer span:contains(Discard)"));

        // reopen the record in form view
        await click(form.$("tbody td:contains(xphone)"));

        assert.strictEqual(
            $(".modal .modal-body input.o_field_widget").val(),
            "123",
            "should display 123 (previous change has been discarded)"
        );

        // write in the many2one field, value = 41 (xpad)
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        testUtils.fields.many2one.clickItem("product_id", "xpad");

        // save and close
        await click($(".modal .modal-footer button:eq(0)"));

        assert.strictEqual(
            form.$("tbody td:contains(xpad)").length,
            1,
            "should display 'xpad' in a td"
        );

        // save the record
        await clickSave(target);
    });

    QUnit.skipWOWL(
        "one2many list with inline form view with context with parent key",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[0].product_id = 41;
            serverData.models.partner.records[1].product_id = 37;

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="product_id"/>
                        <field name="p">
                            <form>
                                <field name="product_id" context="{'partner_foo':parent.foo, 'lalala': parent.product_id}"/>
                            </form>
                            <tree>
                                <field name="product_id"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        assert.strictEqual(
                            args.kwargs.context.partner_foo,
                            "yop",
                            "should have correctly evaluated parent foo field"
                        );
                        assert.strictEqual(
                            args.kwargs.context.lalala,
                            41,
                            "should have correctly evaluated parent product_id field"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await clickEdit(target);
            // open a modal
            await click(form.$("tr.o_data_row:eq(0) td:contains(xphone)"));

            // write in the many2one field
            await click($(".modal .o_field_many2one input"));
        }
    );

    QUnit.skipWOWL(
        "value of invisible x2many fields is correctly evaluated in context",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].timmy = [12];
            serverData.models.partner.records[0].p = [2, 3];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="product_id" context="{'p': p, 'timmy': timmy}"/>
                        <field name="p" invisible="1"/>
                        <field name="timmy" invisible="1"/>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        assert.deepEqual(
                            args.kwargs.context,
                            {
                                p: [
                                    [4, 2, false],
                                    [4, 3, false],
                                ],
                                timmy: [[6, false, [12]]],
                            },
                            "values of x2manys should have been correctly evaluated in context"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await clickEdit(target);
            await click(form.$(".o_field_widget[name=product_id] input"));
        }
    );

    QUnit.skipWOWL(
        "one2many list, editable, with many2one and with context with parent key",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[1].product_id = 37;

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="product_id" context="{'partner_foo':parent.foo}"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        assert.strictEqual(
                            args.kwargs.context.partner_foo,
                            "yop",
                            "should have correctly evaluated parent foo field"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await clickEdit(target);

            await click(form.$("tr.o_data_row:eq(0) td:contains(xphone)"));

            // trigger a name search
            await click(form.$("table td input"));
        }
    );

    QUnit.skipWOWL("one2many list, editable, with a date in the context", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].product_id = 37;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="date"/>
                        <field name="p" context="{'date':date}">
                            <tree editable="top">
                                <field name="date"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.strictEqual(
                        args.kwargs.context.date,
                        "2017-01-25",
                        "should have properly evaluated date key in context"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        await clickEdit(target);
        await addRow(target);
    });

    QUnit.skipWOWL("one2many field with context", async function (assert) {
        assert.expect(2);

        var counter = 0;

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles" context="{'turtles':turtles}">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    var expected =
                        counter === 0
                            ? [[4, 2, false]]
                            : [
                                  [4, 2, false],
                                  [0, args.kwargs.context.turtles[1][1], { turtle_foo: "hammer" }],
                              ];
                    assert.deepEqual(
                        args.kwargs.context.turtles,
                        expected,
                        "should have properly evaluated turtles key in context"
                    );
                    counter++;
                }
                return this._super.apply(this, arguments);
            },
        });

        await clickEdit(target);
        await addRow(target);
        await testUtils.fields.editInput(form.$('input[name="turtle_foo"]'), "hammer");
        await addRow(target);
    });

    QUnit.test("one2many list edition, some basic functionality", async function (assert) {
        assert.expect(3);

        serverData.models.partner.fields.foo.default = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        await clickEdit(target);

        await click(target, "tbody td.o_field_x2many_list_row_add a");

        assert.containsOnce(
            target,
            "td .o_field_widget input",
            "should have created a row in edit mode"
        );

        await editInput(target, "td .o_field_widget input", "a");

        assert.containsOnce(
            target,
            "td .o_field_widget input",
            "should not have unselected the row after edition"
        );

        await editInput(target, "td .o_field_widget input", "abc");
        await clickSave(target);

        assert.strictEqual(
            [...target.querySelectorAll("td")].filter((el) => el.innerText === "abc").length,
            1,
            "should have a row with the correct value"
        );
    });

    QUnit.test(
        "one2many list, the context is properly evaluated and sent",
        async function (assert) {
            assert.expect(2);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="p" context="{'hello': 'world', 'abc': int_field}">
                            <tree editable="top">
                                <field name="foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        var context = args.kwargs.context;
                        assert.strictEqual(context.hello, "world");
                        assert.strictEqual(context.abc, 10);
                    }
                },
            });

            await clickEdit(target);
            await click(target, "tbody td.o_field_x2many_list_row_add a");
        }
    );

    QUnit.skipWOWL("one2many with many2many widget: create", async function (assert) {
        assert.expect(10);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles" widget="many2many">
                        <tree>
                            <field name="turtle_foo"/>
                            <field name="turtle_qux"/>
                            <field name="turtle_int"/>
                            <field name="product_id"/>
                        </tree>
                        <form>
                            <group>
                                <field name="turtle_foo"/>
                                <field name="turtle_bar"/>
                                <field name="turtle_int"/>
                                <field name="product_id"/>
                            </group>
                        </form>
                    </field>
                </form>`,
            archs: {
                "turtle,false,list": `
                    <tree>
                        <field name="display_name"/>
                        <field name="turtle_foo"/>
                        <field name="turtle_bar"/>
                        <field name="product_id"/>
                    </tree>`,
                "turtle,false,search": `
                    <search>
                        <field name="turtle_foo"/>
                        <field name="turtle_bar"/>
                        <field name="product_id"/>
                    </search>`,
            },
            session: {},
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/turtle/create") {
                    assert.ok(args.args, "should write on the turtle record");
                }
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(args.args[0][0], 1, "should write on the partner record 1");
                    assert.strictEqual(
                        args.args[1].turtles[0][0],
                        6,
                        "should send only a 'replace with' command"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        await clickEdit(target);
        await addRow(target);

        assert.strictEqual(
            $(".modal .o_data_row").length,
            2,
            "should have 2 records in the select view (the last one is not displayed because it is already selected)"
        );

        await click($(".modal .o_data_row:first .o_list_record_selector input"));
        await click($(".modal .o_select_button"));
        await click($(".o_form_button_save"));
        await clickEdit(target);
        await addRow(target);

        assert.strictEqual(
            $(".modal .o_data_row").length,
            1,
            "should have 1 record in the select view"
        );

        await click($(".modal-footer button:eq(1)"));
        await testUtils.fields.editInput(
            $('.modal input.o_field_widget[name="turtle_foo"]'),
            "tototo"
        );
        await testUtils.fields.editInput($('.modal input.o_field_widget[name="turtle_int"]'), 50);
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickHighlightedItem("product_id");

        await click($(".modal-footer button:contains(&):first"));

        assert.strictEqual($(".modal").length, 0, "should close the modals");

        assert.containsN(form, ".o_data_row", 3, "should have 3 records in one2many list");
        assert.strictEqual(
            form.$(".o_data_row").text(),
            "blip1.59yop1.50tototo1.550xphone",
            "should display the record values in one2many list"
        );

        await click($(".o_form_button_save"));
    });

    QUnit.skipWOWL("one2many with many2many widget: edition", async function (assert) {
        assert.expect(7);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles" widget="many2many">
                        <tree>
                            <field name="turtle_foo"/>
                            <field name="turtle_qux"/>
                            <field name="turtle_int"/>
                            <field name="product_id"/>
                        </tree>
                        <form>
                            <group>
                                <field name="turtle_foo"/>
                                <field name="turtle_bar"/>
                                <field name="turtle_int"/>
                                <field name="turtle_trululu"/>
                                <field name="product_id"/>
                            </group>
                        </form>
                    </field>
                </form>`,
            archs: {
                "turtle,false,list": `
                    <tree>
                        <field name="display_name"/>
                        <field name="turtle_foo"/>
                        <field name="turtle_bar"/>
                        <field name="product_id"/>
                    </tree>`,
                "turtle,false,search": `
                    <search>
                        <field name="turtle_foo"/>
                        <field name="turtle_bar"/>
                        <field name="product_id"/>
                    </search>`,
            },
            session: {},
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/turtle/write") {
                    assert.strictEqual(args.args[0].length, 1, "should write on the turtle record");
                    assert.deepEqual(
                        args.args[1],
                        { product_id: 37 },
                        "should write only the product_id on the turtle record"
                    );
                }
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(args.args[0][0], 1, "should write on the partner record 1");
                    assert.strictEqual(
                        args.args[1].turtles[0][0],
                        6,
                        "should send only a 'replace with' command"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        await click(form.$(".o_data_row:first"));
        await testUtils.nextTick(); // wait for quick edit
        assert.strictEqual(
            $(".modal .modal-title").first().text().trim(),
            "Open: one2many turtle field",
            "modal should use the python field string as title"
        );
        await clickDiscard(target.querySelector(".modal"));

        // edit the first one2many record
        await click(form.$(".o_data_row:first"));
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickHighlightedItem("product_id");
        await click($(".modal-footer button:first"));

        await click($(".o_form_button_save"));

        // add a one2many record
        await clickEdit(target);
        await addRow(target);
        await click($(".modal .o_data_row:first .o_list_record_selector input"));
        await click($(".modal .o_select_button"));

        // edit the second one2many record
        await click(form.$(".o_data_row:eq(1)"));
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickHighlightedItem("product_id");
        await click($(".modal-footer button:first"));

        await click($(".o_form_button_save"));
    });

    QUnit.test("new record, the context is properly evaluated and sent", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.int_field.default = 17;
        let n = 0;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="p" context="{'hello': 'world', 'abc': int_field}">
                            <tree editable="top">
                                <field name="foo"/>
                            </tree>
                        </field>
                    </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    n++;
                    if (n === 2) {
                        var context = args.kwargs.context;
                        assert.strictEqual(context.hello, "world");
                        assert.strictEqual(context.abc, 17);
                    }
                }
            },
        });

        await click(target, "tbody td.o_field_x2many_list_row_add a");
    });

    QUnit.skipWOWL("parent data is properly sent on an onchange rpc", async function (assert) {
        assert.expect(1);

        serverData.models.partner.onchanges = { bar: function () {} };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="bar"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    const fieldValues = args.args[1];
                    assert.strictEqual(
                        fieldValues.trululu.foo,
                        "yop",
                        "should have properly sent the parent foo value"
                    );
                }
            },
        });

        await clickEdit(target);
        await click(target, "tbody td.o_field_x2many_list_row_add a");
        // use of owlCompatibilityExtraNextTick because we have an x2many field with a boolean field
        // (written in owl), so when we add a line, we sequentially render the list itself
        // (including the boolean field), so we have to wait for the next animation frame, and
        // then we render the control panel (also in owl), so we have to wait again for the
        // next animation frame
        await testUtils.owlCompatibilityExtraNextTick();
    });

    QUnit.skipWOWL(
        "parent data is properly sent on an onchange rpc (existing x2many record)",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.onchanges = {
                display_name: function () {},
            };
            serverData.models.partner.records[0].p = [1];
            serverData.models.partner.records[0].turtles = [2];
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name"/>
                            <field name="turtles" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        const fieldValues = args.args[1];
                        assert.strictEqual(fieldValues.trululu.foo, "yop");
                        // we only send fields that changed inside the reverse many2one
                        assert.deepEqual(fieldValues.trululu.p, [
                            [1, 1, { display_name: "new val" }],
                        ]);
                    }
                    return this._super(...arguments);
                },
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.containsOnce(form, ".o_data_row");

            await click(form.$(".o_data_row .o_data_cell:first"));

            assert.containsOnce(form, ".o_data_row.o_selected_row");
            await testUtils.fields.editInput(
                form.$(".o_selected_row .o_field_widget[name=display_name]"),
                "new val"
            );
        }
    );

    QUnit.skipWOWL(
        "parent data is properly sent on an onchange rpc, new record",
        async function (assert) {
            assert.expect(4);

            serverData.models.turtle.onchanges = { turtle_bar: function () {} };
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_bar"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "onchange" && args.model === "turtle") {
                        var fieldValues = args.args[1];
                        assert.strictEqual(
                            fieldValues.turtle_trululu.foo,
                            "My little Foo Value",
                            "should have properly sent the parent foo value"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });
            await click(form.$("tbody td.o_field_x2many_list_row_add a"));
            // use of owlCompatibilityExtraNextTick because we have an x2many field with a boolean field
            // (written in owl), so when we add a line, we sequentially render the list itself
            // (including the boolean field), so we have to wait for the next animation frame, and
            // then we render the control panel (also in owl), so we have to wait again for the
            // next animation frame
            await testUtils.owlCompatibilityExtraNextTick();
            assert.verifySteps(["onchange", "onchange"]);
        }
    );

    QUnit.skipWOWL("id in one2many obtained in onchange is properly set", async function (assert) {
        assert.expect(1);

        serverData.models.partner.onchanges.turtles = function (obj) {
            obj.turtles = [[5], [1, 3, { turtle_foo: "kawa" }]];
        };
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="id"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
        });

        assert.strictEqual(
            form.$("tr.o_data_row").text(),
            "3kawa",
            "should have properly displayed id and foo field"
        );
    });

    QUnit.skipWOWL("id field in one2many in a new record", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="id" invisible="1"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "create") {
                    var virtualID = args.args[0].turtles[0][1];
                    assert.deepEqual(
                        args.args[0].turtles,
                        [[0, virtualID, { turtle_foo: "cat" }]],
                        "should send proper commands"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });
        await click(form.$("td.o_field_x2many_list_row_add a"));
        await testUtils.fields.editInput(form.$('td input[name="turtle_foo"]'), "cat");
        await clickSave(target);
    });

    QUnit.skipWOWL("sub form view with a required field", async function (assert) {
        assert.expect(2);
        serverData.models.partner.fields.foo.required = true;
        serverData.models.partner.fields.foo.default = null;

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <form>
                            <group><field name="foo"/></group>
                        </form>
                        <tree>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await clickEdit(target);
        await click(form.$("tbody td.o_field_x2many_list_row_add a"));
        await click($(".modal-footer button.btn-primary").first());

        assert.strictEqual($(".modal").length, 1, "should still have an open modal");
        assert.strictEqual(
            $(".modal tbody label.o_field_invalid").length,
            1,
            "should have displayed invalid fields"
        );
    });

    QUnit.skipWOWL("one2many list with action button", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <button name="method_name" type="object" icon="fa-plus"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            intercepts: {
                execute_action: function (event) {
                    assert.deepEqual(event.data.env.currentID, 2, "should call with correct id");
                    assert.strictEqual(
                        event.data.env.model,
                        "partner",
                        "should call with correct model"
                    );
                    assert.strictEqual(
                        event.data.action_data.name,
                        "method_name",
                        "should call correct method"
                    );
                    assert.strictEqual(
                        event.data.action_data.type,
                        "object",
                        "should have correct type"
                    );
                },
            },
        });

        await click(form.$(".o_list_button button"));
    });

    QUnit.skipWOWL("one2many kanban with action button", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <kanban>
                            <field name="foo"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div>
                                        <span><t t-esc="record.foo.value"/></span>
                                        <button name="method_name" type="object" class="fa fa-plus"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
            intercepts: {
                execute_action: function (event) {
                    assert.deepEqual(event.data.env.currentID, 2, "should call with correct id");
                    assert.strictEqual(
                        event.data.env.model,
                        "partner",
                        "should call with correct model"
                    );
                    assert.strictEqual(
                        event.data.action_data.name,
                        "method_name",
                        "should call correct method"
                    );
                    assert.strictEqual(
                        event.data.action_data.type,
                        "object",
                        "should have correct type"
                    );
                },
            },
        });

        await click(form.$(".oe_kanban_action_button"));
    });

    QUnit.skipWOWL(
        "one2many kanban with edit type action and widget with specialData",
        async function (assert) {
            assert.expect(3);

            testUtils.mock.patch(BasicModel, {
                _fetchSpecialDataForMyWidget() {
                    assert.step("_fetchSpecialDataForMyWidget");
                    return Promise.resolve();
                },
            });
            const MyWidget = AbstractField.extend({
                specialData: "_fetchSpecialDataForMyWidget",
                className: "my_widget",
            });
            fieldRegistry.add("specialWidget", MyWidget);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                // turtle_int is displayed without widget in the kanban, and with
                // widget required specialData in the form
                arch: `
                    <form>
                        <group>
                            <field name="turtles" mode="kanban">
                                <kanban>
                                    <templates>
                                        <t t-name="kanban-box">
                                            <div><field name="display_name"/></div>
                                            <div><field name="turtle_foo"/></div>
                                            <div><field name="turtle_int"/></div>
                                            <div> <a type="edit"> Edit </a> </div>
                                        </t>
                                    </templates>
                                </kanban>
                                <form>
                                    <field name="product_id" widget="statusbar"/>
                                    <field name="turtle_int" widget="specialWidget"/>
                                </form>
                            </field>
                        </group>
                    </form>`,
                resId: 1,
            });

            await click(form.$(".oe_kanban_action:eq(0)"));
            assert.containsOnce(document.body, ".modal .my_widget", "should add our custom widget");
            assert.verifySteps(["_fetchSpecialDataForMyWidget"]);
        }
    );

    QUnit.skipWOWL(
        "one2many list with onchange and domain widget (widget using SpecialData)",
        async function (assert) {
            // TODO: rename this test: it no longer uses the DomainField
            assert.expect(4);

            testUtils.mock.patch(BasicModel, {
                _fetchSpecialDataForMyWidget() {
                    assert.step("_fetchSpecialDataForMyWidget");
                    return Promise.resolve();
                },
            });
            const MyWidget = AbstractField.extend({
                specialData: "_fetchSpecialDataForMyWidget",
                className: "my_widget",
            });
            fieldRegistry.add("specialWidget", MyWidget);

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    var virtualID = obj.turtles[1][1];
                    obj.turtles = [
                        [5], // delete all
                        [
                            0,
                            virtualID,
                            {
                                display_name: "coucou",
                                product_id: [37, "xphone"],
                                turtle_bar: false,
                                turtle_foo: "has changed",
                                turtle_int: 42,
                                turtle_qux: 9.8,
                                partner_ids: [],
                                turtle_ref: "product,37",
                            },
                        ],
                    ];
                },
            };
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                // turtle_int is displayed without widget in the list, and with
                // widget required specialData in the form
                arch: `
                    <form>
                        <group>
                            <field name="turtles" mode="tree">
                                <tree>
                                    <field name="display_name"/>
                                    <field name="turtle_foo"/>
                                    <field name="turtle_int"/>
                                </tree>
                                <form>
                                    <field name="turtle_int" widget="specialWidget"/>
                                </form>
                            </field>
                        </group>
                    </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            await click(form.$(".o_field_one2many .o_field_x2many_list_row_add a"));
            assert.strictEqual($(".modal").length, 1, "form view dialog should be opened");
            await click($(".modal-footer button:first"));

            assert.strictEqual(
                form.$(".o_field_one2many tbody tr:first").text(),
                "coucouhas changed42",
                "the onchange should create one new record and remove the existing"
            );

            await click(form.$(".o_field_one2many .o_legacy_list_view tbody tr:eq(0) td:first"));

            await clickSave(target);
            assert.verifySteps(
                ["_fetchSpecialDataForMyWidget"],
                "should only fetch special data once"
            );
        }
    );

    QUnit.skipWOWL("one2many without inline tree arch", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].turtles = [2, 3];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            // should not call loadViews for the field with many2many_tags widget,
            // nor for the invisible field
            arch: `
                <form>
                    <group>
                        <field name="p" widget="many2many_tags"/>
                        <field name="turtles"/>
                        <field name="timmy" invisible="1"/>
                    </group>
                </form>`,
            resId: 1,
            archs: {
                "turtle,false,list": `
                    <tree>
                        <field name="turtle_bar"/>
                        <field name="display_name"/>
                        <field name="partner_ids"/>
                    </tree>`,
            },
        });

        assert.containsOnce(
            form,
            '.o_field_widget[name="turtles"] .o_list_view',
            "should display one2many list view in the modal"
        );

        assert.containsN(form, ".o_data_row", 2, "should display the 2 turtles");
    });

    QUnit.skipWOWL("many2one and many2many in one2many", async function (assert) {
        assert.expect(11);

        serverData.models.turtle.records[1].product_id = 37;
        serverData.models.partner.records[0].turtles = [2, 3];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field"/>
                        <field name="turtles">
                            <form>
                                <group>
                                    <field name="product_id"/>
                                </group>
                            </form>
                            <tree editable="top">
                                <field name="display_name"/>
                                <field name="product_id"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "write") {
                    var commands = args.args[1].turtles;
                    assert.strictEqual(commands.length, 2, "should have generated 2 commands");
                    assert.deepEqual(
                        commands[0],
                        [
                            1,
                            2,
                            {
                                partner_ids: [[6, false, [2, 1]]],
                                product_id: 41,
                            },
                        ],
                        "generated commands should be correct"
                    );
                    assert.deepEqual(
                        commands[1],
                        [4, 3, false],
                        "generated commands should be correct"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(form, ".o_data_row", 2, "should display the 2 turtles");
        assert.strictEqual(
            form.$(".o_data_row:first td:nth(1)").text(),
            "xphone",
            "should correctly display the m2o"
        );
        assert.strictEqual(
            form.$(".o_data_row:first td:nth(2) .badge").length,
            2,
            "m2m should contain two tags"
        );
        assert.strictEqual(
            form.$(".o_data_row:first td:nth(2) .badge:first span .o_tag_badge_text").text(),
            "second record",
            "m2m values should have been correctly fetched"
        );

        await click(form.$(".o_data_row:first"));
        assert.containsOnce(
            form,
            ".o_form_view.o_form_editable",
            "should toggle form mode to edit"
        );

        // edit the m2m of first row
        await click(form.$(".o_list_view tbody td:first()"));
        // remove a tag
        await click(form.$(".o_field_many2manytags .badge:contains(aaa) .o_delete"));
        assert.strictEqual(
            form.$(".o_selected_row .o_field_many2manytags .o_badge_text:contains(aaa)").length,
            0,
            "tag should have been correctly removed"
        );
        // add a tag
        await testUtils.fields.many2one.clickOpenDropdown("partner_ids");
        await testUtils.fields.many2one.clickHighlightedItem("partner_ids");
        assert.strictEqual(
            form.$(".o_selected_row .o_field_many2manytags .o_badge_text:contains(first record)")
                .length,
            1,
            "tag should have been correctly added"
        );

        // edit the m2o of first row
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickItem("product_id", "xpad");
        assert.strictEqual(
            form.$(".o_selected_row .o_field_many2one:first input").val(),
            "xpad",
            "m2o value should have been updated"
        );

        // save (should correctly generate the commands)
        await clickSave(target);
    });

    QUnit.skipWOWL(
        "many2manytag in one2many, onchange, some modifiers, and more than one page",
        async function (assert) {
            assert.expect(9);

            serverData.models.partner.records[0].turtles = [1, 2, 3];

            serverData.models.partner.onchanges.turtles = function () {};

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top" limit="2">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags" attrs="{'readonly': [('turtle_foo', '=', 'a')]}"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                viewOptions: { mode: "edit" },
                mockRPC(route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });
            assert.containsN(form, ".o_data_row", 2, "there should be only 2 rows displayed");
            await clickFirst(form.$(".o_list_record_remove"));
            await clickFirst(form.$(".o_list_record_remove"));

            assert.containsOnce(form, ".o_data_row", "there should be just one remaining row");

            assert.verifySteps([
                "read", // initial read on partner
                "read", // initial read on turtle
                "read", // batched read on partner (field partner_ids)
                "read", // after first delete, read on turtle (to fetch 3rd record)
                "onchange", // after first delete, onchange on field turtles
                "onchange", // onchange after second delete
            ]);
        }
    );

    QUnit.skipWOWL("onchange many2many in one2many list editable", async function (assert) {
        assert.expect(14);

        serverData.models.product.records.push({
            id: 1,
            display_name: "xenomorphe",
        });

        serverData.models.turtle.onchanges = {
            product_id: function (rec) {
                if (rec.product_id) {
                    rec.partner_ids = [[5], [4, rec.product_id === 41 ? 1 : 2]];
                }
            },
        };
        var partnerOnchange = function (rec) {
            if (!rec.int_field || !rec.turtles.length) {
                return;
            }
            rec.turtles = [
                [5],
                [
                    0,
                    0,
                    {
                        display_name: "new line",
                        product_id: [37, "xphone"],
                        partner_ids: [[5], [4, 1]],
                    },
                ],
                [
                    0,
                    rec.turtles[0][1],
                    {
                        display_name: rec.turtles[0][2].display_name,
                        product_id: [1, "xenomorphe"],
                        partner_ids: [[5], [4, 2]],
                    },
                ],
            ];
        };

        serverData.models.partner.onchanges = {
            int_field: partnerOnchange,
            turtles: partnerOnchange,
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field"/>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="display_name"/>
                                <field name="product_id"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
        });

        // add new line (first, xpad)
        await addRow(target);
        await testUtils.fields.editInput(form.$('input[name="display_name"]'), "first");
        await click(form.$('div[name="product_id"] input'));
        // the onchange won't be generated
        await click($("li.ui-menu-item a:contains(xpad)").trigger("mouseenter"));

        assert.containsOnce(
            form,
            ".o_field_many2manytags.o_input",
            "should display the line in editable mode"
        );
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "xpad",
            "should display the product xpad"
        );
        assert.strictEqual(
            form.$(".o_field_many2manytags.o_input .o_badge_text").text(),
            "first record",
            "should display the tag from the onchange"
        );

        await click(form.$('input.o_field_integer[name="int_field"]'));

        assert.strictEqual(
            form.$(".o_data_cell.o_required_modifier").text(),
            "xpad",
            "should display the product xpad"
        );
        assert.strictEqual(
            form.$(".o_field_many2manytags:not(.o_input) .o_badge_text").text(),
            "first record",
            "should display the tag in readonly"
        );

        // enable the many2many onchange and generate it
        await testUtils.fields.editInput(form.$('input.o_field_integer[name="int_field"]'), "10");

        assert.strictEqual(
            form.$(".o_data_cell.o_required_modifier").text(),
            "xenomorphexphone",
            "should display the product xphone and xenomorphe"
        );
        assert.strictEqual(
            form.$(".o_data_row").text().replace(/\s+/g, " "),
            "firstxenomorphe second record new linexphone first record ",
            "should display the name, one2many and many2many value"
        );

        // disable the many2many onchange
        await testUtils.fields.editInput(form.$('input.o_field_integer[name="int_field"]'), "0");

        // remove and start over
        await click(form.$(".o_list_record_remove:first button"));
        await click(form.$(".o_list_record_remove:first button"));

        // enable the many2many onchange
        await testUtils.fields.editInput(form.$('input.o_field_integer[name="int_field"]'), "10");

        // add new line (first, xenomorphe)
        await addRow(target);
        await testUtils.fields.editInput(form.$('input[name="display_name"]'), "first");
        await click(form.$('div[name="product_id"] input'));
        // generate the onchange
        await click($("li.ui-menu-item a:contains(xenomorphe)").trigger("mouseenter"));

        assert.containsOnce(
            form,
            ".o_field_many2manytags.o_input",
            "should display the line in editable mode"
        );
        assert.strictEqual(
            form.$(".o_field_many2one input").val(),
            "xenomorphe",
            "should display the product xenomorphe"
        );
        assert.strictEqual(
            form.$(".o_field_many2manytags.o_input .o_badge_text").text(),
            "second record",
            "should display the tag from the onchange"
        );

        // put list in readonly mode
        await click(form.$('input.o_field_integer[name="int_field"]'));

        assert.strictEqual(
            form.$(".o_data_cell.o_required_modifier").text(),
            "xenomorphexphone",
            "should display the product xphone and xenomorphe"
        );
        assert.strictEqual(
            form.$(".o_field_many2manytags:not(.o_input) .o_badge_text").text(),
            "second recordfirst record",
            "should display the tag in readonly (first record and second record)"
        );

        await testUtils.fields.editInput(form.$('input.o_field_integer[name="int_field"]'), "10");

        assert.strictEqual(
            form.$(".o_data_row").text().replace(/\s+/g, " "),
            "firstxenomorphe second record new linexphone first record ",
            "should display the name, one2many and many2many value"
        );

        await clickSave(target);

        assert.strictEqual(
            form.$(".o_data_row").text().replace(/\s+/g, " "),
            "firstxenomorphe second record new linexphone first record ",
            "should display the name, one2many and many2many value after save"
        );
    });

    QUnit.skipWOWL("load view for x2many in one2many", async function (assert) {
        assert.expect(2);

        serverData.models.turtle.records[1].product_id = 37;
        serverData.models.partner.records[0].turtles = [2, 3];
        serverData.models.partner.records[2].turtles = [1, 3];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field"/>
                        <field name="turtles">
                            <form>
                                <group>
                                    <field name="product_id"/>
                                    <field name="partner_ids"/>
                                </group>
                            </form>
                            <tree>
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            archs: {
                "partner,false,list": '<tree><field name="display_name"/></tree>',
            },
        });

        assert.containsN(form, ".o_data_row", 2, "should display the 2 turtles");

        await click(form.$(".o_data_row:first"));
        await testUtils.nextTick(); // wait for quick edit

        assert.strictEqual(
            $('.modal .o_field_widget[name="partner_ids"] .o_list_view').length,
            1,
            "should display many2many list view in the modal"
        );
    });

    QUnit.skipWOWL(
        "one2many (who contains a one2many) with tree view and without form view",
        async function (assert) {
            assert.expect(1);

            // avoid error in _postprocess

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="turtles">
                                <tree>
                                    <field name="partner_ids"/>
                                </tree>
                            </field>
                        </group>
                    </form>`,
                resId: 1,
                archs: {
                    "turtle,false,form": '<form><field name="turtle_foo"/></form>',
                },
            });

            await click(form.$(".o_data_row:first"));

            assert.strictEqual(
                $('.modal .o_field_widget[name="turtle_foo"]').val(),
                "blip",
                "should open the modal and display the form field"
            );
        }
    );

    QUnit.skipWOWL(
        "one2many with x2many in form view (but not in list view)",
        async function (assert) {
            assert.expect(1);

            // avoid error when saving the edited related record (because the
            // related x2m field is unknown in the inline list view)
            // also ensure that the changes are correctly saved

            serverData.models.turtle.fields.o2m = {
                string: "o2m",
                type: "one2many",
                relation: "user",
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="turtles">
                                <tree>
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </group>
                    </form>`,
                resId: 1,
                archs: {
                    "turtle,false,form": `
                        <form>
                            <field name="partner_ids" widget="many2many_tags"/>
                        </form>`,
                },
                viewOptions: {
                    mode: "edit",
                },
                mockRPC(route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(args.args[1].turtles, [
                            [
                                1,
                                2,
                                {
                                    partner_ids: [[6, false, [2, 4, 1]]],
                                },
                            ],
                        ]);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await click(form.$(".o_data_row:first")); // edit first record

            await testUtils.fields.many2one.clickOpenDropdown("partner_ids");
            await testUtils.fields.many2one.clickHighlightedItem("partner_ids");

            // add a many2many tag and save
            await click($(".modal .o_field_many2manytags input"));
            await testUtils.fields.editInput($(".modal .o_field_many2manytags input"), "test");
            await click($(".modal .modal-footer .btn-primary")); // save

            await clickSave(target);
        }
    );

    QUnit.skipWOWL("many2many list in a one2many opened by a many2one", async function (assert) {
        assert.expect(1);

        serverData.models.turtle.records[1].turtle_trululu = 2;
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_trululu"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            archs: {
                "partner,false,form": '<form> <field name="timmy"/> </form>',
                "partner_type,false,list":
                    '<tree editable="bottom"><field name="display_name"/></tree>',
                "partner_type,false,search": "<search></search>",
            },
            viewOptions: {
                mode: "edit",
            },
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/get_formview_id") {
                    return Promise.resolve(false);
                }
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args[1].timmy,
                        [[6, false, [12]]],
                        "should properly write ids"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        // edit the first partner in the one2many partner form view
        await click(form.$(".o_data_row:first td.o_data_cell"));
        // open form view for many2one
        await click(form.$(".o_external_button"));

        // click on add, to add a new partner in the m2m
        await click($(".modal .o_field_x2many_list_row_add a"));

        // select the partner_type 'gold' (this closes the 2nd modal)
        await click($(".modal td:contains(gold)"));

        // confirm the changes in the modal
        await click($(".modal .modal-footer .btn-primary"));

        await clickSave(target);
    });

    QUnit.skipWOWL("nested x2many default values", async function (assert) {
        assert.expect(3);

        serverData.models.partner.fields.turtles.default = [
            [0, 0, { partner_ids: [[6, 0, [4]]] }],
            [0, 0, { partner_ids: [[6, 0, [1]]] }],
        ];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="partner_ids" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
        });

        assert.containsN(
            form,
            ".o_list_view .o_data_row",
            2,
            "one2many list should contain 2 rows"
        );
        assert.containsN(
            form,
            '.o_list_view .o_field_many2manytags[name="partner_ids"] .badge',
            2,
            "m2mtags should contain two tags"
        );
        assert.strictEqual(
            form.$('.o_list_view .o_field_many2manytags[name="partner_ids"] .o_badge_text').text(),
            "aaafirst record",
            "tag names should have been correctly loaded"
        );
    });

    QUnit.skipWOWL("nested x2many (inline form view) and onchanges", async function (assert) {
        assert.expect(6);

        serverData.models.partner.onchanges.bar = function (obj) {
            if (!obj.bar) {
                obj.p = [
                    [5],
                    [
                        0,
                        0,
                        {
                            turtles: [
                                [
                                    0,
                                    0,
                                    {
                                        turtle_foo: "new turtle",
                                    },
                                ],
                            ],
                        },
                    ],
                ];
            }
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form>
                    <field name="bar"/>
                    <field name="p">
                        <tree>
                            <field name="turtles"/>
                        </tree>
                        <form>
                            <field name="turtles">
                                <tree>
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
        });

        assert.containsNone(form, ".o_data_row");

        await click(form.$(".o_field_widget[name=bar] input"));
        assert.containsOnce(form, ".o_data_row");
        assert.strictEqual(form.$(".o_data_row").text(), "1 record");

        await click(form.$(".o_data_row:first"));

        assert.containsOnce(document.body, ".modal .o_form_view");
        assert.containsOnce(document.body, ".modal .o_form_view .o_data_row");
        assert.strictEqual($(".modal .o_form_view .o_data_row").text(), "new turtle");
    });

    QUnit.skipWOWL("nested x2many (non inline form view) and onchanges", async function (assert) {
        assert.expect(6);

        serverData.models.partner.onchanges.bar = function (obj) {
            if (!obj.bar) {
                obj.p = [
                    [5],
                    [
                        0,
                        0,
                        {
                            turtles: [
                                [
                                    0,
                                    0,
                                    {
                                        turtle_foo: "new turtle",
                                    },
                                ],
                            ],
                        },
                    ],
                ];
            }
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="p">
                        <tree>
                            <field name="turtles"/>
                        </tree>
                    </field>
                </form>`,
            archs: {
                "partner,false,form": `
                    <form>
                        <field name="turtles">
                            <tree>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
            },
        });

        assert.containsNone(form, ".o_data_row");

        await click(form.$(".o_field_widget[name=bar] input"));
        assert.containsOnce(form, ".o_data_row");
        assert.strictEqual(form.$(".o_data_row").text(), "1 record");

        await click(form.$(".o_data_row:first"));

        assert.containsOnce(document.body, ".modal .o_form_view");
        assert.containsOnce(document.body, ".modal .o_form_view .o_data_row");
        assert.strictEqual($(".modal .o_form_view .o_data_row").text(), "new turtle");
    });

    QUnit.skipWOWL(
        "nested x2many (non inline views and no widget on inner x2many in list)",
        async function (assert) {
            assert.expect(5);

            serverData.models.partner.records[0].p = [1];
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="p"/></form>',
                archs: {
                    "partner,false,list": '<tree><field name="turtles"/></tree>',
                    "partner,false,form":
                        '<form><field name="turtles" widget="many2many_tags"/></form>',
                },
                resId: 1,
            });

            assert.containsOnce(form, ".o_data_row");
            assert.strictEqual(form.$(".o_data_row").text(), "1 record");

            await click(form.$(".o_data_row"));

            assert.containsOnce(document.body, ".modal .o_form_view");
            assert.containsOnce(document.body, ".modal .o_form_view .o_field_many2manytags .badge");
            assert.strictEqual($(".modal .o_field_many2manytags").text().trim(), "donatello");
        }
    );

    QUnit.skipWOWL(
        "one2many (who contains display_name) with tree view and without form view",
        async function (assert) {
            assert.expect(1);

            // avoid error in _fetchX2Manys

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="turtles">
                                <tree>
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </group>
                    </form>`,
                resId: 1,
                archs: {
                    "turtle,false,form": '<form><field name="turtle_foo"/></form>',
                },
            });

            await click(form.$(".o_data_row:first"));

            assert.strictEqual(
                $('.modal .o_field_widget[name="turtle_foo"]').val(),
                "blip",
                "should open the modal and display the form field"
            );
        }
    );

    QUnit.skipWOWL("one2many field with virtual ids", async function (assert) {
        assert.expect(11);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <notebook>
                                <page>
                                    <field name="p" mode="kanban">
                                        <kanban>
                                            <templates>
                                                <t t-name="kanban-box">
                                                    <div class="oe_kanban_details">
                                                        <div class="o_test_id">
                                                            <field name="id"/>
                                                        </div>
                                                        <div class="o_test_foo">
                                                            <field name="foo"/>
                                                        </div>
                                                    </div>
                                                </t>
                                            </templates>
                                        </kanban>
                                    </field>
                                </page>
                            </notebook>
                        </group>
                    </sheet>
                </form>`,
            archs: {
                "partner,false,form": '<form><field name="foo"/></form>',
            },
            resId: 4,
        });

        assert.containsOnce(
            form,
            ".o_field_widget .o_kanban_view",
            "should have one inner kanban view for the one2many field"
        );
        assert.strictEqual(
            form.$(".o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").length,
            0,
            "should not have kanban records yet"
        );

        // // switch to edit mode and create a new kanban record
        await clickEdit(target);
        await click(form.$(".o_field_widget .o-kanban-button-new"));

        // save & close the modal
        assert.strictEqual(
            $(".modal-content input.o_field_widget").val(),
            "My little Foo Value",
            "should already have the default value for field foo"
        );
        await click($(".modal-content .btn-primary").first());

        assert.containsOnce(
            form,
            ".o_field_widget .o_kanban_view",
            "should have one inner kanban view for the one2many field"
        );
        assert.strictEqual(
            form.$(".o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").length,
            1,
            "should now have one kanban record"
        );
        assert.strictEqual(
            form
                .$(
                    ".o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_id"
                )
                .text(),
            "",
            "should not have a value for the id field"
        );
        assert.strictEqual(
            form
                .$(
                    ".o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_foo"
                )
                .text(),
            "My little Foo Value",
            "should have a value for the foo field"
        );

        // save the view to force a create of the new record in the one2many
        await clickSave(target);
        assert.containsOnce(
            form,
            ".o_field_widget .o_kanban_view",
            "should have one inner kanban view for the one2many field"
        );
        assert.strictEqual(
            form.$(".o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)").length,
            1,
            "should now have one kanban record"
        );
        assert.notEqual(
            form
                .$(
                    ".o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_id"
                )
                .text(),
            "",
            "should now have a value for the id field"
        );
        assert.strictEqual(
            form
                .$(
                    ".o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_foo"
                )
                .text(),
            "My little Foo Value",
            "should still have a value for the foo field"
        );
    });

    QUnit.skipWOWL("one2many field with virtual ids with kanban button", async function (assert) {
        assert.expect(25);

        testUtils.mock.patch(KanbanRecord, {
            init: function () {
                this._super.apply(this, arguments);
                this._onKanbanActionClicked = this.__proto__._onKanbanActionClicked;
            },
        });

        serverData.models.partner.records[0].p = [4];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" mode="kanban">
                        <kanban>
                            <templates>
                                <field name="foo"/>
                                <t t-name="kanban-box">
                                    <div>
                                        <span><t t-esc="record.foo.value"/></span>
                                        <button type="object" class="btn btn-link fa fa-shopping-cart" name="button_warn" string="button_warn" warn="warn" />
                                        <button type="object" class="btn btn-link fa fa-shopping-cart" name="button_disabled" string="button_disabled" />
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            archs: {
                "partner,false,form": '<form><field name="foo"/></form>',
            },
            resId: 1,
            services: {
                notification: {
                    notify: function (params) {
                        assert.step(params.type);
                    },
                },
            },
            intercepts: {
                execute_action: function (event) {
                    assert.step(
                        event.data.action_data.name +
                            "_" +
                            event.data.env.model +
                            "_" +
                            event.data.env.currentID
                    );
                    event.data.on_success();
                },
            },
        });

        // 1. Define all css selector
        var oKanbanView = ".o_field_widget .o_kanban_view";
        var oKanbanRecordActive = oKanbanView + " .o_kanban_record:not(.o_kanban_ghost)";
        var oAllKanbanButton = oKanbanRecordActive + ' button[data-type="object"]';
        var btn1 = oKanbanRecordActive + ':nth-child(1) button[data-type="object"]';
        var btn2 = oKanbanRecordActive + ':nth-child(2) button[data-type="object"]';
        var btn1Warn = btn1 + '[data-name="button_warn"]';
        var btn1Disabled = btn1 + '[data-name="button_disabled"]';
        var btn2Warn = btn2 + '[data-name="button_warn"]';
        var btn2Disabled = btn2 + '[data-name="button_disabled"]';

        // check if we already have one kanban card
        assert.containsOnce(
            form,
            oKanbanView,
            "should have one inner kanban view for the one2many field"
        );
        assert.containsOnce(form, oKanbanRecordActive, "should have one kanban records yet");

        // we have 2 buttons
        assert.containsN(form, oAllKanbanButton, 2, "should have 2 buttons type object");

        // disabled ?
        assert.containsNone(
            form,
            oAllKanbanButton + "[disabled]",
            "should not have button type object disabled"
        );

        // click on the button
        await click(form.$(btn1Disabled));
        await click(form.$(btn1Warn));

        // switch to edit mode
        await clickEdit(target);

        // click on existing buttons
        await click(form.$(btn1Disabled));
        await click(form.$(btn1Warn));

        // create new kanban
        await click(form.$(".o_field_widget .o-kanban-button-new"));

        // save & close the modal
        assert.strictEqual(
            $(".modal-content input.o_field_widget").val(),
            "My little Foo Value",
            "should already have the default value for field foo"
        );
        await click($(".modal-content .btn-primary").first());

        // check new item
        assert.containsN(form, oAllKanbanButton, 4, "should have 4 buttons type object");
        assert.containsN(form, btn1, 2, "should have 2 buttons type object in area 1");
        assert.containsN(form, btn2, 2, "should have 2 buttons type object in area 2");
        assert.containsOnce(
            form,
            oAllKanbanButton + "[disabled]",
            "should have 1 button type object disabled"
        );

        assert.strictEqual(
            form.$(btn2Disabled).attr("disabled"),
            "disabled",
            "Should have a button type object disabled in area 2"
        );
        assert.strictEqual(
            form.$(btn2Warn).attr("disabled"),
            undefined,
            "Should have a button type object not disabled in area 2"
        );
        assert.strictEqual(
            form.$(btn2Warn).attr("warn"),
            "warn",
            "Should have a button type object with warn attr in area 2"
        );

        // click all buttons
        await click(form.$(btn1Disabled));
        await click(form.$(btn1Warn));
        await click(form.$(btn2Disabled));
        await click(form.$(btn2Warn));

        // save the form
        await clickSave(target);

        assert.containsNone(
            form,
            oAllKanbanButton + "[disabled]",
            "should not have button type object disabled after save"
        );

        // click all buttons
        await click(form.$(btn1Disabled));
        await click(form.$(btn1Warn));
        await click(form.$(btn2Disabled));
        await click(form.$(btn2Warn));

        assert.verifySteps(
            [
                "button_disabled_partner_4",
                "button_warn_partner_4",

                "button_disabled_partner_4",
                "button_warn_partner_4",

                "button_disabled_partner_4",
                "button_warn_partner_4",
                "danger", // warn btn8

                "button_disabled_partner_4",
                "button_warn_partner_4",
                "button_disabled_partner_5",
                "button_warn_partner_5",
            ],
            "should have triggered theses 11 clicks event"
        );

        testUtils.mock.unpatch(KanbanRecord);
    });

    QUnit.skipWOWL("focusing fields in one2many list", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </tree>
                        </field>
                    </group>
                    <field name="foo"/>
                </form>`,
            resId: 1,
        });
        await clickEdit(target);

        await click(form.$(".o_data_row:first td:first"));
        assert.strictEqual(
            form.$('input[name="turtle_foo"]')[0],
            document.activeElement,
            "turtle foo field should have focus"
        );

        await testUtils.fields.triggerKeydown(form.$('input[name="turtle_foo"]'), "tab");
        assert.strictEqual(
            form.$('input[name="turtle_int"]')[0],
            document.activeElement,
            "turtle int field should have focus"
        );
    });

    QUnit.test("one2many list editable = top", async function (assert) {
        assert.expect(6);

        serverData.models.turtle.fields.turtle_foo.default = "default foo turtle";
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "write") {
                    const commands = args.args[1].turtles;
                    assert.strictEqual(commands[0][0], 0, "first command is a create");
                    assert.strictEqual(commands[1][0], 4, "second command is a link to");
                }
            },
        });
        await clickEdit(target);

        assert.containsOnce(target, ".o_data_row", "should start with one data row");

        await addRow(target);

        assert.containsN(target, ".o_data_row", 2, "should have 2 data rows");
        assert.strictEqual(
            target.querySelector("tr.o_data_row input").value,
            "default foo turtle",
            "first row should be the new value"
        );
        assert.hasClass(
            target.querySelector("tr.o_data_row"),
            "o_selected_row",
            "first row should be selected"
        );

        await clickSave(target);
    });

    QUnit.test("one2many list editable = bottom", async function (assert) {
        assert.expect(6);
        serverData.models.turtle.fields.turtle_foo.default = "default foo turtle";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "write") {
                    const commands = args.args[1].turtles;
                    assert.strictEqual(commands[0][0], 4, "first command is a link to");
                    assert.strictEqual(commands[1][0], 0, "second command is a create");
                }
            },
        });
        await clickEdit(target);

        assert.containsOnce(target, ".o_data_row", "should start with one data row");

        await addRow(target);

        assert.containsN(target, ".o_data_row", 2, "should have 2 data rows");
        assert.strictEqual(
            target.querySelector("tr.o_data_row input").value,
            "default foo turtle",
            "second row should be the new value"
        );
        assert.hasClass(
            target.querySelectorAll("tr.o_data_row")[1],
            "o_selected_row",
            "second row should be selected"
        );

        await clickSave(target);
    });

    QUnit.skipWOWL('one2many list edition, no "Remove" button in modal', async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.foo.default = false;

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });
        await clickEdit(target);

        await click(form.$("tbody td.o_field_x2many_list_row_add a"));
        assert.containsOnce($(document), $(".modal"), "there should be a modal opened");
        assert.containsNone(
            $(".modal .modal-footer .o_btn_remove"),
            'modal should not contain a "Remove" button'
        );

        // Discard a modal
        await click($(".modal-footer .btn-secondary"));

        await clickDiscard(target);
    });

    QUnit.skipWOWL('x2many fields use their "mode" attribute', async function (assert) {
        assert.expect(1);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field mode="kanban" name="turtles">
                            <tree>
                                <field name="turtle_foo"/>
                            </tree>
                            <kanban>
                                <templates>
                                    <t t-name="kanban-box">
                                        <div>
                                            <field name="turtle_int"/>
                                        </div>
                                    </t>
                                </templates>
                            </kanban>
                        </field>
                    </group>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            form,
            ".o_field_one2many .o_kanban_view",
            "should have rendered a kanban view"
        );
    });

    QUnit.skipWOWL("one2many list editable, onchange and required field", async function (assert) {
        assert.expect(8);

        serverData.models.turtle.fields.turtle_foo.required = true;
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.int_field = obj.turtles.length;
            },
        };
        serverData.models.partner.records[0].int_field = 0;
        serverData.models.partner.records[0].turtles = [];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="turtle_int"/>
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
            resId: 1,
        });
        await clickEdit(target);

        assert.strictEqual(
            form.$('.o_field_widget[name="int_field"]').val(),
            "0",
            "int_field should start with value 0"
        );
        await addRow(target);
        assert.strictEqual(
            form.$('.o_field_widget[name="int_field"]').val(),
            "0",
            "int_field should still be 0 (no onchange should have been done yet"
        );

        assert.verifySteps(["read", "onchange"]);

        await testUtils.fields.editInput(form.$('.o_field_widget[name="turtle_foo"]'), "some text");
        assert.verifySteps(["onchange"]);
        assert.strictEqual(
            form.$('.o_field_widget[name="int_field"]').val(),
            "1",
            "int_field should now be 1 (the onchange should have been done"
        );
    });

    QUnit.skipWOWL(
        "one2many list editable: trigger onchange when row is valid",
        async function (assert) {
            // should omit require fields that aren't in the view as they (obviously)
            // have no value, when checking the validity of required fields
            // shouldn't consider numerical fields with value 0 as unset
            assert.expect(13);

            serverData.models.turtle.fields.turtle_foo.required = true;
            serverData.models.turtle.fields.turtle_qux.required = true; // required field not in the view
            serverData.models.turtle.fields.turtle_bar.required = true; // required boolean field with no default
            delete serverData.models.turtle.fields.turtle_bar.default;
            serverData.models.turtle.fields.turtle_int.required = true; // required int field (default 0)
            serverData.models.turtle.fields.turtle_int.default = 0;
            serverData.models.turtle.fields.partner_ids.required = true; // required many2many
            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = obj.turtles.length;
                },
            };
            serverData.models.partner.records[0].int_field = 0;
            serverData.models.partner.records[0].turtles = [];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="turtles"/>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
                archs: {
                    "turtle,false,list": `
                        <tree editable="top">
                            <field name="turtle_qux"/>
                            <field name="turtle_bar"/>
                            <field name="turtle_int"/>
                            <field name="turtle_foo"/>
                            <field name="partner_ids" widget="many2many_tags"/>
                        </tree>`,
                },
                resId: 1,
            });
            await clickEdit(target);

            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "0",
                "int_field should start with value 0"
            );

            // add a new row (which is invalid at first)
            await addRow(target);
            await testUtils.owlCompatibilityExtraNextTick();
            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "0",
                "int_field should still be 0 (no onchange should have been done yet)"
            );
            assert.verifySteps(["load_views", "read", "onchange"]);

            // fill turtle_foo field
            await testUtils.fields.editInput(
                form.$('.o_field_widget[name="turtle_foo"]'),
                "some text"
            );
            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "0",
                "int_field should still be 0 (no onchange should have been done yet)"
            );
            assert.verifySteps([], "no onchange should have been applied");

            // fill partner_ids field with a tag (all required fields will then be set)
            await testUtils.fields.many2one.clickOpenDropdown("partner_ids");
            await testUtils.fields.many2one.clickHighlightedItem("partner_ids");
            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "1",
                "int_field should now be 1 (the onchange should have been done"
            );
            assert.verifySteps(["name_search", "read", "onchange"]);
        }
    );

    QUnit.skipWOWL(
        "one2many list editable: 'required' modifiers is properly working",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = obj.turtles.length;
                },
            };

            serverData.models.partner.records[0].turtles = [];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            await clickEdit(target);

            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "10",
                "int_field should start with value 10"
            );

            await addRow(target);

            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "10",
                "int_field should still be 10 (no onchange, because line is not valid)"
            );

            // fill turtle_foo field
            await testUtils.fields.editInput(
                form.$('.o_field_widget[name="turtle_foo"]'),
                "some text"
            );

            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "1",
                "int_field should be 1 (onchange triggered, because line is now valid)"
            );
        }
    );

    QUnit.skipWOWL(
        "one2many list editable: 'required' modifiers is properly working, part 2",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = obj.turtles.length;
                },
            };

            serverData.models.partner.records[0].turtles = [];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="int_field"/>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_int"/>
                                <field name="turtle_foo" attrs='{"required": [["turtle_int", "=", 0]]}'/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            await clickEdit(target);

            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "10",
                "int_field should start with value 10"
            );

            await addRow(target);

            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "10",
                "int_field should still be 10 (no onchange, because line is not valid)"
            );

            // fill turtle_int field
            await testUtils.fields.editInput(form.$('.o_field_widget[name="turtle_int"]'), "1");

            assert.strictEqual(
                form.$('.o_field_widget[name="int_field"]').val(),
                "1",
                "int_field should be 1 (onchange triggered, because line is now valid)"
            );
        }
    );

    QUnit.skipWOWL(
        "one2many list editable: add new line before onchange returns",
        async function (assert) {
            // If the user adds a new row (with a required field with onchange), selects
            // a value for that field, then adds another row before the onchange returns,
            // the editable list must wait for the onchange to return before trying to
            // unselect the first row, otherwise it will be detected as invalid.
            assert.expect(7);

            serverData.models.turtle.onchanges = {
                turtle_trululu: function () {},
            };

            var prom;
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_trululu" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === "onchange") {
                        return Promise.resolve(prom).then(_.constant(result));
                    }
                    return result;
                },
            });

            // add a first line but hold the onchange back
            await addRow(target);
            prom = testUtils.makeTestPromise();
            assert.containsOnce(
                form,
                ".o_data_row",
                "should have created the first row immediately"
            );
            await testUtils.fields.many2one.clickOpenDropdown("turtle_trululu");
            await testUtils.fields.many2one.clickHighlightedItem("turtle_trululu");

            // try to add a second line and check that it is correctly waiting
            // for the onchange to return
            await addRow(target);
            assert.strictEqual($(".modal").length, 0, "no modal should be displayed");
            assert.strictEqual(
                $(".o_field_invalid").length,
                0,
                "no field should be marked as invalid"
            );
            assert.containsOnce(
                form,
                ".o_data_row",
                "should wait for the onchange to create the second row"
            );
            assert.hasClass(
                form.$(".o_data_row"),
                "o_selected_row",
                "first row should still be in edition"
            );

            // resolve the onchange promise
            prom.resolve();
            await testUtils.nextTick();
            assert.containsN(form, ".o_data_row", 2, "second row should now have been created");
            assert.doesNotHaveClass(
                form.$(".o_data_row:first"),
                "o_selected_row",
                "first row should no more be in edition"
            );
        }
    );

    QUnit.skipWOWL(
        "editable list: multiple clicks on Add an item do not create invalid rows",
        async function (assert) {
            assert.expect(3);

            serverData.models.turtle.onchanges = {
                turtle_trululu: function () {},
            };

            var prom;
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_trululu" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === "onchange") {
                        return Promise.resolve(prom).then(_.constant(result));
                    }
                    return result;
                },
            });
            prom = testUtils.makeTestPromise();
            // click twice to add a new line
            await addRow(target);
            await addRow(target);
            assert.containsNone(
                form,
                ".o_data_row",
                "no row should have been created yet (waiting for the onchange)"
            );

            // resolve the onchange promise
            prom.resolve();
            await testUtils.nextTick();
            assert.containsOnce(form, ".o_data_row", "only one row should have been created");
            assert.hasClass(
                form.$(".o_data_row:first"),
                "o_selected_row",
                "the created row should be in edition"
            );
        }
    );

    QUnit.skipWOWL("editable list: value reset by an onchange", async function (assert) {
        // this test reproduces a subtle behavior that may occur in a form view:
        // the user adds a record in a one2many field, and directly clicks on a
        // datetime field of the form view which has an onchange, which totally
        // overrides the value of the one2many (commands 5 and 0). The handler
        // that switches the edited row to readonly is then called after the
        // new value of the one2many field is applied (the one returned by the
        // onchange), so the row that must go to readonly doesn't exist anymore.
        assert.expect(2);

        serverData.models.partner.onchanges = {
            datetime: function (obj) {
                obj.turtles = [[5], [0, 0, { display_name: "new" }]];
            },
        };

        var prom;
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="datetime"/>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "onchange") {
                    return Promise.resolve(prom).then(_.constant(result));
                }
                return result;
            },
        });

        // trigger the two onchanges
        await addRow(target);
        await testUtils.fields.editInput(form.$(".o_data_row .o_field_widget"), "a name");
        prom = testUtils.makeTestPromise();
        await click(form.$(".o_datepicker_input"));
        var dateTimeVal = fieldUtils.format.datetime(moment(), { timezone: false });
        await testUtils.fields.editSelect(form.$(".o_datepicker_input"), dateTimeVal);

        // resolve the onchange promise
        prom.resolve();
        await testUtils.nextTick();

        assert.containsOnce(form, ".o_data_row", "should have one record in the o2m");
        assert.strictEqual(
            form.$(".o_data_row .o_data_cell").text(),
            "new",
            "should be the record created by the onchange"
        );
    });

    QUnit.skipWOWL("editable list: onchange that returns a warning", async function (assert) {
        assert.expect(5);

        serverData.models.turtle.onchanges = {
            display_name: function () {},
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step(args.method);
                    return Promise.resolve({
                        value: {},
                        warning: {
                            title: "Warning",
                            message: "You must first select a partner",
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                mode: "edit",
            },
            intercepts: {
                warning: function () {
                    assert.step("warning");
                },
            },
        });

        // add a line (this should trigger an onchange and a warning)
        await addRow(target);

        // check if 'Add an item' still works (this should trigger an onchange
        // and a warning again)
        await addRow(target);

        assert.verifySteps(["onchange", "warning", "onchange", "warning"]);
    });

    QUnit.skipWOWL("editable list: contexts are correctly sent", async function (assert) {
        assert.expect(5);

        serverData.models.partner.records[0].timmy = [12];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="timmy" context="{'key': parent.foo}">
                        <tree editable="top">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "read" && args.model === "partner") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            active_field: 2,
                            bin_size: true,
                            someKey: "some value",
                        },
                        "sent context should be correct"
                    );
                }
                if (args.method === "read" && args.model === "partner_type") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            key: "yop",
                            active_field: 2,
                            someKey: "some value",
                        },
                        "sent context should be correct"
                    );
                }
                if (args.method === "write") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            active_field: 2,
                            someKey: "some value",
                        },
                        "sent context should be correct"
                    );
                }
                return this._super.apply(this, arguments);
            },
            session: {
                user_context: { someKey: "some value" },
            },
            viewOptions: {
                mode: "edit",
                context: { active_field: 2 },
            },
            resId: 1,
        });

        await click(form.$(".o_data_cell:first"));
        await testUtils.fields.editInput(form.$(".o_field_widget[name=display_name]"), "abc");
        await clickSave(target);
    });

    QUnit.skipWOWL("resetting invisible one2manys", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records[0].turtles = [];
        serverData.models.partner.onchanges.foo = function (obj) {
            obj.turtles = [[5], [4, 1]];
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="turtles" invisible="1"/>
                </form>`,
            viewOptions: {
                mode: "edit",
            },
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.fields.editInput(form.$('input[name="foo"]'), "abcd");
        assert.verifySteps(["read", "onchange"]);
    });

    QUnit.skipWOWL(
        "one2many: onchange that returns unknown field in list, but not in form",
        async function (assert) {
            assert.expect(5);

            serverData.models.partner.onchanges = {
                name: function () {},
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="name"/>
                        <field name="p">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="display_name"/>
                                <field name="timmy" widget="many2many_tags"/>
                            </form>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        return Promise.resolve({
                            value: {
                                p: [[5], [0, 0, { display_name: "new", timmy: [[5], [4, 12]] }]],
                            },
                        });
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.containsOnce(form, ".o_data_row", "the one2many should contain one row");
            assert.containsNone(
                form,
                '.o_field_widget[name="timmy"]',
                "timmy should not be displayed in the list view"
            );

            await click(form.$(".o_data_row td:first"));

            assert.strictEqual(
                $('.modal .o_field_many2manytags[name="timmy"]').length,
                1,
                "timmy should be displayed in the form view"
            );
            assert.strictEqual(
                $('.modal .o_field_many2manytags[name="timmy"] .badge').length,
                1,
                "m2mtags should contain one tag"
            );
            assert.strictEqual(
                $('.modal .o_field_many2manytags[name="timmy"] .o_badge_text').text(),
                "gold",
                "tag name should have been correctly loaded"
            );
        }
    );

    QUnit.skipWOWL(
        "multi level of nested x2manys, onchange and rawChanges",
        async function (assert) {
            assert.expect(8);

            serverData.models.partner.records[0].p = [1];
            serverData.models.partner.onchanges = {
                name: function () {},
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="name"/>
                        <field name="p" attrs="{'readonly': [['name', '=', 'readonly']]}">
                            <tree><field name="display_name"/></tree>
                            <form>
                                <field name="display_name"/>
                                <field name="p">
                                    <tree><field name="display_name"/></tree>
                                    <form><field name="display_name"/></form>
                                </field>
                            </form>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(args.args[1].p[0][2], {
                            p: [[1, 1, { display_name: "new name" }]],
                        });
                    }
                    return this._super(...arguments);
                },
                resId: 1,
            });

            await click(form.$('.o_field_widget[name="name"]'));
            await testUtils.fields.editInput($('.o_field_widget[name="name"]'), "readonly");

            assert.containsOnce(form, ".o_data_row", "the one2many should contain one row");

            // open the o2m record in readonly first
            await click(form.$(".o_data_row td:first"));
            assert.containsOnce(document.body, ".modal .o_form_readonly");

            await clickDiscard(target.querySelector(".modal"));
            await clickDiscard(target);

            // switch to edit mode and open it again
            await click(form.$(".o_data_row td:first"));
            await testUtils.nextTick(); // wait for quick edit
            assert.containsOnce(document.body, ".modal .o_form_editable");
            assert.containsOnce(
                document.body,
                ".modal .o_data_row",
                "the one2many should contain one row"
            );

            // open the o2m again, in the dialog
            await click($(".modal .o_data_row td:first"));

            assert.containsN(document.body, ".modal .o_form_editable", 2);

            // edit the name and click save modal that is on top
            await testUtils.fields.editInput(
                $(".modal:nth(1) .o_field_widget[name=display_name]"),
                "new name"
            );
            await click($(".modal:nth(1) .modal-footer .btn-primary"));

            assert.containsOnce(document.body, ".modal .o_form_editable");

            // click save on the other modal
            await click($(".modal .modal-footer .btn-primary"));

            assert.containsNone(document.body, ".modal");

            // save the main record
            await clickSave(target);
        }
    );

    QUnit.skipWOWL("onchange and required fields with override in arch", async function (assert) {
        assert.expect(4);

        serverData.models.partner.onchanges = {
            turtles: function () {},
        };
        serverData.models.turtle.fields.turtle_foo.required = true;
        serverData.models.partner.records[0].turtles = [];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_int"/>
                            <field name="turtle_foo" required="0"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });
        await clickEdit(target);

        // triggers an onchange on partner, because the new record is valid
        await addRow(target);

        assert.verifySteps(["read", "onchange", "onchange"]);
    });

    QUnit.skipWOWL("onchange on a one2many containing a one2many", async function (assert) {
        // the purpose of this test is to ensure that the onchange specs are
        // correctly and recursively computed
        assert.expect(1);

        serverData.models.partner.onchanges = {
            p: function () {},
        };
        var checkOnchange = false;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                            <field name="p">
                                <tree editable="bottom">
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange" && checkOnchange) {
                    assert.strictEqual(
                        args.args[3]["p.p.display_name"],
                        "",
                        "onchange specs should be computed recursively"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        await addRow(target);
        await click($(".modal .o_field_x2many_list_row_add a"));
        await testUtils.fields.editInput($(".modal .o_data_cell input"), "new record");
        checkOnchange = true;
        await clickFirst($(".modal .modal-footer .btn-primary"));
    });

    QUnit.skipWOWL("editing tabbed one2many (editable=bottom)", async function (assert) {
        assert.expect(12);

        serverData.models.partner.records[0].turtles = [];
        for (var i = 0; i < 42; i++) {
            var id = 100 + i;
            serverData.models.turtle.records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
            serverData.models.partner.records[0].turtles.push(id);
        }

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "write") {
                    assert.strictEqual(
                        args.args[1].turtles[40][0],
                        0,
                        "should send a create command"
                    );
                    assert.deepEqual(args.args[1].turtles[40][2], { turtle_foo: "rainbow dash" });
                }
                return this._super.apply(this, arguments);
            },
        });

        await clickEdit(target);
        await addRow(target);

        assert.containsN(form, "tr.o_data_row", 41);
        assert.hasClass(form.$("tr.o_data_row").last(), "o_selected_row");

        await testUtils.fields.editInput(
            form.$('.o_data_row input[name="turtle_foo"]'),
            "rainbow dash"
        );
        await clickSave(target);

        assert.containsN(form, "tr.o_data_row", 40);

        assert.verifySteps(["read", "read", "onchange", "write", "read", "read"]);
    });

    QUnit.skipWOWL("editing tabbed one2many (editable=bottom), again...", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records[0].turtles = [];
        for (var i = 0; i < 9; i++) {
            var id = 100 + i;
            serverData.models.turtle.records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
            serverData.models.partner.records[0].turtles.push(id);
        }

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="3">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        await clickEdit(target);
        // add a new record page 1 (this increases the limit to 4)
        await addRow(target);
        await testUtils.fields.editInput(
            form.$('.o_data_row input[name="turtle_foo"]'),
            "rainbow dash"
        );
        await click(form.$(".o_x2m_control_panel .o_pager_next")); // page 2: 4 records
        await click(form.$(".o_x2m_control_panel .o_pager_next")); // page 3: 2 records

        assert.containsN(form, "tr.o_data_row", 2, "should have 2 data rows on the current page");
    });

    QUnit.skipWOWL("editing tabbed one2many (editable=top)", async function (assert) {
        assert.expect(15);

        serverData.models.partner.records[0].turtles = [];
        serverData.models.turtle.fields.turtle_foo.default = "default foo";
        for (var i = 0; i < 42; i++) {
            var id = 100 + i;
            serverData.models.turtle.records.push({ id: id, turtle_foo: "turtle" + (id - 99) });
            serverData.models.partner.records[0].turtles.push(id);
        }

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "write") {
                    assert.strictEqual(args.args[1].turtles[40][0], 0);
                    assert.deepEqual(args.args[1].turtles[40][2], { turtle_foo: "rainbow dash" });
                }
                return this._super.apply(this, arguments);
            },
        });

        await clickEdit(target);
        await click(form.$(".o_field_widget[name=turtles] .o_pager_next"));

        assert.containsN(form, "tr.o_data_row", 2);

        await addRow(target);

        assert.containsN(form, "tr.o_data_row", 3);

        assert.hasClass(form.$("tr.o_data_row").first(), "o_selected_row");

        assert.strictEqual(
            form.$("tr.o_data_row input").val(),
            "default foo",
            "selected input should have correct string"
        );

        await testUtils.fields.editInput(
            form.$('.o_data_row input[name="turtle_foo"]'),
            "rainbow dash"
        );
        await clickSave(target);

        assert.containsN(form, "tr.o_data_row", 40);

        assert.verifySteps(["read", "read", "read", "onchange", "write", "read", "read"]);
    });

    QUnit.skipWOWL(
        "one2many field: change value before pending onchange returns",
        async function (assert) {
            assert.expect(2);

            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

            serverData.models.partner.onchanges = {
                int_field: function () {},
            };
            var prom;
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="int_field"/>
                                <field name="trululu"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === "onchange") {
                        // delay the onchange RPC
                        return Promise.resolve(prom).then(_.constant(result));
                    }
                    return result;
                },
            });

            await addRow(target);
            prom = testUtils.makeTestPromise();
            await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), "44");

            var $dropdown = form.$(".o_field_many2one input").autocomplete("widget");
            // set trululu before onchange
            await testUtils.fields.editAndTrigger(form.$(".o_field_many2one input"), "first", [
                "keydown",
                "keyup",
            ]);
            // complete the onchange
            prom.resolve();
            assert.strictEqual(
                form.$(".o_field_many2one input").val(),
                "first",
                "should have kept the new value"
            );
            await testUtils.nextTick();
            // check name_search result
            assert.strictEqual(
                $dropdown.find("li:not(.o_m2o_dropdown_option)").length,
                1,
                "autocomplete should contains 1 suggestion"
            );

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        }
    );

    QUnit.skipWOWL(
        "focus is correctly reset after an onchange in an x2many",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.onchanges = {
                int_field: function () {},
            };
            var prom;
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="int_field"/>
                                <button string="hello"/>
                                <field name="qux"/>
                                <field name="trululu"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === "onchange") {
                        // delay the onchange RPC
                        return Promise.resolve(prom).then(_.constant(result));
                    }
                    return result;
                },
            });

            await addRow(target);
            prom = testUtils.makeTestPromise();
            await testUtils.fields.editAndTrigger(form.$(".o_field_widget[name=int_field]"), "44", [
                "input",
                { type: "keydown", which: $.ui.keyCode.TAB },
            ]);
            prom.resolve();
            await testUtils.nextTick();

            assert.strictEqual(
                document.activeElement,
                form.$(".o_field_widget[name=qux]")[0],
                "qux field should have the focus"
            );

            await testUtils.fields.many2one.clickOpenDropdown("trululu");
            await testUtils.fields.many2one.clickHighlightedItem("trululu");
            assert.strictEqual(
                form.$(".o_field_many2one input").val(),
                "first record",
                "the one2many field should have the expected value"
            );
        }
    );

    QUnit.skipWOWL("checkbox in an x2many that triggers an onchange", async function (assert) {
        assert.expect(1);

        serverData.models.partner.onchanges = {
            bar: function () {},
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="bar"/>
                        </tree>
                    </field>
                </form>`,
        });

        await addRow(target);
        // use of owlCompatibilityExtraNextTick because we have a boolean field (owl) inside the
        // x2many, so an update of the x2many requires to wait for 2 animation frames: one
        // for the list to be re-rendered (with the boolean field) and one for the control
        // panel.
        await testUtils.owlCompatibilityExtraNextTick();
        await click(form.$(".o_field_widget[name=bar] input"));
        assert.notOk(
            form.$(".o_field_widget[name=bar] input").prop("checked"),
            "the checkbox should be unticked"
        );
    });

    QUnit.skipWOWL(
        "one2many with default value: edit line to make it invalid",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.fields.p.default = [
                [0, false, { foo: "coucou", int_field: 5, p: [] }],
            ];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="foo"/>
                                <field name="int_field"/>
                            </tree>
                        </field>
                    </form>`,
            });

            // edit the line and enter an invalid value for int_field
            await click(form.$(".o_data_row .o_data_cell:nth(1)"));
            await testUtils.fields.editInput(form.$(".o_field_widget[name=int_field]"), "e");
            await click(form.$el);

            assert.containsOnce(
                form,
                ".o_data_row.o_selected_row",
                "line should not have been removed and should still be in edition"
            );
            assert.containsNone(
                document.body,
                ".modal",
                "a confirmation dialog should not be opened"
            );
            assert.hasClass(
                form.$(".o_field_widget[name=int_field]"),
                "o_field_invalid",
                "should indicate that int_field is invalid"
            );
        }
    );

    QUnit.skipWOWL(
        "default value for nested one2manys (coming from onchange)",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.onchanges.p = function (obj) {
                obj.p = [
                    [5],
                    [0, 0, { turtles: [[5], [4, 1]] }], // link record 1 by default
                ];
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="p">
                                <tree>
                                    <field name="turtles"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "create") {
                        assert.strictEqual(
                            args.args[0].p[0][0],
                            0,
                            "should send a command 0 (CREATE) for p"
                        );
                        assert.deepEqual(
                            args.args[0].p[0][2],
                            { turtles: [[4, 1, false]] },
                            "should send the correct values"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.strictEqual(
                form.$(".o_data_cell").text(),
                "1 record",
                "should correctly display the value of the inner o2m"
            );

            await clickSave(target);
        }
    );

    QUnit.skipWOWL("display correct value after validation error", async function (assert) {
        assert.expect(4);

        serverData.models.partner.onchanges.turtles = function () {};

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    if (args.args[1].turtles[0][2].turtle_foo === "pinky") {
                        // we simulate a validation error.  In the 'real' web client,
                        // the server error will be used by the session to display
                        // an error dialog.  From the point of view of the basic
                        // model, the promise is just rejected.
                        return Promise.reject();
                    }
                }
                if (args.method === "write") {
                    assert.deepEqual(
                        args.args[1].turtles[0],
                        [1, 2, { turtle_foo: "foo" }],
                        'should send the "good" value'
                    );
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: { mode: "edit" },
            resId: 1,
        });

        assert.strictEqual(
            form.$(".o_data_row .o_data_cell:nth(0)").text(),
            "blip",
            "initial text should be correct"
        );

        // click and edit value to 'foo', which will trigger onchange
        await click(form.$(".o_data_row .o_data_cell:nth(0)"));
        await testUtils.fields.editInput(form.$(".o_field_widget[name=turtle_foo]"), "foo");
        await click(form.$el);
        assert.strictEqual(
            form.$(".o_data_row .o_data_cell:nth(0)").text(),
            "foo",
            "field should have been changed to foo"
        );

        // click and edit value to 'pinky', which trigger a failed onchange
        await click(form.$(".o_data_row .o_data_cell:nth(0)"));
        await testUtils.fields.editInput(form.$(".o_field_widget[name=turtle_foo]"), "pinky");
        await click(form.$el);

        assert.strictEqual(
            form.$(".o_data_row .o_data_cell:nth(0)").text(),
            "foo",
            "turtle_foo text should now be set back to foo"
        );

        // we make sure here that when we save, the values are the current
        // values displayed in the field.
        await clickSave(target);
    });

    QUnit.skipWOWL(
        "propagate context to sub views without default_* keys",
        async function (assert) {
            assert.expect(7);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="turtles">
                                <tree editable="bottom">
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                mockRPC(route, args) {
                    assert.strictEqual(
                        args.kwargs.context.flutter,
                        "shy",
                        "view context key should be used for every rpcs"
                    );
                    if (args.method === "onchange") {
                        if (args.model === "partner") {
                            assert.strictEqual(
                                args.kwargs.context.default_flutter,
                                "why",
                                "should have default_* values in context for form view RPCs"
                            );
                        } else if (args.model === "turtle") {
                            assert.notOk(
                                args.kwargs.context.default_flutter,
                                "should not have default_* values in context for subview RPCs"
                            );
                        }
                    }
                    return this._super.apply(this, arguments);
                },
                viewOptions: {
                    context: {
                        flutter: "shy",
                        default_flutter: "why",
                    },
                },
            });
            await addRow(target);
            await testUtils.fields.editInput(form.$('input[name="turtle_foo"]'), "pinky pie");
            await clickSave(target);
        }
    );

    QUnit.skipWOWL(
        "nested one2manys with no widget in list and as invisible list in form",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.records[0].p = [1];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree><field name="turtles"/></tree>
                            <form><field name="turtles" invisible="1"/></form>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(form, ".o_data_row");
            assert.strictEqual(form.$(".o_data_row .o_data_cell").text(), "1 record");

            await click(form.$(".o_data_row"));

            assert.containsOnce(document.body, ".modal .o_form_view");
            assert.containsNone(document.body, ".modal .o_form_view .o_field_one2many");

            // Test possible caching issues
            await clickDiscard(target.querySelector(".modal"));
            await click(form.$(".o_data_row"));

            assert.containsOnce(document.body, ".modal .o_form_view");
            assert.containsNone(document.body, ".modal .o_form_view .o_field_one2many");
        }
    );

    QUnit.skipWOWL("onchange on nested one2manys", async function (assert) {
        assert.expect(6);

        serverData.models.partner.onchanges.display_name = function (obj) {
            if (obj.display_name) {
                obj.p = [
                    [5],
                    [
                        0,
                        0,
                        {
                            display_name: "test",
                            turtles: [[5], [0, 0, { display_name: "test nested" }]],
                        },
                    ],
                ];
            }
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="display_name"/>
                        <field name="p">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree>
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "create") {
                    assert.strictEqual(
                        args.args[0].p[0][0],
                        0,
                        "should send a command 0 (CREATE) for p"
                    );
                    assert.strictEqual(
                        args.args[0].p[0][2].display_name,
                        "test",
                        "should send the correct values"
                    );
                    assert.strictEqual(
                        args.args[0].p[0][2].turtles[0][0],
                        0,
                        "should send a command 0 (CREATE) for turtles"
                    );
                    assert.deepEqual(
                        args.args[0].p[0][2].turtles[0][2],
                        { display_name: "test nested" },
                        "should send the correct values"
                    );
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.fields.editInput(
            form.$(".o_field_widget[name=display_name]"),
            "trigger onchange"
        );

        assert.strictEqual(
            form.$(".o_data_cell").text(),
            "test",
            "should have added the new row to the one2many"
        );

        // open the new subrecord to check the value of the nested o2m, and to
        // ensure that it will be saved
        await click(form.$(".o_data_cell:first"));
        assert.strictEqual(
            $(".modal .o_data_cell").text(),
            "test nested",
            "should have added the new row to the nested one2many"
        );
        await clickFirst($(".modal .modal-footer .btn-primary"));

        await clickSave(target);
    });

    QUnit.skipWOWL("one2many with multiple pages and sequence field", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records[0].turtles = [3, 2, 1];
        serverData.models.partner.onchanges.turtles = function () {};

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree limit="2">
                            <field name="turtle_int" widget="handle"/>
                            <field name="turtle_foo"/>
                            <field name="partner_ids" invisible="1"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        value: {
                            turtles: [
                                [5],
                                [1, 1, { turtle_foo: "from onchange", partner_ids: [[5]] }],
                            ],
                        },
                    });
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: "edit",
            },
        });
        await click(form.$(".o_list_record_remove:first button"));
        assert.strictEqual(
            form.$(".o_data_row").text(),
            "from onchange",
            "onchange has been properly applied"
        );
    });

    QUnit.skipWOWL(
        "one2many with multiple pages and sequence field, part2",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].turtles = [3, 2, 1];
            serverData.models.partner.onchanges.turtles = function () {};

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                                <field name="partner_ids" invisible="1"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        return Promise.resolve({
                            value: {
                                turtles: [
                                    [5],
                                    [1, 1, { turtle_foo: "from onchange id2", partner_ids: [[5]] }],
                                    [1, 3, { turtle_foo: "from onchange id3", partner_ids: [[5]] }],
                                ],
                            },
                        });
                    }
                    return this._super(route, args);
                },
                viewOptions: {
                    mode: "edit",
                },
            });
            await click(form.$(".o_list_record_remove:first button"));
            assert.strictEqual(
                form.$(".o_data_row").text(),
                "from onchange id2from onchange id3",
                "onchange has been properly applied"
            );
        }
    );

    QUnit.skipWOWL(
        "one2many with sequence field, override default_get, bottom when inline",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].turtles = [3, 2, 1];

            serverData.models.turtle.fields.turtle_int.default = 10;

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            // starting condition
            assert.strictEqual($(".o_data_cell").text(), "blipyopkawa");

            // click add a new line
            // save the record
            // check line is at the correct place

            var inputText = "ninja";
            await addRow(target);
            await testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), inputText);
            await clickSave(target);

            assert.strictEqual($(".o_data_cell").text(), "blipyopkawa" + inputText);
        }
    );

    QUnit.skipWOWL(
        "one2many with sequence field, override default_get, top when inline",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].turtles = [3, 2, 1];

            serverData.models.turtle.fields.turtle_int.default = 10;

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="top">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            // starting condition
            assert.strictEqual($(".o_data_cell").text(), "blipyopkawa");

            // click add a new line
            // save the record
            // check line is at the correct place

            var inputText = "ninja";
            await addRow(target);
            await testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), inputText);
            await clickSave(target);

            assert.strictEqual($(".o_data_cell").text(), inputText + "blipyopkawa");
        }
    );

    QUnit.skipWOWL(
        "one2many with sequence field, override default_get, bottom when popup",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records[0].turtles = [3, 2, 1];

            serverData.models.turtle.fields.turtle_int.default = 10;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree>
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                            <form>
                                <field name="turtle_int" invisible="1"/>
                                <field name="turtle_foo"/>
                            </form>
                        </field>
                        </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            // starting condition
            assert.strictEqual($(".o_data_cell").text(), "blipyopkawa");

            // click add a new line
            // save the record
            // check line is at the correct place

            var inputText = "ninja";
            await click($(".o_field_x2many_list_row_add a"));
            await testUtils.fields.editInput($('.o_input[name="turtle_foo"]'), inputText);
            await click($(".modal .modal-footer .btn-primary:first"));

            assert.strictEqual($(".o_data_cell").text(), "blipyopkawa" + inputText);

            await click($(".o_form_button_save"));
            assert.strictEqual($(".o_data_cell").text(), "blipyopkawa" + inputText);
        }
    );

    QUnit.skipWOWL(
        "one2many with sequence field, override default_get, not last page",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].turtles = [3, 2, 1];

            serverData.models.turtle.fields.turtle_int.default = 10;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="turtle_int" widget="handle"/>
                            </tree>
                            <form>
                                <field name="turtle_int"/>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            // click add a new line
            // check turtle_int for new is the current max of the page
            await click($(".o_field_x2many_list_row_add a"));
            assert.strictEqual($('.modal .o_input[name="turtle_int"]').val(), "10");
        }
    );

    QUnit.skipWOWL(
        "one2many with sequence field, override default_get, last page",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].turtles = [3, 2, 1];

            serverData.models.turtle.fields.turtle_int.default = 10;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="4">
                                <field name="turtle_int" widget="handle"/>
                            </tree>
                            <form>
                                <field name="turtle_int"/>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            // click add a new line
            // check turtle_int for new is the current max of the page +1
            await click($(".o_field_x2many_list_row_add a"));
            assert.strictEqual($('.modal .o_input[name="turtle_int"]').val(), "22");
        }
    );

    QUnit.skipWOWL(
        "one2many with sequence field, fetch name_get from empty list, field text",
        async function (assert) {
            // There was a bug where a RPC would fail because no route was set.
            // The scenario is:
            // - create a new parent model, which has a one2many
            // - add at least 2 one2many lines which have:
            //     - a handle field
            //     - a many2one, which is not required, and we will leave it empty
            // - reorder the lines with the handle
            // -> This will call a resequence, which calls a name_get.
            // -> With the bug that would fail, if it's ok the test will pass.

            // This test will also make sure lists with
            // FieldText (turtle_description) can be reordered with a handle.
            // More specifically this will trigger a reset on a FieldText
            // while the field is not in editable mode.
            assert.expect(4);

            serverData.models.turtle.fields.turtle_int.default = 10;
            serverData.models.turtle.fields.product_id.default = 37;
            serverData.models.turtle.fields.not_required_product_id = {
                string: "Product",
                type: "many2one",
                relation: "product",
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                                <field name="not_required_product_id"/>
                                <field name="turtle_description" widget="text"/>
                            </tree>
                        </field>
                    </form>`,
                viewOptions: {
                    mode: "edit",
                },
            });

            // starting condition
            assert.strictEqual($(".o_data_cell:nth-child(2)").text(), "");

            var inputText1 = "relax";
            var inputText2 = "max";
            await addRow(target);
            await testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), inputText1);
            await addRow(target);
            await testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), inputText2);
            await addRow(target);

            assert.strictEqual($(".o_data_cell:nth-child(2)").text(), inputText1 + inputText2);

            var $handles = form.$(".ui-sortable-handle");

            assert.equal($handles.length, 3, "There should be 3 sequence handlers");

            await testUtils.dom.dragAndDrop($handles.eq(1), form.$("tbody tr").first(), {
                position: "top",
            });

            assert.strictEqual($(".o_data_cell:nth-child(2)").text(), inputText2 + inputText1);
        }
    );

    QUnit.skip("one2many with several pages, onchange and default order", async function (assert) {
        // This test reproduces a specific scenario where a one2many is displayed
        // over several pages, and has a default order such that a record that
        // would normally be on page 1 is actually on another page. Moreover,
        // there is an onchange on that one2many which converts all commands 4
        // (LINK_TO) into commands 1 (UPDATE), which is standard in the ORM.
        // This test ensures that the record displayed on page 2 is never fully
        // read.
        assert.expect(8);

        serverData.models.partner.records[0].turtles = [1, 2, 3];
        serverData.models.turtle.records[0].partner_ids = [1];
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                var res = _.map(obj.turtles, function (command) {
                    if (command[0] === 1) {
                        // already an UPDATE command: do nothing
                        return command;
                    }
                    // convert LINK_TO commands to UPDATE commands
                    var id = command[1];
                    var record = _.findWhere(serverData.models.turtle.records, { id: id });
                    return [1, id, _.pick(record, ["turtle_int", "turtle_foo", "partner_ids"])];
                });
                obj.turtles = [[5]].concat(res);
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top" limit="2" default_order="turtle_foo">
                            <field name="turtle_int"/>
                            <field name="turtle_foo" class="foo"/>
                            <field name="partner_ids" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                var ids = args.method === "read" ? " [" + args.args[0] + "]" : "";
                assert.step(args.method + ids);
            },
            resId: 1,
        });

        await click(target, ".o_form_button_edit");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell.foo")].map((el) => el.innerText),
            ["blip", "kawa"]
        );

        // edit turtle_int field of first row
        await click(target.querySelector(".o_data_cell"));
        await editInput(target.querySelector(".o_data_row"), ".o_field_widget[name=turtle_int]", 3);
        await click(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell.foo")].map((el) => el.innerText),
            ["blip", "kawa"]
        );

        assert.verifySteps([
            "read [1]", // main record
            "read [1,2,3]", // one2many (turtle_foo, all records)
            "read [2,3]", // one2many (all fields in view, records of first page)
            "read [2,4]", // many2many inside one2many (partner_ids), first page only
            "onchange",
            "read [1]", // AAB FIXME 4 (draft fixing taskid-2323491):
            // this test's purpose is to assert that this rpc isn't
            // done, but yet it is. Actually, it wasn't before because mockOnChange
            // returned [1] as command list, instead of [[6, false, [1]]], so basically
            // this value was ignored. Now that mockOnChange properly works, the value
            // is taken into account but the basicmodel doesn't care it concerns a
            // record of the second page, and does the read. I don't think we
            // introduced a regression here, this test was simply wrong...
        ]);
    });

    QUnit.test(
        "new record, with one2many with more default values than limit",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="2">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                context: { default_turtles: [1, 2, 3] },
            });
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map(
                    (el) => el.querySelector(".o_data_cell").innerText
                ),
                ["yop", "blip"]
            );

            await clickSave(target);
            assert.deepEqual(
                [...target.querySelectorAll(".o_data_row")].map(
                    (el) => el.querySelector(".o_data_cell").innerText
                ),
                ["yop", "blip"]
            );
        }
    );

    QUnit.skipWOWL(
        "add a new line after limit is reached should behave nicely",
        async function (assert) {
            serverData.models.partner.records[0].turtles = [1, 2, 3];
            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [5],
                        [1, 1, { turtle_foo: "yop" }],
                        [1, 2, { turtle_foo: "blip" }],
                        [1, 3, { turtle_foo: "kawa" }],
                        [0, obj.turtles[3][2], { turtle_foo: "abc" }],
                    ];
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree limit="3" editable="bottom">
                                <field name="turtle_foo" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });
            await click(target, ".o_form_button_edit");
            await click(target, ".o_field_x2many_list_row_add a");
            assert.containsN(target, ".o_data_row", 4);

            await editInput(target, 'div[name="turtle_foo"] .o_input', "a");
            assert.containsN(
                target,
                ".o_data_row",
                4,
                "should still have 4 data rows (the limit is increased to 4)"
            );
        }
    );

    QUnit.skipWOWL(
        "onchange in a one2many with non inline view on an existing record",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.fields.sequence = { string: "Sequence", type: "integer" };
            serverData.models.partner.records[0].sequence = 1;
            serverData.models.partner.records[1].sequence = 2;
            serverData.models.partner.onchanges = { sequence: function () {} };

            serverData.models.partner_type.fields.partner_ids = {
                string: "Partner",
                type: "one2many",
                relation: "partner",
            };
            serverData.models.partner_type.records[0].partner_ids = [1, 2];

            const form = await makeView({
                type: "form",
                model: "partner_type",
                serverData,
                arch: `<form><field name="partner_ids"/></form>`,
                archs: {
                    "partner,false,list": `
                        <tree>
                            <field name="sequence" widget="handle"/>
                            <field name="display_name"/>
                        </tree>`,
                },
                resId: 12,
                mockRPC(route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
                viewOptions: { mode: "edit" },
            });

            // swap 2 lines in the one2many
            await testUtils.dom.dragAndDrop(
                form.$(".ui-sortable-handle:eq(1)"),
                form.$("tbody tr").first(),
                { position: "top" }
            );
            assert.verifySteps(["load_views", "read", "read", "onchange", "onchange"]);
        }
    );

    QUnit.skipWOWL(
        "onchange in a one2many with non inline view on a new record",
        async function (assert) {
            assert.expect(6);

            serverData.models.turtle.onchanges = {
                display_name: function (obj) {
                    if (obj.display_name) {
                        obj.turtle_int = 44;
                    }
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="turtles"/></form>`,
                archs: {
                    "turtle,false,list": `
                        <tree editable="bottom">
                            <field name="display_name"/>
                            <field name="turtle_int"/>
                        </tree>`,
                },
                mockRPC(route, args) {
                    assert.step(args.method || route);
                    return this._super.apply(this, arguments);
                },
            });

            // add a row and trigger the onchange
            await addRow(target);
            await testUtils.fields.editInput(
                form.$(".o_data_row .o_field_widget[name=display_name]"),
                "a name"
            );

            assert.strictEqual(
                form.$(".o_data_row .o_field_widget[name=turtle_int]").val(),
                "44",
                "should have triggered the onchange"
            );

            assert.verifySteps([
                "load_views", // load sub list
                "onchange", // main record
                "onchange", // sub record
                "onchange", // edition of display_name of sub record
            ]);
        }
    );

    QUnit.skipWOWL('add a line, edit it and "Save & New"', async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree><field name="display_name"/></tree>
                        <form><field name="display_name"/></form>
                    </field>
                </form>`,
        });

        assert.containsNone(target, ".o_data_row", "there should be no record in the relation");
        // add a new record
        await click(target, ".o_field_x2many_list_row_add a");
        await editInput(target, ".modal .o_field_widget input", "new record");
        await click(target.querySelector(".modal .modal-footer .btn-primary"));

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row .o_data_cell")].map((el) => el.innerText),
            ["new record"]
        );

        // reopen freshly added record and edit it
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, ".modal .o_field_widget", "new record edited");

        // save it, and choose to directly create another record
        await click(target.querySelectorAll(".modal .modal-footer .btn-primary")[1]);

        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget").innerText,
            "",
            "should have cleared the input"
        );

        await editInput(target, ".modal .o_field_widget input", "another new record");
        await click(target.querySelector(".modal .modal-footer .btn-primary"));

        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row .o_data_cell")].map((el) => el.innerText),
            ["new record", "editedanother new record"]
        );
    });

    // WOWL to unskip after context ref
    QUnit.skipWOWL("o2m add a line custom control create editable", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <control>
                                <create string="Add food" context="" />
                                <create string="Add pizza" context="{'default_display_name': 'pizza'}"/>
                            </control>
                            <control>
                                <create string="Add pasta" context="{'default_display_name': 'pasta'}"/>
                            </control>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                        </form>
                    </field>
                </form>`,
        });

        // new controls correctly added
        const rowAdd = target.querySelectorAll(".o_field_x2many_list_row_add");
        assert.strictEqual(rowAdd.length, 1);
        assert.strictEqual(rowAdd[0].closest("tr").querySelectorAll("td").length, 1);
        assert.deepEqual(
            [...rowAdd[0].querySelectorAll("a")].map((el) => el.innerText),
            ["Add food", "Add pizza", "Add pasta"]
        );

        // click add food
        // check it's empty
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            [""]
        );

        // click add pizza
        // press enter to save the record
        // check it's pizza
        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[1]);
        const input = target.querySelector(
            '.o_field_widget[name="p"] .o_selected_row .o_field_widget[name="display_name"]'
        );
        await input.dispatchEvent(new KeyboardEvent("keydown", { key: "enter" }));
        // click add pasta
        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[2]);
        await clickSave(target);
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["", "pizza", "pasta"]
        );
    });

    // WOWL TODO DAM
    QUnit.skipWOWL("o2m add a line custom control create non-editable", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                        <control>
                            <create string="Add food" context="" />
                            <create string="Add pizza" context="{'default_display_name': 'pizza'}" />
                        </control>
                        <control>
                            <create string="Add pasta" context="{'default_display_name': 'pasta'}" />
                        </control>
                        <field name="display_name"/>
                    </tree>
                    <form>
                        <field name="display_name"/>
                        </form>
                    </field>
                </form>
            `,
        });

        // new controls correctly added
        const rowAdd = target.querySelectorAll(".o_field_x2many_list_row_add");
        assert.strictEqual(rowAdd.length, 1);
        assert.containsN(rowAdd[0].closest("tr"), "td", 2);
        assert.deepEqual(
            [...rowAdd[0].querySelectorAll("a")].map((el) => el.innerText),
            ["Add food", "Add pizza", "Add pasta"]
        );

        // click add food
        // check it's empty
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await click(target.querySelector(".modal .modal-footer .btn-primary"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            [""]
        );

        // click add pizza
        // save the modal
        // check it's pizza
        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[1]);
        await click(target.querySelector(".modal .modal-footer .btn-primary"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["", "pizza"]
        );

        // click add pasta
        // save the whole record
        // check it's pizzapasta
        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[2]);
        await click(target.querySelector(".modal .modal-footer .btn-primary"));
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_cell")].map((el) => el.innerText),
            ["", "pizza", "pasta"]
        );
    });

    QUnit.test("o2m add a line custom control create align with handle", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="int_field" widget="handle"/>
                        </tree>
                    </field>
                </form>`,
        });

        // controls correctly added, at one column offset when handle is present
        const tr = target.querySelector(".o_field_x2many_list_row_add").closest("tr");
        assert.containsN(tr, "td", 2);
        const tds = tr.querySelectorAll("td");
        assert.strictEqual(tds[0].innerText, "");
        assert.strictEqual(tds[1].innerText, "Add a line");
    });

    QUnit.skipWOWL("one2many form view with action button", async function (assert) {
        // once the action button is clicked, the record is reloaded (via the
        // on_close handler, executed because the python method does not return
        // any action, or an ir.action.act_window_close) ; this test ensures that
        // it reloads the fields of the opened view (i.e. the form in this case).
        // See https://github.com/odoo/odoo/issues/24189
        serverData.models.partner.records[0].p = [2];
        serverData.views = {
            "partner_type,false,list": `
                <tree>
                    <field name="display_name"/>
                </tree>
            `,
        };
        const actionService = serviceRegistry.get("action");
        serviceRegistry.add(
            "action",
            {
                dependencies: actionService.dependencies,
                async start(env) {
                    const action = await actionService.start(env);
                    return action;
                },
            },
            { force: true }
        );
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                        </tree>
                        <form>
                            <button type="action" string="Set Timmy"/>
                            <field name="timmy"/>
                        </form>
                    </field>
                </form>`,
            // intercepts: {
            //     execute_action: function (ev) {
            //         data.partner.records[1].display_name = "new name";
            //         data.partner.records[1].timmy = [12];
            //         ev.data.on_closed();
            //     },
            // },
        });
        await clickEdit(target);

        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(target.querySelector(".o_data_cell").innerText, "second record");

        // open one2many record in form view
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".modal .o_form_view");
        assert.containsNone(target, ".modal .o_form_view .o_data_row");

        // click on the action button
        await click(target.querySelector(".modal .o_form_view button"));
        assert.containsOnce(target, ".modal .o_data_row");
        assert.strictEqual(target.querySelector(".modal .o_data_cell").innerText, "gold");

        // save the dialog
        await click(target.querySelector(".modal .modal-footer .btn-primary"));

        assert.strictEqual(target.querySelector(".o_data_cell").text(), "new name");
    });

    QUnit.skipWOWL("onchange affecting inline unopened list view", async function (assert) {
        // when we got onchange result for fields of record that were not
        // already available because they were in a inline view not already
        // opened, in a given configuration the change were applied ignoring
        // existing data, thus a line of a one2many field inside a one2many
        // field could be duplicated unexplectedly
        assert.expect(5);

        var numUserOnchange = 0;

        serverData.models.user.onchanges = {
            partner_ids: function (obj) {
                if (numUserOnchange === 0) {
                    // simulate proper server onchange after save of modal with new record
                    obj.partner_ids = [
                        [5],
                        [
                            1,
                            1,
                            {
                                display_name: "first record",
                                turtles: [[5], [1, 2, { display_name: "donatello" }]],
                            },
                        ],
                        [
                            1,
                            2,
                            {
                                display_name: "second record",
                                turtles: [[5], obj.partner_ids[1][2].turtles[0]],
                            },
                        ],
                    ];
                }
                numUserOnchange++;
            },
        };

        const form = await makeView({
            type: "form",
            model: "user",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="partner_ids">
                                <form>
                                    <field name="turtles">
                                        <tree editable="bottom">
                                            <field name="display_name"/>
                                        </tree>
                                    </field>
                                </form>
                                <tree>
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </group>
                    </sheet>
                </form>`,
            resId: 17,
        });

        // add a turtle on second partner
        await clickEdit(target);
        await click(form.$(".o_data_row:eq(1)"));
        await click($(".modal .o_field_x2many_list_row_add a"));
        $('.modal input[name="display_name"]').val("michelangelo").change();
        await click($(".modal .btn-primary"));
        // open first partner so changes from previous action are applied
        await click(form.$(".o_data_row:eq(0)"));
        await click($(".modal .btn-primary"));
        await clickSave(target);

        assert.strictEqual(
            numUserOnchange,
            2,
            "there should 2 and only 2 onchange from closing the partner modal"
        );

        await click(form.$(".o_data_row:eq(0)"));
        await testUtils.nextTick(); // wait for quick edit
        assert.strictEqual($(".modal .o_data_row").length, 1, "only 1 turtle for first partner");
        assert.strictEqual(
            $(".modal .o_data_row").text(),
            "donatello",
            "first partner turtle is donatello"
        );
        await clickDiscard(target.querySelector(".modal"));

        await click(form.$(".o_data_row:eq(1)"));
        assert.strictEqual($(".modal .o_data_row").length, 1, "only 1 turtle for second partner");
        assert.strictEqual(
            $(".modal .o_data_row").text(),
            "michelangelo",
            "second partner turtle is michelangelo"
        );
        await clickDiscard(target.querySelector(".modal"));
    });

    QUnit.skipWOWL("click on URL should not open the record", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].turtles = [1];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="display_name" widget="email"/>
                            <field name="turtle_foo" widget="url"/>
                        </tree>
                        <form/>
                    </field>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_email_cell a"));
        assert.containsNone(target, ".modal");

        await click(target.querySelector(".o_url_cell a"));
        assert.containsNone(target, ".modal");
    });

    QUnit.skipWOWL("create and edit on m2o in o2m, and press ESCAPE", async function (assert) {
        assert.expect(4);

        await makeLegacyDialogMappingTestEnv();

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="top">
                            <field name="turtle_trululu"/>
                        </tree>
                    </field>
                </form>`,
            archs: {
                "partner,false,form": '<form><field name="display_name"/></form>',
            },
        });

        await addRow(target);

        assert.containsOnce(form, ".o_selected_row", "should have create a new row in edition");

        await testUtils.fields.many2one.createAndEdit("turtle_trululu", "ABC");

        assert.strictEqual(
            $(".modal .o_form_view").length,
            1,
            "should have opened a form view in a dialog"
        );

        await testUtils.fields.triggerKeydown(
            $(".modal .o_form_view .o_field_widget[name=display_name]"),
            "escape"
        );

        assert.strictEqual($(".modal .o_form_view").length, 0, "should have closed the dialog");
        assert.containsOnce(form, ".o_selected_row", "new row should still be present");
    });

    QUnit.skipWOWL(
        "one2many add a line should not crash if orderedResIDs is not set",
        async function (assert) {
            // There is no assertion, the code will just crash before the bugfix.
            assert.expect(0);

            serverData.models.partner.records[0].turtles = [];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <header>
                            <button name="post" type="object" string="Validate" class="oe_highlight"/>
                        </header>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                viewOptions: {
                    mode: "edit",
                },
                intercepts: {
                    execute_action: function (event) {
                        event.data.on_fail();
                    },
                },
            });

            await click($('button[name="post"]'));
            await addRow(target);
        }
    );

    QUnit.skipWOWL(
        "one2many shortcut tab should not crash when there is no input widget",
        async function (assert) {
            assert.expect(2);

            // create a one2many view which has no input (only 1 textarea in this case)
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo" widget="text"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            // add a row, fill it, then trigger the tab shortcut
            await addRow(target);
            await testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), "ninja");
            await testUtils.fields.triggerKeydown(form.$('.o_input[name="turtle_foo"]'), "tab");

            assert.strictEqual(
                form.$(".o_field_text").text(),
                "blipninja",
                "current line should be saved"
            );
            assert.containsOnce(form, "textarea.o_field_text", "new line should be created");
        }
    );

    QUnit.skipWOWL(
        "one2many with onchange, required field, shortcut enter",
        async function (assert) {
            assert.expect(5);

            serverData.models.turtle.onchanges = {
                turtle_foo: function () {},
            };

            var prom;
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === "onchange") {
                        return Promise.resolve(prom).then(_.constant(result));
                    }
                    return result;
                },
                // simulate what happens in the client:
                // the new value isn't notified directly to the model
                fieldDebounce: 5000,
            });

            var value = "hello";

            // add a new line
            await addRow(target);

            // we want to add a delay to simulate an onchange
            prom = testUtils.makeTestPromise();

            // write something in the field
            var $input = form.$('input[name="turtle_foo"]');
            await testUtils.fields.editInput($input, value);
            await testUtils.fields.triggerKeydown($input, "enter");

            // check that nothing changed before the onchange finished
            assert.strictEqual($input.val(), value, "input content shouldn't change");
            assert.containsOnce(form, ".o_data_row", "should still contain only one row");

            // unlock onchange
            prom.resolve();
            await testUtils.nextTick();

            // check the current line is added with the correct content and a new line is editable
            assert.strictEqual(form.$("td.o_data_cell").text(), value);
            assert.strictEqual(form.$('input[name="turtle_foo"]').val(), "");
            assert.containsN(form, ".o_data_row", 2, "should now contain two rows");
        }
    );

    QUnit.skipWOWL(
        "no deadlock when leaving a one2many line with uncommitted changes",
        async function (assert) {
            // Before unselecting a o2m line, field widgets are asked to commit their changes (new values
            // that they wouldn't have sent to the model yet). This test is added alongside a bug fix
            // ensuring that we don't end up in a deadlock when a widget actually has some changes to
            // commit at that moment.
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
                // we set a fieldDebounce to precisely mock the behavior of the webclient: changes are
                // not sent to the model at keystrokes, but when the input is left

                // legacyParams: { fieldDebounce: 5000 }, // WOWL keep this in view API?
            });

            await addRow(target);

            await editInput(target, ".o_field_widget[name=turtles] input", "some foo value");

            // click to add a second row to unselect the current one, then save
            await addRow(target);
            await clickSave(target);

            assert.containsOnce(target, ".o_form_readonly");
            assert.strictEqual(
                target.querySelector(".o_data_row").innerText.trim(),
                "some foo value"
            );
            assert.verifySteps([
                "onchange", // main record
                "onchange", // line 1
                "onchange", // line 2
                "create",
                "read", // main record
                "read", // line 1
            ]);
        }
    );

    QUnit.skipWOWL("one2many with extra field from server not in form", async function (assert) {
        assert.expect(6);

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="display_name"/>
                </form>
            `,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="datetime"/>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    args.args[1].p[0][2].datetime = "2018-04-05 12:00:00";
                }
            },
        });

        await clickEdit(target);

        // Add a record in the list
        await addRow(target);

        await editInput(target, ".modal div[name=display_name] input", "michelangelo");

        // Save the record in the modal (though it is still virtual)
        await click(target.querySelector(".modal .btn-primary"));

        assert.containsOnce(target, ".o_data_row");

        let cells = target.querySelectorAll(".o_data_cell");

        assert.equal(cells[0].innerText, "");
        assert.equal(cells[1].innerText, "michelangelo");

        // Save the whole thing
        await clickSave(target);

        // x2mList = target.querySelectorAll(".o_field_x2many_list[name=p]");

        // // Redo asserts in RO mode after saving
        // assert.equal(
        //     x2mList.find(".o_data_row").length,
        //     1,
        //     "There should be 1 records in the x2m list"
        // );

        // newlyAdded = x2mList.find(".o_data_row").eq(0);

        // cells = newlyAdded.querySelectorAll(".o_data_cell");
        // assert.equal(cells[0].innerText,"04/05/2018 12:00:00");
        // assert.equal(cells[1].innerText,"michelangelo");
    });

    QUnit.skipWOWL("one2many invisible depends on parent field", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="product_id"/>
                        </group>
                        <notebook>
                            <page string="Partner page">
                                <field name="bar"/>
                                <field name="p">
                                    <tree>
                                        <field name="foo" attrs="{'column_invisible': [('parent.product_id', '!=', False)]}"/>
                                        <field name="bar" attrs="{'column_invisible': [('parent.bar', '=', False)]}"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many"
        );
        await clickEdit(target);
        await click(form.$('.o_field_many2one[name="product_id"] input'));
        await click($("li.ui-menu-item a:contains(xpad)").trigger("mouseenter"));
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
        await click(form.$('.o_field_boolean[name="bar"] input'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column after the value change"
        );
    });

    QUnit.skipWOWL(
        "column_invisible attrs on a button in a one2many list",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.records[0].p = [2];
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="product_id"/>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <button name="abc" string="Do it" class="some_button" attrs="{'column_invisible': [('parent.product_id', '=', False)]}"/>
                        </tree>
                    </field>
                </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.strictEqual(form.$(".o_field_widget[name=product_id] input").val(), "");
            assert.containsN(form, ".o_list_table th", 2); // foo + trash bin
            assert.containsNone(form, ".some_button");

            await testUtils.fields.many2one.clickOpenDropdown("product_id");
            await testUtils.fields.many2one.clickHighlightedItem("product_id");

            assert.strictEqual(form.$(".o_field_widget[name=product_id] input").val(), "xphone");
            assert.containsN(form, ".o_list_table th", 3); // foo + button + trash bin
            assert.containsOnce(form, ".some_button");
        }
    );

    QUnit.skipWOWL("column_invisible attrs on adjacent buttons", async function (assert) {
        assert.expect(14);

        serverData.models.partner.records[0].p = [2];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="product_id"/>
                    <field name="trululu"/>
                    <field name="p">
                        <tree>
                            <button name="abc1" string="Do it 1" class="some_button1"/>
                            <button name="abc2" string="Do it 2" class="some_button2" attrs="{'column_invisible': [('parent.product_id', '!=', False)]}"/>
                            <field name="foo"/>
                            <button name="abc3" string="Do it 3" class="some_button3" attrs="{'column_invisible': [('parent.product_id', '!=', False)]}"/>
                            <button name="abc4" string="Do it 4" class="some_button4" attrs="{'column_invisible': [('parent.trululu', '!=', False)]}"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            viewOptions: {
                mode: "edit",
            },
        });

        assert.strictEqual(form.$(".o_field_widget[name=product_id] input").val(), "");
        assert.strictEqual(form.$(".o_field_widget[name=trululu] input").val(), "aaa");
        assert.containsN(form, ".o_list_table th", 4); // button group 1 + foo + button group 2 + trash bin
        assert.containsOnce(form, ".some_button1");
        assert.containsOnce(form, ".some_button2");
        assert.containsOnce(form, ".some_button3");
        assert.containsNone(form, ".some_button4");

        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickHighlightedItem("product_id");

        assert.strictEqual(form.$(".o_field_widget[name=product_id] input").val(), "xphone");
        assert.strictEqual(form.$(".o_field_widget[name=trululu] input").val(), "aaa");
        assert.containsN(form, ".o_list_table th", 3); // button group 1 + foo + trash bin
        assert.containsOnce(form, ".some_button1");
        assert.containsNone(form, ".some_button2");
        assert.containsNone(form, ".some_button3");
        assert.containsNone(form, ".some_button4");
    });

    QUnit.skipWOWL("field context is correctly passed to x2m subviews", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles" context="{some_key 1}">
                        <kanban>
                            <templates>
                                <t t-name="kanban-box">
                                    <div>
                                        <t t-if="context.some_key">
                                            <field name="turtle_foo"/>
                                        </t>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            form.$(".o_kanban_record:not(.o_kanban_ghost)").length,
            1,
            "should have a record in the relation"
        );
        assert.strictEqual(
            form.$(".o_kanban_record span:contains(blip)").length,
            1,
            "condition in the kanban template should have been correctly evaluated"
        );
    });

    QUnit.skipWOWL("one2many kanban with widget handle", async function (assert) {
        assert.expect(5);

        serverData.models.partner.records[0].turtles = [1, 2, 3];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <kanban>
                            <field name="turtle_int" widget="handle"/>
                                <templates>
                                    <t t-name="kanban-box">
                                        <div><field name="turtle_foo"/></div>
                                    </t>
                                </templates>
                        </kanban>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.deepEqual(args.args[1], {
                        turtles: [
                            [1, 2, { turtle_int: 0 }],
                            [1, 3, { turtle_int: 1 }],
                            [1, 1, { turtle_int: 2 }],
                        ],
                    });
                }
                return this._super.apply(this, arguments);
            },
            resId: 1,
        });

        assert.strictEqual(form.$(".o_kanban_record:not(.o_kanban_ghost)").text(), "yopblipkawa");
        assert.doesNotHaveClass(form.$(".o_field_one2many .o_kanban_view"), "ui-sortable");

        await clickEdit(target);

        assert.hasClass(form.$(".o_field_one2many .o_kanban_view"), "ui-sortable");

        var $record = form.$(
            ".o_field_one2many[name=turtles] .o_kanban_view .o_kanban_record:first"
        );
        var $to = form.$(
            ".o_field_one2many[name=turtles] .o_kanban_view .o_kanban_record:nth-child(3)"
        );
        await testUtils.dom.dragAndDrop($record, $to, { position: "bottom" });

        assert.strictEqual(form.$(".o_kanban_record:not(.o_kanban_ghost)").text(), "blipkawayop");

        await clickSave(target);
    });

    QUnit.skipWOWL("one2many editable list: edit and click on add a line", async function (assert) {
        assert.expect(9);

        serverData.models.turtle.onchanges = {
            turtle_int: function () {},
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom"><field name="turtle_int"/></tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step("onchange");
                }
                return this._super.apply(this, arguments);
            },
            // in this test, we want to to accurately mock what really happens, that is, input
            // fields only trigger their changes on 'change' event, not on 'input'
            fieldDebounce: 100000,
            viewOptions: {
                mode: "edit",
            },
        });

        assert.containsOnce(form, ".o_data_row");

        // edit first row
        await click(form.$(".o_data_row:first .o_data_cell:first"));
        assert.hasClass(form.$(".o_data_row:first"), "o_selected_row");
        await testUtils.fields.editInput(form.$(".o_selected_row input[name=turtle_int]"), "44");

        assert.verifySteps([]);
        // simulate a long click on 'Add a line' (mousedown [delay] mouseup and click events)
        var $addLine = form.$(".o_field_x2many_list_row_add a");
        testUtils.dom.triggerEvents($addLine, "mousedown");
        // mousedown is supposed to trigger the change event on the edited input, but it doesn't
        // in the test environment, for an unknown reason, so we trigger it manually to reproduce
        // what really happens
        testUtils.dom.triggerEvents(form.$(".o_selected_row input[name=turtle_int]"), "change");
        await testUtils.nextTick();

        // release the click
        await testUtils.dom.triggerEvents($addLine, ["mouseup", "click"]);
        assert.verifySteps(["onchange", "onchange"]);

        assert.containsN(form, ".o_data_row", 2);
        assert.strictEqual(form.$(".o_data_row:first").text(), "44");
        assert.hasClass(form.$(".o_data_row:nth(1)"), "o_selected_row");
    });

    QUnit.skipWOWL(
        "many2manys inside a one2many are fetched in batch after onchange",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [5],
                        [
                            1,
                            1,
                            {
                                turtle_foo: "leonardo",
                                partner_ids: [[4, 2]],
                            },
                        ],
                        [
                            1,
                            2,
                            {
                                turtle_foo: "donatello",
                                partner_ids: [
                                    [4, 2],
                                    [4, 4],
                                ],
                            },
                        ],
                    ];
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="turtles">
                            <tree editable="bottom">
                                <field name="turtle_foo"/>
                                <field name="partner_ids" widget="many2many_tags"/>
                            </tree>
                        </field>
                    </form>`,
                enableBasicModelBachedRPCs: true,
                mockRPC(route, args) {
                    assert.step(args.method || route);
                    if (args.method === "read") {
                        assert.deepEqual(
                            args.args[0],
                            [2, 4],
                            "should read the partner_ids once, batched"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.containsN(form, ".o_data_row", 2);
            assert.strictEqual(
                form.$('.o_field_widget[name="partner_ids"]').text().replace(/\s/g, ""),
                "secondrecordsecondrecordaaa"
            );

            assert.verifySteps(["onchange", "read"]);
        }
    );

    QUnit.skipWOWL("two one2many fields with same relation and onchanges", async function (assert) {
        // this test simulates the presence of two one2many fields with onchanges, such that
        // changes to the first o2m are repercuted on the second one
        assert.expect(6);

        serverData.models.partner.fields.turtles2 = {
            string: "Turtles 2",
            type: "one2many",
            relation: "turtle",
            relation_field: "turtle_trululu",
        };
        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                // when we add a line to turtles, add same line to turtles2
                if (obj.turtles.length) {
                    obj.turtles = [[5]].concat(obj.turtles);
                    obj.turtles2 = obj.turtles;
                }
            },
            turtles2: function (obj) {
                // simulate an onchange on turtles2 as well
                if (obj.turtles2.length) {
                    obj.turtles2 = [[5]].concat(obj.turtles2);
                }
            },
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom"><field name="name" required="1"/></tree>
                    </field>
                    <field name="turtles2">
                        <tree editable="bottom"><field name="name" required="1"/></tree>
                    </field>
                </form>`,
        });

        // trigger first onchange by adding a line in turtles field (should add a line in turtles2)
        await click(form.$('.o_field_widget[name="turtles"] .o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput(
            form.$('.o_field_widget[name="turtles"] .o_field_widget[name="name"]'),
            "ABC"
        );

        assert.containsOnce(
            form,
            '.o_field_widget[name="turtles"] .o_data_row',
            "line of first o2m should have been created"
        );
        assert.containsOnce(
            form,
            '.o_field_widget[name="turtles2"] .o_data_row',
            "line of second o2m should have been created"
        );

        // add a line in turtles2
        await click(form.$('.o_field_widget[name="turtles2"] .o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput(
            form.$('.o_field_widget[name="turtles2"] .o_field_widget[name="name"]'),
            "DEF"
        );

        assert.containsOnce(
            form,
            '.o_field_widget[name="turtles"] .o_data_row',
            "we should still have 1 line in turtles"
        );
        assert.containsN(
            form,
            '.o_field_widget[name="turtles2"] .o_data_row',
            2,
            "we should have 2 lines in turtles2"
        );
        assert.hasClass(
            form.$('.o_field_widget[name="turtles2"] .o_data_row:nth(1)'),
            "o_selected_row",
            "second row should be in edition"
        );

        await clickSave(target);

        assert.strictEqual(form.$('.o_field_widget[name="turtles2"] .o_data_row').text(), "ABCDEF");
    });

    QUnit.skipWOWL(
        "column widths are kept when adding first record in o2m",
        async function (assert) {
            assert.expect(2);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="top">
                                <field name="date"/>
                                <field name="foo"/>
                            </tree>
                        </field>
                    </form>`,
            });

            var width = form.$('th[data-name="date"]')[0].offsetWidth;

            await addRow(target);

            assert.containsOnce(form, ".o_data_row");
            assert.strictEqual(form.$('th[data-name="date"]')[0].offsetWidth, width);
        }
    );

    QUnit.skipWOWL("column widths are kept when editing a record in o2m", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].p = [2];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="date"/>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            viewOptions: {
                mode: "edit",
            },
        });

        var width = form.$('th[data-name="date"]')[0].offsetWidth;

        await click(form.$(".o_data_row .o_data_cell:first"));

        assert.strictEqual(form.$('th[data-name="date"]')[0].offsetWidth, width);

        var longVal =
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, " +
            "justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum " +
            "purus bibendum est.";
        await testUtils.fields.editInput(form.$(".o_field_widget[name=foo]"), longVal);

        assert.strictEqual(form.$('th[data-name="date"]')[0].offsetWidth, width);
    });

    QUnit.skipWOWL(
        "column widths are kept when remove last record in o2m",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].p = [2];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="top">
                                <field name="date"/>
                                <field name="foo"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            var width = form.$('th[data-name="date"]')[0].offsetWidth;

            await click(form.$(".o_data_row .o_list_record_remove"));

            assert.strictEqual(form.$('th[data-name="date"]')[0].offsetWidth, width);
        }
    );

    QUnit.skipWOWL(
        "column widths are correct after toggling optional fields",
        async function (assert) {
            assert.expect(2);

            var RamStorageService = AbstractStorageService.extend({
                storage: new RamStorage(),
            });

            serverData.models.partner.records[0].p = [2];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="top">
                                <field name="date" required="1"/>
                                <field name="foo"/>
                                <field name="int_field" optional="1"/>
                            </tree>
                        </field>
                    </form>`,
                services: {
                    local_storage: RamStorageService,
                },
            });

            // date fields have an hardcoded width, which apply when there is no
            // record, and should be kept afterwards
            let width = form.$('th[data-name="date"]')[0].offsetWidth;

            // create a record to store the current widths, but discard it directly to keep
            // the list empty (otherwise, the browser automatically computes the optimal widths)
            await addRow(target);

            assert.strictEqual(form.$('th[data-name="date"]')[0].offsetWidth, width);

            await click(form.$(".o_optional_columns_dropdown_toggle"));
            await click(form.$("div.o_optional_columns div.dropdown-item input"));

            assert.strictEqual(form.$('th[data-name="date"]')[0].offsetWidth, width);
        }
    );

    QUnit.skipWOWL("editable one2many list with oe_read_only button", async function (assert) {
        assert.expect(9);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="turtle_foo"/>
                            <button name="do_it" type="object" class="oe_read_only"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        // should have three visible columns in readonly: foo + readonly button + trash
        assert.containsN(form, ".o_list_view thead th:visible", 3);
        assert.containsN(form, ".o_list_view tbody .o_data_row td:visible", 3);
        assert.containsN(form, ".o_list_view tfoot td:visible", 3);
        assert.containsOnce(form, ".o_list_record_remove_header");

        await clickEdit(target);

        // should have two visible columns in edit: foo + trash
        assert.hasClass(form.$(".o_form_view"), "o_form_editable");
        assert.containsN(form, ".o_list_view thead th:visible", 2);
        assert.containsN(form, ".o_list_view tbody .o_data_row td:visible", 2);
        assert.containsN(form, ".o_list_view tfoot td:visible", 2);
        assert.containsOnce(form, ".o_list_record_remove_header");
    });

    QUnit.skipWOWL(
        "one2many reset by onchange (of another field) while being edited",
        async function (assert) {
            // In this test, we have a many2one and a one2many. The many2one has an onchange that
            // updates the value of the one2many. We set a new value to the many2one (name_create)
            // such that the onchange is delayed. During the name_create, we click to add a new row
            // to the one2many. After a while, we unlock the name_create, which triggers the onchange
            // and resets the one2many. At the end, we want the row to be in edition.
            assert.expect(3);

            const prom = testUtils.makeTestPromise();
            serverData.models.partner.onchanges = {
                trululu: (obj) => {
                    obj.p = [[5]].concat(obj.p);
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="trululu"/>
                        <field name="p">
                            <tree editable="top"><field name="product_id" required="1"/></tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    const result = this._super.apply(this, arguments);
                    if (args.method === "name_create") {
                        return prom.then(() => result);
                    }
                    return result;
                },
            });

            // set a new value for trululu (will delay the onchange)
            await testUtils.fields.many2one.searchAndClickItem("trululu", { search: "new value" });

            // add a row in p
            await addRow(target);
            assert.containsNone(form, ".o_data_row");

            // resolve the name_create to trigger the onchange, and the reset of p
            prom.resolve();
            await testUtils.nextTick();
            // use of owlCompatibilityExtraNextTick because we have two sequential updates of the
            // fieldX2Many: one because of the onchange, and one because of the click on add a line.
            // As an update requires an update of the ControlPanel, which is an Owl Component, and
            // waits for it, we need to wait for two animation frames before seeing the new line in
            // the DOM
            await testUtils.owlCompatibilityExtraNextTick();
            assert.containsOnce(form, ".o_data_row");
            assert.hasClass(form.$(".o_data_row"), "o_selected_row");
        }
    );

    QUnit.skipWOWL(
        "one2many with many2many_tags in list and list in form with a limit",
        async function (assert) {
            // This test is skipped for now, as it doesn't work, and it can't be fixed in the current
            // architecture (without large changes). However, this is unlikely to happen as the default
            // limit is 80, and it would be useless to display so many records with a many2many_tags
            // widget. So it would be nice if we could make it work in the future, but it's no big
            // deal for now.
            serverData.models.partner.records[0].p = [1];
            serverData.models.partner.records[0].turtles = [1, 2, 3];

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p">
                            <tree>
                                <field name="turtles" widget="many2many_tags"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree limit="2">
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_field_widget[name=p] .o_data_row");
            assert.containsN(target, ".o_data_row .o_field_many2manytags .badge", 3);

            await click(target.querySelector(".o_data_row"));

            assert.containsOnce(document.body, ".modal .o_form_view");
            assert.containsN(document.body, ".modal .o_field_widget[name=turtles] .o_data_row", 2);
            assert.isVisible(target.querySelector(".modal .o_field_x2many_list .o_pager"));
            assert.strictEqual(
                target.querySelector(".modal .o_field_x2many_list .o_pager").innerText.trim(),
                "1-2 / 3"
            );
        }
    );

    QUnit.skipWOWL(
        "one2many with many2many_tags in list and list in form, and onchange",
        async function (assert) {
            assert.expect(8);

            serverData.models.partner.onchanges = {
                bar: function (obj) {
                    obj.p = [
                        [5],
                        [
                            0,
                            0,
                            {
                                turtles: [
                                    [5],
                                    [
                                        0,
                                        0,
                                        {
                                            display_name: "new turtle",
                                        },
                                    ],
                                ],
                            },
                        ],
                    ];
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p">
                            <tree>
                                <field name="turtles" widget="many2many_tags"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="bottom">
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
            });

            assert.containsOnce(form, ".o_field_widget[name=p] .o_data_row");
            assert.containsOnce(form, ".o_data_row .o_field_many2manytags .badge");

            await click(form.$(".o_data_row"));

            assert.containsOnce(document.body, ".modal .o_form_view");
            assert.containsOnce(document.body, ".modal .o_field_widget[name=turtles] .o_data_row");
            assert.strictEqual(
                $(".modal .o_field_widget[name=turtles] .o_data_row").text(),
                "new turtle"
            );

            await click($(".modal .o_field_x2many_list_row_add a"));
            assert.containsN(document.body, ".modal .o_field_widget[name=turtles] .o_data_row", 2);
            assert.strictEqual(
                $(".modal .o_field_widget[name=turtles] .o_data_row:first").text(),
                "new turtle"
            );
            assert.hasClass(
                $(".modal .o_field_widget[name=turtles] .o_data_row:nth(1)"),
                "o_selected_row"
            );
        }
    );

    QUnit.skipWOWL(
        "one2many with many2many_tags in list and list in form, and onchange (2)",
        async function (assert) {
            assert.expect(7);

            serverData.models.partner.onchanges = {
                bar: function (obj) {
                    obj.p = [
                        [5],
                        [
                            0,
                            0,
                            {
                                turtles: [
                                    [5],
                                    [
                                        0,
                                        0,
                                        {
                                            display_name: "new turtle",
                                        },
                                    ],
                                ],
                            },
                        ],
                    ];
                },
            };
            serverData.models.turtle.onchanges = {
                turtle_foo: function (obj) {
                    obj.display_name = obj.turtle_foo;
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p">
                            <tree>
                                <field name="turtles" widget="many2many_tags"/>
                            </tree>
                            <form>
                                <field name="turtles">
                                    <tree editable="bottom">
                                        <field name="turtle_foo" required="1"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
            });

            assert.containsOnce(form, ".o_field_widget[name=p] .o_data_row");

            await click(form.$(".o_data_row"));

            assert.containsOnce(document.body, ".modal .o_form_view");

            await click($(".modal .o_field_x2many_list_row_add a"));
            assert.containsN(document.body, ".modal .o_field_widget[name=turtles] .o_data_row", 2);

            await testUtils.fields.editInput($(".modal .o_selected_row input"), "another one");
            await testUtils.modal.clickButton("Save & Close");

            assert.containsNone(document.body, ".modal");

            assert.containsOnce(form, ".o_field_widget[name=p] .o_data_row");
            assert.containsN(form, ".o_data_row .o_field_many2manytags .badge", 2);
            assert.strictEqual(
                form.$(".o_data_row .o_field_many2manytags .o_badge_text").text(),
                "new turtleanother one"
            );
        }
    );

    QUnit.skipWOWL(
        "one2many value returned by onchange with unknown fields",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.onchanges = {
                bar: function (obj) {
                    obj.p = [
                        [5],
                        [
                            0,
                            0,
                            {
                                bar: true,
                                display_name: "coucou",
                                trululu: [2, "second record"],
                                turtles: [[5], [0, 0, { turtle_int: 4 }]],
                            },
                        ],
                    ];
                },
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p" widget="many2many_tags"/>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "create") {
                        assert.deepEqual(args.args[0].p[0][2], {
                            bar: true,
                            display_name: "coucou",
                            trululu: 2,
                            turtles: [[5], [0, 0, { turtle_int: 4 }]],
                        });
                    }
                    return this._super(...arguments);
                },
            });

            assert.containsOnce(form, ".o_field_many2manytags .badge");
            assert.strictEqual(form.$(".o_field_many2manytags .o_badge_text").text(), "coucou");

            await clickSave(target);
        }
    );

    QUnit.skipWOWL("mounted is called only once for x2many control panel", async function (assert) {
        // This test could be removed as soon as the field widgets will be converted in owl.
        // It comes with a fix for a bug that occurred because in some circonstances, 'mounted'
        // is called twice for the x2many control panel.
        // Specifically, this occurs when there is 'pad' widget in the form view, because this
        // widget does a 'setValue' in its 'start', which thus resets the field x2many.
        assert.expect(5);

        const PadLikeWidget = fieldRegistry.get("char").extend({
            start() {
                this._setValue("some value");
            },
        });
        fieldRegistry.add("pad_like", PadLikeWidget);

        let resolveCP;
        const prom = new Promise((r) => {
            resolveCP = r;
        });
        patch(ControlPanel.prototype, "cp_patch_mock", {
            setup() {
                this._super(...arguments);
                owl.onMounted(() => {
                    assert.step("mounted");
                });
                owl.onWillUnmount(() => {
                    assert.step("willUnmount");
                });
            },
            async update() {
                const _super = this._super.bind(this);
                // the issue is a race condition, so we manually delay the update to turn it deterministic
                await prom;
                _super.update(...arguments);
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo" widget="pad_like"/>
                    <field name="p">
                        <tree><field name="display_name"/></tree>
                    </field>
                </form>`,
            viewOptions: {
                withControlPanel: false, // s.t. there is only one CP: the one of the x2many
            },
        });

        assert.verifySteps(["mounted"]);

        resolveCP();
        await testUtils.nextTick();

        assert.verifySteps([]);

        unpatch(ControlPanel.prototype, "cp_patch_mock");
        delete fieldRegistry.map.pad_like;

        assert.verifySteps(["willUnmount"]);
    });

    QUnit.skipWOWL(
        "one2many: internal state is updated after another field changes",
        async function (assert) {
            // The FieldOne2Many is configured such that it is reset at any field change.
            // The MatrixProductConfigurator feature relies on that, and requires that its
            // internal state is correctly updated. This white-box test artificially checks that.
            assert.expect(2);

            let o2m;
            testUtils.mock.patch(FieldOne2Many, {
                init() {
                    this._super(...arguments);
                    o2m = this;
                },
            });

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="p">
                            <tree><field name="display_name"/></tree>
                        </field>
                    </form>`,
            });

            assert.strictEqual(o2m.recordData.display_name, false);

            await testUtils.fields.editInput(form.$(".o_field_widget[name=display_name]"), "val");

            assert.strictEqual(o2m.recordData.display_name, "val");

            testUtils.mock.unpatch(FieldOne2Many);
        }
    );

    QUnit.skipWOWL("nested one2many, onchange, no command value", async function (assert) {
        // This test ensures that we always send all values to onchange rpcs for nested
        // one2manys, even if some field hasn't changed. In this particular test case,
        // a first onchange returns a value for the inner one2many, and a second onchange
        // removes it, thus restoring the field to its initial empty value. From this point,
        // the nested one2many value must still be sent to onchange rpcs (on the main record),
        // as it might be used to compute other fields (so the fact that the nested o2m is empty
        // must be explicit).
        assert.expect(3);

        serverData.models.turtle.fields.o2m = {
            string: "o2m",
            type: "one2many",
            relation: "partner",
            relation_field: "trululu",
        };
        serverData.models.turtle.fields.turtle_bar.default = true;
        serverData.models.partner.onchanges.turtles = function (obj) {};
        serverData.models.turtle.onchanges.turtle_bar = function (obj) {
            if (obj.turtle_bar) {
                obj.o2m = [[5], [0, false, { display_name: "default" }]];
            } else {
                obj.o2m = [[5]];
            }
        };

        let step = 1;
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom">
                            <field name="o2m"/>
                            <field name="turtle_bar"/>
                        </tree>
                    </field>
                </form>`,
            async mockRPC(route, args) {
                if (step === 3 && args.method === "onchange" && args.model === "partner") {
                    assert.deepEqual(args.args[1].turtles[0][2], {
                        turtle_bar: false,
                        o2m: [], // we must send a value for this field
                    });
                }
                const result = await this._super(...arguments);
                if (args.model === "turtle") {
                    // sanity checks; this is what the onchanges on turtle must return
                    if (step === 2) {
                        assert.deepEqual(result.value, {
                            o2m: [[5], [0, false, { display_name: "default" }]],
                            turtle_bar: true,
                        });
                    }
                    if (step === 3) {
                        assert.deepEqual(result.value, {
                            o2m: [[5]],
                        });
                    }
                }
                return result;
            },
        });

        step = 2;
        await click(form.$(".o_field_x2many_list .o_field_x2many_list_row_add a"));
        // use of owlCompatibilityExtraNextTick because we have an x2many field with a boolean field
        // (written in owl), so when we add a line, we sequentially render the list itself
        // (including the boolean field), so we have to wait for the next animation frame, and
        // then we render the control panel (also in owl), so we have to wait again for the
        // next animation frame
        await testUtils.owlCompatibilityExtraNextTick();
        step = 3;
        await click(form.$(".o_data_row .o_field_boolean input"));
    });

    QUnit.skipWOWL("update a one2many from a custom field widget", async function (assert) {
        // In this test, we define a custom field widget to render/update a one2many
        // field. For the update part, we ensure that updating primitive fields of a sub
        // record works. There is no guarantee that updating a relational field on the sub
        // record would work. Deleting a sub record works as well. However, creating sub
        // records isn't supported. There are obviously a lot of limitations, but the code
        // hasn't been designed to support all this. This test simply encodes what can be
        // done, and this comment explains what can't (and won't be implemented in stable
        // versions).
        assert.expect(3);

        serverData.models.partner.records[0].p = [1, 2];
        const MyRelationalField = AbstractField.extend({
            events: {
                "click .update": "_onUpdate",
                "click .delete": "_onDelete",
            },
            async _render() {
                const records = await this._rpc({
                    method: "read",
                    resModel: "partner",
                    args: [this.valueIs],
                });
                this.$el.text(records.map((r) => `${r.display_name}/${r.int_field}`).join(", "));
                this.$el.append($('<button class="update fa fa-edit">'));
                this.$el.append($('<button class="delete fa fa-trash">'));
            },
            _onUpdate() {
                this._setValue({
                    operation: "UPDATE",
                    id: this.value.data[0].id,
                    data: {
                        display_name: "new name",
                        int_field: 44,
                    },
                });
            },
            _onDelete() {
                this._setValue({
                    operation: "DELETE",
                    ids: [this.value.data[0].id],
                });
            },
        });
        fieldRegistry.add("my_relational_field", MyRelationalField);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" widget="my_relational_field"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            form.$(".o_field_widget[name=p]").text(),
            "first record/10, second record/9"
        );

        await click(form.$("button.update"));

        assert.strictEqual(
            form.$(".o_field_widget[name=p]").text(),
            "new name/44, second record/9"
        );

        await click(form.$("button.delete"));

        assert.strictEqual(form.$(".o_field_widget[name=p]").text(), "second record/9");

        delete fieldRegistry.map.my_relational_field;
    });

    QUnit.skipWOWL(
        "Editable list's field widgets call on_attach_callback on row update",
        async function (assert) {
            // We use here a badge widget (owl component, does have a on_attach_callback method) and check its decoration
            // is properly managed in this scenario.
            assert.expect(3);

            serverData.models.partner.records[0].p = [1, 2];
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="int_field"/>
                                <field name="color" widget="badge" decoration-warning="int_field == 9"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.containsN(form, ".o_data_row", 2);
            assert.hasClass(form.$(".o_data_row:nth(1) .o_field_badge"), "bg-warning-light");

            await click(form.$(".o_data_row .o_data_cell:first"));
            await testUtils.owlCompatibilityExtraNextTick();
            await testUtils.fields.editInput(form.$(".o_selected_row .o_field_integer"), "44");
            await testUtils.owlCompatibilityExtraNextTick();

            assert.hasClass(form.$(".o_data_row:nth(1) .o_field_badge"), "bg-warning-light");
        }
    );

    QUnit.skipWOWL(
        "Editable list renderer confirmUpdate method does not create a memory leak by no deleted currently modified row widgets but recreating them anyway.",
        async function (assert) {
            assert.expect(5);

            let count = 0;
            const MyField = AbstractField.extend({
                init() {
                    this._super(...arguments);
                    count++;
                },
                destroy() {
                    this._super(...arguments);
                    count--;
                },
            });
            fieldRegistry.add("myfield", MyField);

            serverData.models.partner.records[0].p = [1, 2];
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="int_field"/>
                                <field name="foo" widget="myfield"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            assert.containsN(form, ".o_data_row", 2);
            assert.strictEqual(count, 2);

            await click(form.$(".o_data_row .o_data_cell:first"));
            assert.strictEqual(count, 2);

            await testUtils.fields.editInput(form.$(".o_selected_row .o_field_integer"), "44");
            assert.strictEqual(count, 2);

            delete fieldRegistry.map.my_field;

            assert.strictEqual(count, 0);
        }
    );

    QUnit.skipWOWL(
        "reordering embedded one2many with handle widget starting with same sequence",
        async function (assert) {
            assert.expect(3);

            serverData.models.turtle = {
                fields: { turtle_int: { string: "int", type: "integer", sortable: true } },
                records: [
                    { id: 1, turtle_int: 1 },
                    { id: 2, turtle_int: 1 },
                    { id: 3, turtle_int: 1 },
                    { id: 4, turtle_int: 2 },
                    { id: 5, turtle_int: 3 },
                    { id: 6, turtle_int: 4 },
                ],
            };
            serverData.models.partner.records[0].turtles = [1, 2, 3, 4, 5, 6];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <notebook>
                                <page string="P page">
                                    <field name="turtles">
                                        <tree default_order="turtle_int">
                                            <field name="turtle_int" widget="handle"/>
                                            <field name="id"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            await clickEdit(target);

            assert.strictEqual(
                form.$("td.o_data_cell:not(.o_handle_cell)").text(),
                "123456",
                "default should be sorted by id"
            );

            // Drag and drop the fourth line in first position
            await testUtils.dom.dragAndDrop(
                form.$(".ui-sortable-handle").eq(3),
                form.$("tbody tr").first(),
                { position: "top" }
            );
            assert.strictEqual(
                form.$("td.o_data_cell:not(.o_handle_cell)").text(),
                "412356",
                "should still have the 6 rows in the correct order"
            );

            await clickSave(target);

            assert.deepEqual(
                _.map(serverData.models.turtle.records, function (turtle) {
                    return _.pick(turtle, "id", "turtle_int");
                }),
                [
                    { id: 1, turtle_int: 2 },
                    { id: 2, turtle_int: 3 },
                    { id: 3, turtle_int: 4 },
                    { id: 4, turtle_int: 1 },
                    { id: 5, turtle_int: 5 },
                    { id: 6, turtle_int: 6 },
                ],
                "should have saved the updated turtle_int sequence"
            );
        }
    );

    // WOWL to unskip after context ref
    QUnit.skipWOWL("combine contexts on o2m field and create tags", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles" context="{'default_turtle_foo': 'hard', 'default_turtle_bar': True}">
                            <tree editable="bottom">
                                <control>
                                    <create name="add_soft_shell_turtle" context="{'default_turtle_foo': 'soft', 'default_turtle_int': 2}"/>
                                </control>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    if (args.model === "turtle") {
                        assert.deepEqual(
                            args.kwargs.context,
                            {
                                default_turtle_foo: "soft",
                                default_turtle_bar: true,
                                default_turtle_int: 2,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            "combined context should have the default_turtle_foo value from the <create>"
                        );
                    }
                }
            },
        });

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
    });

    // The following tests come from relational_fields_tests.js (so there might be issues with serverData)

    QUnit.skipWOWL("search more pager is reset when doing a new search", async function (assert) {
        assert.expect(6);
        serverData.models.partner.fields.datetime.searchable = true;
        serverData.models.partner.records.push(
            ...new Array(170).fill().map((_, i) => ({ id: i + 10, name: "Partner " + i }))
        );
        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="display_name"/>
                </tree>
            `,
            "partner,false,search": `
                <search>
                    <field name="datetime"/>
                    <field name="display_name"/>
                </search>
            `,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="trululu"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        await clickEdit(target);

        await testUtils.fields.many2one.clickOpenDropdown("trululu");
        await testUtils.fields.many2one.clickItem("trululu", "Search");
        await click($(".modal .o_pager_next"));

        assert.strictEqual($(".o_pager_limit").text(), "1173", "there should be 173 records");
        assert.strictEqual($(".o_pager_value").text(), "181-160", "should display the second page");
        assert.strictEqual($("tr.o_data_row").length, 80, "should display 80 record");

        const modal = document.body.querySelector(".modal");
        await cpHelpers.editSearch(modal, "first");
        await cpHelpers.validateSearch(modal);

        assert.strictEqual($(".o_pager_limit").text(), "11", "there should be 1 record");
        assert.strictEqual($(".o_pager_value").text(), "11-1", "should display the first page");
        assert.strictEqual($("tr.o_data_row").length, 1, "should display 1 record");
    });

    QUnit.test("do not call name_get if display_name already known", async function (assert) {
        assert.expect(4);

        serverData.models.partner.fields.product_id.default = 37;
        serverData.models.partner.onchanges = {
            trululu: function (obj) {
                obj.trululu = 1;
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu"/>
                    <field name="product_id"/>
                </form>
            `,
            mockRPC(route, args) {
                assert.step(args.method + " on " + args.model);
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=trululu] input").value,
            "first record"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=product_id] input").value,
            "xphone"
        );
        assert.verifySteps(["onchange on partner"]);
    });

    QUnit.test("x2many default_order multiple fields", async function (assert) {
        serverData.models.partner.records = [
            { int_field: 10, id: 1, display_name: "record1" },
            { int_field: 12, id: 2, display_name: "record2" },
            { int_field: 11, id: 3, display_name: "record3" },
            { int_field: 12, id: 4, display_name: "record4" },
            { int_field: 10, id: 5, display_name: "record5" },
            { int_field: 10, id: 6, display_name: "record6" },
            { int_field: 11, id: 7, display_name: "record7" },
        ];

        serverData.models.partner.records[0].p = [1, 7, 4, 5, 2, 6, 3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" >
                        <tree default_order="int_field,id">
                            <field name="id"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        const recordIdList = [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
            (record) => record.querySelector(".o_data_cell").innerText
        );
        const expectedOrderId = ["1", "5", "6", "3", "7", "2", "4"];
        assert.deepEqual(recordIdList, expectedOrderId);
    });

    QUnit.test("x2many default_order multiple fields with limit", async function (assert) {
        serverData.models.partner.records = [
            { int_field: 10, id: 1, display_name: "record1" },
            { int_field: 12, id: 2, display_name: "record2" },
            { int_field: 11, id: 3, display_name: "record3" },
            { int_field: 12, id: 4, display_name: "record4" },
            { int_field: 10, id: 5, display_name: "record5" },
            { int_field: 10, id: 6, display_name: "record6" },
            { int_field: 11, id: 7, display_name: "record7" },
        ];

        serverData.models.partner.records[0].p = [1, 7, 4, 5, 2, 6, 3];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" >
                        <tree default_order="int_field,id" limit="4">
                            <field name="id"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        const recordIdList = [...target.querySelectorAll(".o_field_x2many_list .o_data_row")].map(
            (record) => record.querySelector(".o_data_cell").innerText
        );
        const expectedOrderId = ["1", "5", "6", "3"];
        assert.deepEqual(recordIdList, expectedOrderId);
    });

    QUnit.skipWOWL("focus when closing many2one modal in many2one modal", async function (assert) {
        assert.expect(12);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="trululu"/></form>`,
            resId: 2,
            archs: {
                "partner,false,form": '<form><field name="trululu"/></form>',
            },
            mockRPC(route, args) {
                if (args.method === "get_formview_id") {
                    return Promise.resolve(false);
                }
                return this._super(route, args);
            },
        });

        // Open many2one modal
        await clickEdit(target);
        await click(form.$(".o_external_button"));

        var $originalModal = $(".modal");
        var $focusedModal = $(document.activeElement).closest(".modal");

        assert.equal($originalModal.length, 1, "There should be one modal");
        assert.equal($originalModal[0], $focusedModal[0], "Modal is focused");
        assert.ok($("body").hasClass("modal-open"), "Modal is said opened");

        // Open many2one modal of field in many2one modal
        await click($originalModal.find(".o_external_button"));
        var $modals = $(".modal");
        $focusedModal = $(document.activeElement).closest(".modal");

        assert.equal($modals.length, 2, "There should be two modals");
        assert.equal($modals[1], $focusedModal[0], "Last modal is focused");
        assert.ok($("body").hasClass("modal-open"), "Modal is said opened");

        // Close second modal
        await click($modals.last().find('button[class="close"]'));
        var $modal = $(".modal");
        $focusedModal = $(document.activeElement).closest(".modal");

        assert.equal($modal.length, 1, "There should be one modal");
        assert.equal($modal[0], $originalModal[0], "First modal is still opened");
        assert.equal($modal[0], $focusedModal[0], "Modal is focused");
        assert.ok($("body").hasClass("modal-open"), "Modal is said opened");

        // Close first modal
        await click($modal.find('button[class="close"]'));
        $modal = $(".modal-dialog.modal-lg");

        assert.equal($modal.length, 0, "There should be no modal");
        assert.notOk($("body").hasClass("modal-open"), "Modal is not said opened");
    });

    QUnit.skipWOWL("one2many from a model that has been sorted", async function (assert) {
        assert.expect(1);

        /* On a standard list view, sort your records by a field
         * Click on a record which contains a x2m with multiple records in it
         * The x2m shouldn't take the orderedBy of the parent record (the one on the form)
         */

        serverData.models.partner.records[0].turtles = [3, 2];
        const form = await makeView({
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
            context: {
                orderedBy: [
                    {
                        name: "foo",
                        asc: false,
                    },
                ],
            },
        });

        assert.strictEqual(
            form.$(".o_field_one2many[name=turtles] .o_data_row").text().trim(),
            "kawablip",
            "The o2m should not have been sorted."
        );
    });

    QUnit.skipWOWL("widget many2many_checkboxes in a subview", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                            <page string="Turtles">
                                <field name="turtles" mode="tree">
                                    <tree>
                                        <field name="id"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            archs: {
                "turtle,false,form": `
                    <form>
                        <field name="partner_ids" widget="many2many_checkboxes"/>
                    </form>`,
            },
            resId: 1,
        });

        await clickEdit(target);
        await click(form.$(".o_data_cell"));
        // edit the partner_ids field by (un)checking boxes on the widget
        var $firstCheckbox = $(".modal .custom-control-input").first();
        await click($firstCheckbox);
        assert.ok($firstCheckbox.prop("checked"), "the checkbox should be ticked");
        var $secondCheckbox = $(".modal .custom-control-input").eq(1);
        await click($secondCheckbox);
        assert.notOk($secondCheckbox.prop("checked"), "the checkbox should be unticked");
    });

    QUnit.skipWOWL("embedded readonly one2many with handle widget", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].turtles = [1, 2, 3];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="turtles" readonly="1">
                            <tree editable="top">
                                <field name="turtle_int" widget="handle"/>
                                <field name="turtle_foo"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            form.$(".o_row_handle").length,
            3,
            "there should be 3 handles (one for each row)"
        );
        assert.strictEqual(
            form.$(".o_row_handle:visible").length,
            0,
            "the handles should be hidden in readonly mode"
        );

        await clickEdit(target);

        assert.strictEqual(form.$(".o_row_handle").length, 3, "the handles should still be there");
        assert.strictEqual(
            form.$(".o_row_handle:visible").length,
            0,
            "the handles should still be hidden (on readonly fields)"
        );
    });

    QUnit.skipWOWL(
        "prevent the dialog in readonly x2many tree view with option no_open True",
        async function (assert) {
            assert.expect(2);
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="turtles">
                                <tree editable="bottom" no_open="True">
                                    <field name="turtle_foo"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                resId: 1,
            });
            assert.containsOnce(
                form,
                '.o_data_row:contains("blip")',
                "There should be one record in x2many list view"
            );
            await click(form.$(".o_data_row:first"));
            assert.strictEqual(
                $(".modal-dialog").length,
                0,
                "There is should be no dialog open on click of readonly list row"
            );
        }
    );

    QUnit.skipWOWL(
        "delete a record while adding another one in a multipage",
        async function (assert) {
            // in a many2one with at least 2 pages, add a new line. Delete the line above it.
            // (the onchange makes it so that the virtualID is inserted in the middle of the currentResIDs.)
            // it should load the next line to display it on the page.
            assert.expect(2);

            serverData.models.partner.records[0].turtles = [2, 3];
            serverData.models.partner.onchanges.turtles = function (obj) {
                obj.turtles = [[5]].concat(obj.turtles);
            };

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="turtles">
                                    <tree editable="bottom" limit="1" decoration-muted="turtle_bar == False">
                                        <field name="turtle_foo"/>
                                        <field name="turtle_bar"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            await clickEdit(target);
            // add a line (virtual record)
            await addRow(target);
            await testUtils.owlCompatibilityExtraNextTick();
            await testUtils.fields.editInput(form.$(".o_input"), "pi");
            // delete the line above it
            await click(form.$(".o_list_record_remove").first());
            await testUtils.owlCompatibilityExtraNextTick();
            // the next line should be displayed below the newly added one
            assert.strictEqual(form.$(".o_data_row").length, 2, "should have 2 records");
            assert.strictEqual(
                form.$(".o_data_row .o_data_cell:first-child").text(),
                "pikawa",
                "should display the correct records on page 1"
            );
        }
    );

    QUnit.skipWOWL("one2many, onchange, edition and multipage...", async function (assert) {
        assert.expect(8);

        serverData.models.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [[5]].concat(obj.turtles);
            },
        };

        serverData.models.partner.records[0].turtles = [1, 2, 3];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree editable="bottom" limit="2">
                            <field name="turtle_foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method + " " + args.model);
                return this._super(route, args);
            },
            viewOptions: {
                mode: "edit",
            },
        });
        await addRow(target);
        await testUtils.fields.editInput(form.$('input[name="turtle_foo"]'), "nora");
        await addRow(target);

        assert.verifySteps([
            "read partner",
            "read turtle",
            "onchange turtle",
            "onchange partner",
            "onchange partner",
            "onchange turtle",
            "onchange partner",
        ]);
    });

    QUnit.skipWOWL(
        "onchange on unloaded record clearing posterious change",
        async function (assert) {
            // when we got onchange result for fields of record that were not
            // already available because they were in a inline view not already
            // opened, in a given configuration the change were applied ignoring
            // posteriously changed data, thus an added/removed/modified line could
            // be reset to the original onchange data
            assert.expect(5);

            var numUserOnchange = 0;

            serverData.models.user.onchanges = {
                partner_ids: function (obj) {
                    // simulate actual server onchange after save of modal with new record
                    if (numUserOnchange === 0) {
                        obj.partner_ids = _.clone(obj.partner_ids);
                        obj.partner_ids.unshift([5]);
                        obj.partner_ids[1][2].turtles.unshift([5]);
                        obj.partner_ids[2] = [
                            1,
                            2,
                            {
                                display_name: "second record",
                                trululu: 1,
                                turtles: [[5]],
                            },
                        ];
                    } else if (numUserOnchange === 1) {
                        obj.partner_ids = _.clone(obj.partner_ids);
                        obj.partner_ids.unshift([5]);
                        obj.partner_ids[1][2].turtles.unshift([5]);
                        obj.partner_ids[2][2].turtles.unshift([5]);
                    }
                    numUserOnchange++;
                },
            };

            const form = await makeView({
                type: "form",
                model: "user",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="partner_ids">
                                    <form>
                                        <field name="trululu"/>
                                        <field name="turtles">
                                            <tree editable="bottom">
                                                <field name="display_name"/>
                                            </tree>
                                        </field>
                                    </form>
                                    <tree>
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </group>
                        </sheet>
                    </form>`,
                resId: 17,
            });

            // open first partner and change turtle name
            await clickEdit(target);
            await click(form.$(".o_data_row:eq(0)"));
            await click($(".modal .o_data_cell:eq(0)"));
            await testUtils.fields.editAndTrigger(
                $('.modal input[name="display_name"]'),
                "Donatello",
                "change"
            );
            await click($(".modal .btn-primary"));

            await click(form.$(".o_data_row:eq(1)"));
            await click($(".modal .o_field_x2many_list_row_add a"));
            await testUtils.fields.editAndTrigger(
                $('.modal input[name="display_name"]'),
                "Michelangelo",
                "change"
            );
            await click($(".modal .btn-primary"));

            assert.strictEqual(
                numUserOnchange,
                2,
                "there should 2 and only 2 onchange from closing the partner modal"
            );

            // check first record still has change
            await click(form.$(".o_data_row:eq(0)"));
            assert.strictEqual(
                $(".modal .o_data_row").length,
                1,
                "only 1 turtle for first partner"
            );
            assert.strictEqual(
                $(".modal .o_data_row").text(),
                "Donatello",
                "first partner turtle is Donatello"
            );
            await clickDiscard(target.querySelector(".modal"));

            // check second record still has changes
            await click(form.$(".o_data_row:eq(1)"));
            assert.strictEqual(
                $(".modal .o_data_row").length,
                1,
                "only 1 turtle for second partner"
            );
            assert.strictEqual(
                $(".modal .o_data_row").text(),
                "Michelangelo",
                "second partner turtle is Michelangelo"
            );
            await clickDiscard(target.querySelector(".modal"));
        }
    );

    QUnit.skipWOWL("quickly switch between pages in one2many list", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].turtles = [1, 2, 3];

        var readDefs = [
            Promise.resolve(),
            testUtils.makeTestPromise(),
            testUtils.makeTestPromise(),
        ];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree limit="1">
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === "read") {
                    var recordID = args.args[0][0];
                    return Promise.resolve(readDefs[recordID - 1]).then(_.constant(result));
                }
                return result;
            },
            resId: 1,
        });

        await click(form.$(".o_field_widget[name=turtles] .o_pager_next"));
        await click(form.$(".o_field_widget[name=turtles] .o_pager_next"));

        readDefs[1].resolve();
        await testUtils.nextTick();
        assert.strictEqual(
            form.$(".o_field_widget[name=turtles] .o_data_cell").text(),
            "donatello"
        );

        readDefs[2].resolve();
        await testUtils.nextTick();

        assert.strictEqual(form.$(".o_field_widget[name=turtles] .o_data_cell").text(), "raphael");
    });

    QUnit.skipWOWL("many2many read, field context is properly sent", async function (assert) {
        assert.expect(4);

        serverData.models.partner.fields.timmy.context = { hello: "world" };
        serverData.models.partner.records[0].timmy = [12];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="timmy" widget="many2many_tags"/></form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "read" && args.model === "partner_type") {
                    assert.step(args.kwargs.context.hello);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(["world"]);

        await clickEdit(target);
        var $m2mInput = form.$(".o_field_many2manytags input");
        $m2mInput.click();
        await testUtils.nextTick();
        $m2mInput.autocomplete("widget").find("li:first()").click();
        await testUtils.nextTick();
        assert.verifySteps(["world"]);
    });

    QUnit.skipWOWL("one2many with extra field from server not in form", async function (assert) {
        assert.expect(6);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="datetime"/>
                            <field name="display_name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            archs: {
                "partner,false,form": `<form> <field name="display_name"/> </form>`,
            },
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    args.args[1].p[0][2].datetime = "2018-04-05 12:00:00";
                }
                return this._super.apply(this, arguments);
            },
        });

        await clickEdit(target);

        var x2mList = form.$(".o_field_x2many_list[name=p]");

        // Add a record in the list
        await click(x2mList.find(".o_field_x2many_list_row_add a"));

        var modal = $(".modal-lg");

        var nameInput = modal.find("input.o_input[name=display_name]");
        await testUtils.fields.editInput(nameInput, "michelangelo");

        // Save the record in the modal (though it is still virtual)
        await click(modal.find(".btn-primary").first());

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
        await clickSave(target);

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
    });

    QUnit.skipWOWL("one2many invisible depends on parent field", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="product_id"/>
                        </group>
                        <notebook>
                            <page string="Partner page">
                                <field name="bar"/>
                                <field name="p">
                                    <tree>
                                        <field name="foo" attrs="{'column_invisible': [('parent.product_id', '!=', False)]}"/>
                                        <field name="bar" attrs="{'column_invisible': [('parent.bar', '=', False)]}"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many"
        );
        await clickEdit(target);
        await testUtils.fields.many2one.clickOpenDropdown("product_id");
        await testUtils.fields.many2one.clickHighlightedItem("product_id");
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
        await click(form.$('.o_field_boolean[name="bar"] input'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column after the value change"
        );
    });

    QUnit.test(
        "one2many column visiblity depends on onchange of parent field",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[0].bar = false;

            serverData.models.partner.onchanges.p = function (obj) {
                // set bar to true when line is added
                if (obj.p.length > 1 && obj.p[1][2].foo === "New line") {
                    obj.bar = true;
                }
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="bar"/>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="foo"/>
                                <field name="int_field" attrs="{'column_invisible': [('parent.bar', '=', False)]}"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 1,
            });

            // bar is false so there should be 1 column
            assert.containsOnce(target, ".o_list_renderer th:not(.o_list_record_remove_header)");
            assert.containsOnce(target, ".o_list_renderer .o_data_row");

            await clickEdit(target);

            // add a new o2m record
            await addRow(target);
            target.querySelector(".o_field_one2many input").focus(); // useless?
            await editInput(target, ".o_field_one2many input", "New line");
            await click(target, ".o_form_view");

            assert.containsN(target, ".o_list_renderer th:not(.o_list_record_remove_header)", 2);
        }
    );

    QUnit.skipWOWL("one2many column_invisible on view not inline", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].p = [2];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="product_id"/>
                        </group>
                        <notebook>
                            <page string="Partner page">
                                <field name="bar"/>
                                <field name="p"/>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
            archs: {
                "partner,false,list": `
                    <tree>
                        <field name="foo" attrs="{'column_invisible': [('parent.product_id', '!=', False)]}"/>
                        <field name="bar" attrs="{'column_invisible': [('parent.bar', '=', False)]}"/>
                    </tree>`,
            },
        });
        assert.containsN(
            form,
            "th:not(.o_list_record_remove_header)",
            2,
            "should be 2 columns in the one2many"
        );
        await clickEdit(target);
        await click(form.$('.o_field_many2one[name="product_id"] input'));
        await testUtils.fields.many2one.clickHighlightedItem("product_id");
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
        await click(form.$('.o_field_boolean[name="bar"] input'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(
            form,
            "th:not(.o_list_record_remove_header)",
            "should be 1 column after the value change"
        );
    });

    QUnit.skipWOWL(
        "one2many field in edit mode with optional fields and trash icon",
        async function (assert) {
            assert.expect(13);

            var RamStorageService = AbstractStorageService.extend({
                storage: new RamStorage(),
            });

            serverData.models.partner.records[0].p = [2];
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="p"/></form>`,
                resId: 1,
                archs: {
                    "partner,false,list": `
                        <tree editable="top">
                            <field name="foo" optional="show"/>
                            <field name="bar" optional="hide"/>
                        </tree>`,
                },
                services: {
                    local_storage: RamStorageService,
                },
            });

            // should have 2 columns 1 for foo and 1 for advanced dropdown
            assert.containsN(
                form.$(".o_field_one2many"),
                "th:not(.o_list_record_remove_header)",
                1,
                "should be 1 th in the one2many in readonly mode"
            );
            assert.containsOnce(
                form.$(".o_field_one2many table"),
                ".o_optional_columns_dropdown_toggle",
                "should have the optional columns dropdown toggle inside the table"
            );
            await clickEdit(target);
            // should have 2 columns 1 for foo and 1 for trash icon, dropdown is displayed
            // on trash icon cell, no separate cell created for trash icon and advanced field dropdown
            assert.containsN(
                form.$(".o_field_one2many"),
                "th",
                2,
                "should be 2 th in the one2many edit mode"
            );
            assert.containsN(
                form.$(".o_field_one2many"),
                ".o_data_row:first > td",
                2,
                "should be 2 cells in the one2many in edit mode"
            );

            await click(form.$(".o_field_one2many table .o_optional_columns_dropdown_toggle"));
            assert.containsN(
                form.$(".o_field_one2many"),
                "div.o_optional_columns div.dropdown-item:visible",
                2,
                "dropdown have 2 advanced field foo with checked and bar with unchecked"
            );
            await click(form.$("div.o_optional_columns div.dropdown-item:eq(1) input"));
            assert.containsN(
                form.$(".o_field_one2many"),
                "th",
                3,
                "should be 3 th in the one2many after enabling bar column from advanced dropdown"
            );

            await click(form.$("div.o_optional_columns div.dropdown-item:first input"));
            assert.containsN(
                form.$(".o_field_one2many"),
                "th",
                2,
                "should be 2 th in the one2many after disabling foo column from advanced dropdown"
            );

            assert.containsN(
                form.$(".o_field_one2many"),
                "div.o_optional_columns div.dropdown-item:visible",
                2,
                "dropdown is still open"
            );
            await addRow(target);
            // use of owlCompatibilityExtraNextTick because the x2many field is reset, meaning that
            // 1) its list renderer is updated (updateState is called): this is async and as it
            // contains a FieldBoolean, which is written in Owl, it completes in the nextAnimationFrame
            // 2) when this is done, the control panel is updated: as it is written in owl, this is
            // done in the nextAnimationFrame
            // -> we need to wait for 2 nextAnimationFrame to ensure that everything is fine
            await testUtils.owlCompatibilityExtraNextTick();
            assert.containsN(
                form.$(".o_field_one2many"),
                "div.o_optional_columns div.dropdown-item:visible",
                0,
                "dropdown is closed"
            );
            var $selectedRow = form.$(".o_field_one2many tr.o_selected_row");
            assert.strictEqual(
                $selectedRow.length,
                1,
                "should have selected row i.e. edition mode"
            );

            await click(form.$(".o_field_one2many table .o_optional_columns_dropdown_toggle"));
            await click(form.$("div.o_optional_columns div.dropdown-item:first input"));
            $selectedRow = form.$(".o_field_one2many tr.o_selected_row");
            assert.strictEqual(
                $selectedRow.length,
                0,
                "current edition mode discarded when selecting advanced field"
            );
            assert.containsN(
                form.$(".o_field_one2many"),
                "th",
                3,
                "should be 3 th in the one2many after re-enabling foo column from advanced dropdown"
            );

            // check after form reload advanced column hidden or shown are still preserved
            await form.reload();
            assert.containsN(
                form.$(".o_field_one2many .o_list_view"),
                "th",
                3,
                "should still have 3 th in the one2many after reloading whole form view"
            );
        }
    );

    QUnit.module("TabNavigation");

    QUnit.skipWOWL(
        "when Navigating to a many2one with tabs, it receives the focus and adds a new line",
        async function (assert) {
            assert.expect(3);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                viewOptions: {
                    mode: "edit",
                },
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="qux"/>
                            </group>
                            <notebook>
                                <page string="Partner page">
                                    <field name="turtles">
                                        <tree editable="bottom">
                                            <field name="turtle_foo"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            assert.strictEqual(
                form.$el.find('input[name="qux"]')[0],
                document.activeElement,
                "initially, the focus should be on the 'qux' field because it is the first input"
            );
            await testUtils.fields.triggerKeydown(form.$el.find('input[name="qux"]'), "tab");
            assert.strictEqual(
                assert.strictEqual(
                    form.$el.find('input[name="turtle_foo"]')[0],
                    document.activeElement,
                    "after tab, the focus should be on the many2one on the first input of the newly added line"
                )
            );
        }
    );

    QUnit.skipWOWL(
        "when Navigating to a many to one with tabs, it places the focus on the first visible field",
        async function (assert) {
            assert.expect(3);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                viewOptions: {
                    mode: "edit",
                },
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="qux"/>
                            </group>
                            <notebook>
                                <page string="Partner page">
                                    <field name="turtles">
                                        <tree editable="bottom">
                                            <field name="turtle_foo"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            assert.strictEqual(
                form.$el.find('input[name="qux"]')[0],
                document.activeElement,
                "initially, the focus should be on the 'qux' field because it is the first input"
            );
            form.$el.find('input[name="qux"]').trigger(
                $.Event("keydown", {
                    which: $.ui.keyCode.TAB,
                    keyCode: $.ui.keyCode.TAB,
                })
            );
            await testUtils.owlCompatibilityExtraNextTick();
            await click(document.activeElement);
            assert.strictEqual(
                assert.strictEqual(
                    form.$el.find('input[name="turtle_foo"]')[0],
                    document.activeElement,
                    "after tab, the focus should be on the many2one"
                )
            );
        }
    );

    QUnit.skipWOWL(
        "when Navigating to a many2one with tabs, not filling any field and hitting tab, we should not add a first line but navigate to the next control",
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.records[0].turtles = [];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                viewOptions: {
                    mode: "edit",
                },
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="qux"/>
                            </group>
                            <notebook>
                                <page string="Partner page">
                                    <field name="turtles">
                                        <tree editable="bottom">
                                            <field name="turtle_foo"/>
                                            <field name="turtle_description"/>
                                        </tree>
                                    </field>
                                </page>
                            </notebook>
                            <group>
                                <field name="foo"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            assert.strictEqual(
                form.$el.find('input[name="qux"]')[0],
                document.activeElement,
                "initially, the focus should be on the 'qux' field because it is the first input"
            );
            await testUtils.fields.triggerKeydown(form.$el.find('input[name="qux"]'), "tab");

            // skips the first field of the one2many
            await testUtils.fields.triggerKeydown($(document.activeElement), "tab");
            // skips the second (and last) field of the one2many
            await testUtils.fields.triggerKeydown($(document.activeElement), "tab");
            assert.strictEqual(
                assert.strictEqual(
                    form.$el.find('input[name="foo"]')[0],
                    document.activeElement,
                    "after tab, the focus should be on the many2one"
                )
            );
        }
    );

    QUnit.skipWOWL(
        "when Navigating to a many to one with tabs, editing in a popup, the popup should receive the focus then give it back",
        async function (assert) {
            assert.expect(3);

            await makeLegacyDialogMappingTestEnv();

            serverData.models.partner.records[0].turtles = [];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                viewOptions: {
                    mode: "edit",
                },
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="qux"/>
                            </group>
                                <notebook>
                                    <page string="Partner page">
                                        <field name="turtles">
                                            <tree>
                                                <field name="turtle_foo"/>
                                                <field name="turtle_description"/>
                                            </tree>
                                        </field>
                                    </page>
                                </notebook>
                            <group>
                                <field name="foo"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
                archs: {
                    "turtle,false,form": `
                        <form>
                            <group>
                                <field name="turtle_foo"/>
                                <field name="turtle_int"/>
                            </group>
                        </form>`,
                },
            });

            assert.strictEqual(
                form.$el.find('input[name="qux"]')[0],
                document.activeElement,
                "initially, the focus should be on the 'qux' field because it is the first input"
            );
            await testUtils.fields.triggerKeydown(form.$el.find('input[name="qux"]'), "tab");
            assert.strictEqual(
                $.find('input[name="turtle_foo"]')[0],
                document.activeElement,
                "when the one2many received the focus, the popup should open because it automatically adds a new line"
            );

            await testUtils.fields.triggerKeydown($('input[name="turtle_foo"]'), "escape");
            assert.strictEqual(
                form.$el.find(".o_field_x2many_list_row_add a")[0],
                document.activeElement,
                "after escape, the focus should be back on the add new line link"
            );
        }
    );

    QUnit.skipWOWL(
        "when creating a new many2one on a x2many then discarding it immediately with ESCAPE, it should not crash",
        async function (assert) {
            assert.expect(1);

            serverData.models.partner.records[0].turtles = [];

            const form = await makeView({
                type: "form",
                resModel: "partner",
                viewOptions: {
                    mode: "edit",
                },
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="turtles">
                                <tree editable="top">
                                    <field name="turtle_foo"/>
                                    <field name="turtle_trululu"/>
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                resId: 1,
                archs: {
                    "partner,false,form":
                        '<form><group><field name="foo"/><field name="bar"/></group></form>',
                },
            });

            // add a new line
            await click(form.$el.find(".o_field_x2many_list_row_add>a"));

            // open the field turtle_trululu (one2many)
            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;
            await click(form.$el.find(".o_input_dropdown>input"));

            await testUtils.fields.editInput(form.$(".o_field_many2one input"), "ABC");
            // click create and edit
            await click(
                $(".ui-autocomplete .ui-menu-item a:contains(Create and)").trigger("mouseenter")
            );

            // hit escape immediately
            var escapeKey = $.ui.keyCode.ESCAPE;
            $(document.activeElement).trigger(
                $.Event("keydown", { which: escapeKey, keyCode: escapeKey })
            );

            assert.ok("did not crash");
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        }
    );

    QUnit.skipWOWL(
        "navigating through an editable list with custom controls [REQUIRE FOCUS]",
        async function (assert) {
            assert.expect(5);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="p">
                            <tree editable="bottom">
                                <control>
                                    <create string="Custom 1" context="{'default_foo': '1'}"/>
                                    <create string="Custom 2" context="{'default_foo': '2'}"/>
                                </control>
                                <field name="foo"/>
                            </tree>
                        </field>
                        <field name="int_field"/>
                    </form>`,
                viewOptions: {
                    mode: "edit",
                },
            });

            assert.strictEqual(
                document.activeElement,
                form.$('.o_field_widget[name="display_name"]')[0],
                "first input should be focused by default"
            );

            // press tab to navigate to the list
            await testUtils.fields.triggerKeydown(
                form.$('.o_field_widget[name="display_name"]'),
                "tab"
            );
            // press ESC to cancel 1st control click (create)
            await testUtils.fields.triggerKeydown(form.$(".o_data_cell input"), "escape");
            assert.strictEqual(
                document.activeElement,
                form.$(".o_field_x2many_list_row_add a:first")[0],
                "first editable list control should now have the focus"
            );

            // press right to focus the second control
            await testUtils.fields.triggerKeydown(
                form.$(".o_field_x2many_list_row_add a:first"),
                "right"
            );
            assert.strictEqual(
                document.activeElement,
                form.$(".o_field_x2many_list_row_add a:nth(1)")[0],
                "second editable list control should now have the focus"
            );

            // press left to come back to first control
            await testUtils.fields.triggerKeydown(
                form.$(".o_field_x2many_list_row_add a:nth(1)"),
                "left"
            );
            assert.strictEqual(
                document.activeElement,
                form.$(".o_field_x2many_list_row_add a:first")[0],
                "first editable list control should now have the focus"
            );

            // press tab to leave the list
            await testUtils.fields.triggerKeydown(
                form.$(".o_field_x2many_list_row_add a:first"),
                "tab"
            );
            assert.strictEqual(
                document.activeElement,
                form.$('.o_field_widget[name="int_field"]')[0],
                "last input should now be focused"
            );
        }
    );

    QUnit.skipWOWL(
        "add_record in an o2m with an OWL field: wait mounted before success",
        async function (assert) {
            assert.expect(7);

            let testInst = 0;
            class TestField extends AbstractFieldOwl {
                setup() {
                    super.setup();
                    const ID = testInst++;
                    owl.onMounted(() => {
                        assert.step(`mounted ${ID}`);
                    });

                    owl.onWillUnmount(() => {
                        assert.step(`willUnmount ${ID}`);
                    });
                }
                activate() {
                    return true;
                }
            }

            TestField.template = owl.xml`<span>test</span>`;
            fieldRegistryOwl.add("test_field", TestField);

            const def = testUtils.makeTestPromise();
            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="name" widget="test_field"/>
                            </tree>
                        </field>
                    </form>`,
                viewOptions: {
                    mode: "edit",
                },
            });

            const list = form.renderer.allFieldWidgets[form.handle][0];

            list.trigger_up("add_record", {
                context: [
                    {
                        default_name: "this is a test",
                    },
                ],
                allowWarning: true,
                forceEditable: "bottom",
                onSuccess: function () {
                    assert.step("onSuccess");
                    def.resolve();
                },
            });

            await testUtils.nextTick();
            await def;
            assert.verifySteps(["mounted 0", "willUnmount 0", "mounted 1", "onSuccess"]);
            assert.verifySteps(["willUnmount 1"]);
        }
    );
});
