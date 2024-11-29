import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { Deferred, animationFrame, runAllTimers } from "@odoo/hoot-mock";

import {
    Command,
    MockServer,
    clickKanbanRecord,
    clickModalButton,
    clickSave,
    clickViewButton,
    contains,
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

describe.current.tags("desktop");

class Partner extends models.Model {
    _name = "partner";

    name = fields.Char();
    foo = fields.Char({ default: "My little Foo Value" });
    bar = fields.Boolean({ default: true });
    int_field = fields.Integer();
    p = fields.Many2many({ relation: "partner", relation_field: "trululu" });
    turtles = fields.One2many({ relation: "turtle", relation_field: "turtle_trululu" });
    trululu = fields.Many2one({ relation: "partner" });
    timmy = fields.Many2many({ relation: "partner.type", string: "pokemon" });
    product_id = fields.Many2one({ relation: "product.product" });
    color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
    });
    date = fields.Date();
    datetime = fields.Datetime();
    user_id = fields.Many2one({ relation: "res.users" });
    reference = fields.Reference({
        selection: [
            ["product.product", "Product"],
            ["partner.type", "Partner Type"],
            ["partner", "Partner"],
        ],
    });

    _records = [
        {
            id: 1,
            name: "first record",
            foo: "yop",
            int_field: 10,
            turtles: [2],
            trululu: 3,
            user_id: 1,
            reference: "product.product,1",
        },
        {
            id: 2,
            name: "second record",
            foo: "blip",
            int_field: 9,
            trululu: 1,
            product_id: 1,
            date: "2017-01-25",
            datetime: "2016-12-12 10:55:05",
            user_id: 1,
        },
        {
            id: 3,
            name: "aaa",
            bar: false,
        },
    ];
}

class PartnerType extends models.Model {
    color = fields.Integer({ string: "Color index" });
    name = fields.Char();

    _records = [
        {
            id: 1,
            name: "gold",
            color: 2,
        },
        {
            id: 2,
            name: "silver",
            color: 5,
        },
    ];
}

class Product extends models.Model {
    _name = "product.product";

    name = fields.Char();

    _records = [
        {
            id: 1,
            name: "xphone",
        },
        {
            id: 2,
            name: "xpad",
        },
    ];
}

class Turtle extends models.Model {
    _name = "turtle";

    name = fields.Char();
    turtle_foo = fields.Char();
    turtle_bar = fields.Boolean({ default: true });
    turtle_int = fields.Integer();
    turtle_trululu = fields.Many2one({ relation: "partner" });
    turtle_ref = fields.Reference({
        selection: [
            ["product.product", "Product"],
            ["partner", "Partner"],
        ],
    });
    product_id = fields.Many2one({ relation: "product.product", required: true });
    partner_ids = fields.Many2many({ relation: "partner" });

    _records = [
        {
            id: 1,
            name: "leonardo",
            turtle_foo: "yop",
        },
        {
            id: 2,
            name: "donatello",
            turtle_foo: "blip",
            turtle_int: 9,
            partner_ids: [2, 3],
        },
        {
            id: 3,
            name: "raphael",
            product_id: 1,
            turtle_bar: false,
            turtle_foo: "kawa",
            turtle_int: 21,
            turtle_ref: "product.product,1",
        },
    ];
}

class Users extends models.Model {
    _name = "res.users";

    name = fields.Char();
    partner_ids = fields.One2many({ relation: "partner", relation_field: "user_id" });

    has_group() {
        return true;
    }

    _records = [
        {
            id: 1,
            name: "Aline",
            partner_ids: [1, 2],
        },
        {
            id: 2,
            name: "Christine",
        },
    ];
}

defineModels([Partner, PartnerType, Product, Turtle, Users]);

test.tags("desktop");
test("many2many kanban: edition", async () => {
    expect.assertions(24);

    onRpc("partner.type", "web_save", ({ args }) => {
        if (args[0].length) {
            expect(args[1].name).toBe("new name");
        } else {
            expect(args[1].name).toBe("A new type");
        }
    });
    onRpc("partner", "web_save", ({ args }) => {
        const commands = args[1].timmy;
        const [record] = MockServer.env["partner.type"].search_read([["name", "=", "A new type"]]);
        // get the created type's id
        expect(commands).toEqual([
            Command.link(3),
            Command.link(4),
            Command.link(record.id),
            Command.unlink(2),
        ]);
    });

    Partner._records[0].timmy = [1, 2];
    PartnerType._records.push(
        { id: 3, name: "red", color: 6 },
        { id: 4, name: "yellow", color: 4 },
        { id: 5, name: "blue", color: 1 }
    );

    PartnerType._views = {
        form: /* xml */ `
            <form>
                <field name="name" />
            </form>
        `,
        list: /* xml */ `
            <list>
                <field name="name" />
            </list>
        `,
        search: /* xml */ `
            <search>
                <field name="name" string="Name" />
            </search>
        `,
    };

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="timmy">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <div>
                                    <a
                                        t-if="!read_only_mode"
                                        type="delete"
                                        class="fa fa-times float-end delete_icon"
                                    />
                                    <field name="name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                    <form>
                        <field name="name" />
                    </form>
                </field>
            </form>`,
    });

    expect(`.o_kanban_record:visible`).toHaveCount(2);
    expect(`.o_kanban_record:first`).toHaveText("gold");
    expect(`.o_kanban_renderer .delete_icon`).toBeVisible();
    expect(`.o_field_many2many .o-kanban-button-new:visible`).toHaveText("Add");

    // edit existing subrecord

    await clickKanbanRecord({ text: "gold" });

    await fieldInput("name").edit("new name");
    await clickModalButton({ text: "Save" });
    await animationFrame(); // todo: ????

    expect(".o_kanban_record:first:visible").toHaveText("new name");

    // add subrecords
    // -> single select
    await clickViewButton({ text: "Add" });

    expect(".modal .o_list_view tbody .o_list_record_selector").toHaveCount(3);

    await contains(".modal .o_list_view tbody tr:contains(red) .o_data_cell").click();

    expect(".o_kanban_record:visible").toHaveCount(3);
    expect(".o_kanban_record:contains(red)").toBeVisible();

    // -> multiple select
    await clickViewButton({ text: "Add" });
    expect(".modal .o_select_button").not.toBeEnabled();
    await animationFrame();

    expect(".modal .o_list_view tbody .o_list_record_selector").toHaveCount(2);

    await contains(".modal .o_list_view thead .o_list_record_selector input").click();
    await clickModalButton({ text: "Select" });

    expect(".modal .o_list_view").toHaveCount(0);
    expect(".o_kanban_record:visible").toHaveCount(5);

    // -> created record
    await clickViewButton({ text: "Add" });
    await clickModalButton({ text: "New" });

    expect(".modal .o_form_view .o_form_editable").toBeVisible();

    await fieldInput("name").edit("A new type");
    await clickModalButton({ text: "Save & Close" });

    expect(".o_kanban_record:visible").toHaveCount(6);
    expect(".o_kanban_record:contains(A new type)").toBeVisible();

    // delete subrecords
    await clickKanbanRecord({ text: "silver" });

    expect(".modal .modal-footer .o_btn_remove").toHaveCount(1);
    await clickModalButton({ text: "Remove" });

    expect(".modal").toHaveCount(0);
    expect(".o_kanban_record:visible").toHaveCount(5);
    expect(".o_kanban_record:contains(silver)").toHaveCount(0);

    await clickKanbanRecord({ text: "blue", target: ".delete_icon" });

    expect(".o_kanban_record:visible").toHaveCount(4);
    expect(".o_kanban_record:contains(blue)").toHaveCount(0);

    // save the record
    await clickSave();
});

test("many2many kanban(editable): properly handle add-label node attribute", async () => {
    Partner._records[0].timmy = [1];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="timmy" add-label="Add timmy" mode="kanban">
                        <kanban>
                            <templates>
                                <t t-name="card">
                                    <field name="name"/>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
        resId: 1,
    });

    expect(".o_field_many2many[name=timmy] .o-kanban-button-new").toHaveText("Add timmy", {
        message: "In M2M Kanban, Add button should have 'Add timmy' label",
    });
});

test("field string is used in the SelectCreateDialog", async () => {
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };
    Turtle._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
                <field name="turtles" widget="many2many" string="Abcde">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a:eq(0)").click();
    expect(".modal").toHaveCount(1);
    expect(".modal .modal-title").toHaveText("Add: pokemon");

    await contains(".modal .o_form_button_cancel").click();
    expect(".modal").toHaveCount(0);

    await contains(".o_field_x2many_list_row_add a:eq(1)").click();
    expect(".modal").toHaveCount(1);
    expect(".modal .modal-title").toHaveText("Add: Abcde");
});

test("many2many kanban: create action disabled", async () => {
    Partner._records[0].timmy = [1, 2];
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name" string="Name"/></search>',
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <kanban create="0">
                        <templates>
                            <t t-name="card">
                                <div>
                                    <a t-if="!read_only_mode" type="delete" class="fa fa-times float-end delete_icon"/>
                                    <field name="name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o-kanban-button-new").toHaveCount(1);
    expect(".o_kanban_renderer .delete_icon").toHaveCount(2);

    await contains(".o-kanban-button-new:eq(0)").click();
    expect(".modal .modal-footer .btn-primary").toHaveCount(1);
});

test("many2many kanban: conditional create/delete actions", async () => {
    PartnerType._views = {
        form: '<form><field name="name"/></form>',
        list: '<list><field name="name"/></list>',
        search: "<search/>",
    };
    Partner._records[0].timmy = [1, 2];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="color"/>
                <field name="timmy" options="{'create': [('color', '=', 'red')], 'delete': [('color', '=', 'red')]}">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    // color is red
    expect(".o-kanban-button-new").toHaveCount(1, {
        message: '"Add" button should be available',
    });

    await contains(".o_kanban_record:contains(silver):eq(0)").click();
    expect(".modal .modal-footer .o_btn_remove").toHaveCount(1);
    await contains(".modal .modal-footer .o_form_button_cancel:eq(0)").click();

    await contains(".o-kanban-button-new:eq(0)").click();
    expect(".modal .modal-footer button").toHaveCount(3);
    await contains(".modal .modal-footer .o_form_button_cancel:eq(0)").click();

    // set color to black
    await contains('div[name="color"] select').select('"black"');
    expect(".o-kanban-button-new").toHaveCount(1, {
        message: '"Add" button should still be available even after color field changed',
    });

    await contains(".o-kanban-button-new:eq(0)").click();
    // only select and cancel button should be available, create
    // button should be removed based on color field condition
    expect(".modal .modal-footer button").toHaveCount(2);
    await contains(".modal .modal-footer .o_form_button_cancel:eq(0)").click();

    await contains(".o_kanban_record:contains(silver):eq(0)").click();
    expect(".modal .modal-footer .o_btn_remove").toHaveCount(0);
});

test("many2many list (non editable): create a new record and click on action button 1", async () => {
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };
    onRpc((args) => {
        expect.step(args.method);
        if (args.method === "web_save") {
            expect(args.args[1]).toEqual({ name: "Hello" });
        }
    });
    onRpc("myaction", () => {
        expect.step(`action: myaction`);
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <header>
                            <button name="myaction" string="coucou" type="object"/>
                        </header>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();

    await contains(".modal .o_create_button").click();
    expect.verifySteps([
        "get_views",
        "web_read",
        "get_views",
        "web_search_read",
        "has_group",
        "onchange",
    ]);
    await contains(".modal [name='name'] input").edit("Hello");
    expect("[name='name'] input").toHaveValue("Hello");

    await contains(".modal .o_statusbar_buttons [name='myaction']").click();
    expect("[name='name'] input").toHaveValue("Hello");
    expect.verifySteps(["web_save", "action: myaction", "web_read"]);
});

test("many2many list (non editable): create a new record and click on action button 2", async () => {
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };
    onRpc((args) => {
        expect.step(args.method);
        if (args.method === "web_save" && args.args[0].length === 0) {
            expect(args.args[1]).toEqual({ name: "Hello" });
        }
    });
    onRpc("myaction", () => {
        expect.step(`action: myaction`);
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <header>
                            <button name="myaction" string="coucou" type="object"/>
                        </header>
                        <field name="name"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();

    await contains(".modal .o_create_button").click();
    expect.verifySteps([
        "get_views",
        "web_read",
        "get_views",
        "web_search_read",
        "has_group",
        "onchange",
    ]);

    await contains(".modal [name='name'] input").edit("Hello");
    expect("[name='name'] input").toHaveValue("Hello");

    await contains(".modal .o_statusbar_buttons [name='myaction']").click();
    expect("[name='name'] input").toHaveValue("Hello");
    expect(queryAllTexts(".modal  .modal-footer button")).toEqual([
        "Save & Close",
        "Save & New",
        "Discard",
    ]);

    await contains(".modal [name='name'] input").edit("Hello (edited)");

    await contains(".modal-footer button").click();
    expect(".modal").toHaveCount(0);
    expect(queryAllTexts("[name='timmy'] .o_data_row")).toEqual(["Hello (edited)"]);

    expect.verifySteps(["web_save", "action: myaction", "web_read", "web_save", "web_read"]);
});

test("add a new record in a many2many non editable list", async () => {
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        form: '<form><field name="name"/></form>',
        search: '<search><field name="name"/></search>',
    };

    stepAllNetworkCalls();
    onRpc("web_save", ({ kwargs }) => {
        // should not read the record as we're closing the dialog
        expect(kwargs.specification).toEqual({});
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".o_dialog .o_create_button").click();
    await contains(".o_dialog .o_field_widget[name=name] input").edit("a name");
    await contains(".o_dialog .o_form_button_save").click();
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "onchange",
        "get_views",
        "web_search_read",
        "has_group",
        "get_views",
        "onchange",
        "web_save",
        "web_read",
    ]);
});

test("add record in a many2many non editable list with context", async () => {
    expect.assertions(1);

    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };
    onRpc("web_search_read", (args) => {
        // done by the SelectCreateDialog
        expect(args.kwargs.context).toEqual({
            abc: 2,
            allowed_company_ids: [1],
            bin_size: true,
            current_company_id: 1,
            lang: "en",
            tz: "taht",
            uid: 7,
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="timmy" context="{'abc': int_field}">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    });

    await contains(".o_field_widget[name=int_field] input").edit("2");
    await contains(".o_field_x2many_list_row_add a").click();
});

test("many2many list (editable): edition", async () => {
    Partner._records[0].timmy = [1, 2];
    PartnerType._records.push({ id: 15, name: "bronze", color: 6 });
    PartnerType._fields.float_field = fields.Float({ string: "Float" });

    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };
    onRpc((args) => {
        expect.step(args.method);
        if (args.method === "write") {
            expect(args.args[1].timmy).toEqual([
                [6, false, [12, 15]],
                [1, 12, { name: "new name" }],
            ]);
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <list editable="top">
                        <field name="name"/>
                        <field name="float_field"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_list_renderer td.o_list_number").toHaveCount(2);
    expect(".o_list_renderer tbody td:eq(0)").toHaveText("gold", {
        message: "name of first subrecord should be the one in DB",
    });
    expect(".o_list_record_remove").toHaveCount(2);
    expect("td.o_list_record_remove button").toHaveClass("fa fa-times");
    expect(".o_field_x2many_list_row_add").toHaveCount(1);

    // edit existing subrecord
    await contains(".o_list_renderer tbody td:eq(0)").click();
    expect(".modal").toHaveCount(0);
    expect(".o_list_renderer tbody tr:eq(0)").toHaveClass("o_selected_row");
    await contains(".o_selected_row div[name=name] input").edit("new name", { confirm: false });
    expect(".o_list_renderer .o_data_row:eq(0)").toHaveClass("o_selected_row");
    expect(".o_list_renderer div[name=name] input").toBeFocused({
        message: "edited field should still have the focus",
    });
    await contains(".o_form_view").click();
    expect(".o_list_renderer tbody tr:eq(0)").not.toHaveClass("o_selected_row");
    expect(".o_list_renderer tbody td:eq(0)").toHaveText("new name", {
        message: "value of subrecord should have been updated",
    });
    expect.verifySteps(["get_views", "web_read"]);

    // add new subrecords
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal").toHaveCount(1);
    expect(".modal .o_list_view .o_data_row").toHaveCount(1);
    await contains(".modal .o_list_view .o_data_row .o_data_cell").click();
    expect(".modal .o_list_view").toHaveCount(0);
    expect(".o_list_renderer td.o_list_number").toHaveCount(3);

    // remove subrecords
    await contains(".o_list_record_remove:eq(1)").click();
    expect(".o_list_renderer td.o_list_number").toHaveCount(2);
    expect(".o_list_renderer tbody .o_data_row td:eq(0)").toHaveText("new name", {
        message: "the updated row still has the correct values",
    });

    // save
    await clickSave();
    expect(".o_list_renderer td.o_list_number").toHaveCount(2);
    expect(".o_list_renderer .o_data_row td:eq(0)").toHaveText("new name", {
        message: "the updated row still has the correct values",
    });

    expect.verifySteps([
        "get_views", // list view in dialog
        "web_search_read", // list view in dialog
        "has_group",
        "web_read", // relational field (updated)
        "web_save", // save main record
    ]);
});

test("many2many: create & delete attributes (both true)", async () => {
    Partner._records[0].timmy = [1, 2];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <list create="true" delete="true">
                        <field name="color"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect(".o_list_record_remove").toHaveCount(2);
});

test("many2many: create & delete attributes (both false)", async () => {
    Partner._records[0].timmy = [1, 2];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <list create="false" delete="false">
                        <field name="color"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect(".o_list_record_remove").toHaveCount(2);
});

test("many2many list: create action disabled", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <list create="0">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_field_x2many_list_row_add").toHaveCount(1);
});

test("fieldmany2many list comodel not writable", async () => {
    /**
     * Many2Many List should behave as the m2m_tags
     * that is, the relation can be altered even if the comodel itself is not CRUD-able
     * This can happen when someone has read access alone on the comodel
     * and full CRUD on the current model
     */
    expect.assertions(12);

    PartnerType._views = {
        list: `
            <list create="false" delete="false" edit="false">
                <field name="name"/>
            </list>`,
        search: '<search><field name="name"/></search>',
    };
    onRpc((args) => {
        if (args.route === "/web/dataset/call_kw/partner/web_save" && args.args[0].length === 0) {
            expect(args.args[1]).toEqual({ timmy: [[4, 1]] });
        }
        if (args.route === "/web/dataset/call_kw/partner/web_save" && args.args[0].length !== 0) {
            expect(args.args[1]).toEqual({ timmy: [[3, 1]] });
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many" can_create="False" can_write="False"/>
            </form>`,
    });

    expect(".o_field_many2many .o_field_x2many_list_row_add").toHaveCount(1);
    await contains(".o_field_many2many .o_field_x2many_list_row_add a").click();
    expect(".modal").toHaveCount(1);

    expect(".modal-footer button").toHaveCount(2);
    expect(".modal-footer button.o_select_button").toHaveCount(1);
    expect(".modal-footer button.o_form_button_cancel").toHaveCount(1);

    await contains(".modal .o_list_view .o_data_cell").click();
    expect(".modal").toHaveCount(0);

    expect(".o_field_many2many .o_data_row").toHaveCount(1);
    expect(queryAllTexts(".o_field_many2many .o_data_row")).toEqual(["gold"]);
    expect(".o_field_many2many .o_field_x2many_list_row_add").toHaveCount(1);

    await clickSave();

    expect(".o_field_many2many .o_data_row .o_list_record_remove").toHaveCount(1);
    await contains(".o_field_many2many .o_data_row .o_list_record_remove").click();
    await clickSave();
});

test("many2many list: conditional create/delete actions", async () => {
    Partner._records[0].timmy = [1, 2];

    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: "<search/>",
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="color"/>
                <field name="timmy" options="{'create': [('color', '=', 'red')], 'delete': [('color', '=', 'red')]}">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // color is red -> create and delete actions are available
    expect(".o_field_x2many_list_row_add").toHaveCount(1, {
        message: "should have the 'Add an item' link",
    });
    expect(".o_list_record_remove").toHaveCount(2);

    await contains(".o_field_x2many_list_row_add a:eq(0)").click();

    expect(".modal .modal-footer button").toHaveCount(3);

    await contains(".modal .modal-footer .o_form_button_cancel:eq(0)").click();

    // set color to black -> create and delete actions are no longer available
    await contains('div[name="color"] select').select('"black"');

    // add a line and remove icon should still be there as they don't create/delete records,
    // but rather add/remove links
    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect(".o_list_record_remove").toHaveCount(2);

    await contains(".o_field_x2many_list_row_add a:eq(0)").click();
    expect(".modal .modal-footer button").toHaveCount(2);
});

test("many2many field with link/unlink options (list)", async () => {
    Partner._records[0].timmy = [1, 2];
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: "<search/>",
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="color"/>
                <field name="timmy" options="{'link': [('color', '=', 'red')], 'unlink': [('color', '=', 'red')]}">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // color is red -> link and unlink actions are available
    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect(".o_list_record_remove").toHaveCount(2);

    await contains(".o_field_x2many_list_row_add a:eq(0)").click();

    expect(".modal .modal-footer button").toHaveCount(3);

    await contains(".modal .modal-footer .o_form_button_cancel:eq(0)").click();

    // set color to black -> link and unlink actions are no longer available
    await contains('div[name="color"] select').select('"black"');

    expect(".o_field_x2many_list_row_add").toHaveCount(0);
    expect(".o_list_record_remove").toHaveCount(0);
});

test('many2many field with link/unlink options (list, create="0")', async () => {
    Partner._records[0].timmy = [1, 2];
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: "<search/>",
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="color"/>
                <field name="timmy" options="{'link': [('color', '=', 'red')], 'unlink': [('color', '=', 'red')]}">
                    <list create="0">
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // color is red -> link and unlink actions are available
    expect(".o_field_x2many_list_row_add").toHaveCount(1);
    expect(".o_list_record_remove").toHaveCount(2);

    await contains(".o_field_x2many_list_row_add a:eq(0)").click();

    expect(".modal .modal-footer button").toHaveCount(2);

    await contains(".modal .modal-footer .o_form_button_cancel:eq(0)").click();

    // set color to black -> link and unlink actions are no longer available
    await contains('div[name="color"] select').select('"black"');

    expect(".o_field_x2many_list_row_add").toHaveCount(0);
    expect(".o_list_record_remove").toHaveCount(0);
});

test("many2many field with link option (kanban)", async () => {
    Partner._records[0].timmy = [1, 2];

    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: "<search/>",
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="color"/>
                <field name="timmy" options="{'link': [('color', '=', 'red')]}">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    // color is red -> link and unlink actions are available
    expect(".o-kanban-button-new").toHaveCount(1);

    await contains(".o-kanban-button-new").click();

    expect(".modal .modal-footer button").toHaveCount(3);

    await contains(".modal .modal-footer .o_form_button_cancel:eq(0)").click();

    // set color to black -> link and unlink actions are no longer available
    await contains('div[name="color"] select').select('"black"');

    expect(".o-kanban-button-new").toHaveCount(0);
});

test('many2many field with link option (kanban, create="0")', async () => {
    Partner._records[0].timmy = [1, 2];
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: "<search/>",
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="color"/>
                <field name="timmy" options="{'link': [('color', '=', 'red')]}">
                    <kanban create="0">
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    // color is red -> link and unlink actions are available
    expect(".o-kanban-button-new").toHaveCount(1);

    await contains(".o-kanban-button-new").click();

    expect(".modal .modal-footer button").toHaveCount(2);

    await contains(".modal .modal-footer .o_form_button_cancel:eq(0)").click();

    // set color to black -> link and unlink actions are no longer available
    await contains('div[name="color"] select').select('"black"');

    expect(".o-kanban-button-new").toHaveCount(0);
});

test("many2many list: list of id as default value", async () => {
    Partner._fields.turtles = fields.Many2many({
        relation: "turtle",
        relation_field: "turtle_trululu",
        default: [
            [4, 2],
            [4, 3],
        ],
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>
        `,
    });

    expect(queryAllTexts("td.o_data_cell")).toEqual(["blip", "kawa"]);
});

test("context and domain dependent on an x2m must contain the list of current ids for the x2m", async () => {
    expect.assertions(2);

    Partner._fields.turtles = fields.Many2many({
        relation: "turtle",
        relation_field: "turtle_trululu",
        default: [
            [4, 2],
            [4, 3],
        ],
    });
    Turtle._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };
    onRpc("web_search_read", (args) => {
        expect(args.kwargs.domain).toEqual(["&", ["id", "in", [2, 3]], "!", ["id", "in", [2, 3]]]);
        expect(args.kwargs.context.test).toEqual([2, 3]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
        <form>
            <field name="turtles" context="{'test': turtles}" domain="[('id', 'in', turtles)]">
                <list>
                    <field name="turtle_foo"/>
                </list>
            </field>
        </form>`,
    });
    await contains(".o_field_x2many_list_row_add a").click();
});

test("many2many list with x2many: add a record", async () => {
    PartnerType._fields.m2m = fields.Many2many({
        string: "M2M",
        relation: "turtle",
    });
    PartnerType._records[0].m2m = [1, 2];
    PartnerType._records[1].m2m = [2, 3];

    PartnerType._views = {
        list: `
            <list>
                <field name="name"/>
                <field name="m2m" widget="many2many_tags"/>
            </list>`,
        search: '<search><field name="name" string="Name"/></search>',
    };
    onRpc((args) => {
        if (args.method !== "get_views") {
            expect.step(args.route.split("/").at(-1) + " on " + args.model);
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy"/></form>',
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_data_row:first .o_data_cell:eq(0)").click();

    expect(".o_data_row").toHaveCount(1);
    expect(queryAllTexts(".o_data_row:first .o_tag_badge_text")).toEqual(["leonardo", "donatello"]);

    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_data_row .o_data_cell:eq(1)").click();

    expect(".o_data_row").toHaveCount(2);
    expect(queryAllTexts(".o_data_row:eq(1) .o_tag_badge_text")).toEqual(["donatello", "raphael"]);

    expect.verifySteps([
        "web_read on partner",
        "web_search_read on partner.type",
        "has_group on res.users",
        "web_read on partner.type",
        "web_search_read on partner.type",
        "web_read on partner.type",
    ]);
});

test("many2many with a domain", async () => {
    // The domain specified on the field should not be replaced by the potential
    // domain the user writes in the dialog, they should rather be concatenated
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name" string="Name"/></search>',
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" domain="[['name', '=', 'gold']]"/>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal .o_data_row").toHaveCount(1);
    await contains(`.modal .o_searchview input`).edit("s");

    expect(".modal .o_data_row").toHaveCount(0);
});

test("many2many list (editable): edition concurrence", async () => {
    Partner._records[0].timmy = [1, 2];
    PartnerType._records.push({ id: 15, name: "bronze", color: 6 });
    PartnerType._fields.float_field = fields.Float({ string: "Float" });
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name" string="Name"/></search>',
    };

    onRpc((args) => {
        expect.step(args.method);
        if (args.method === "web_save") {
            expect(args.args[1]).toEqual({
                timmy: [[3, 1]],
            });
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="timmy">
                        <list editable="top">
                            <field name="display_name"/>
                            <field name="float_field"/>
                        </list>
                    </field>
                </form>`,
        resId: 1,
    });

    const removeButton = contains(".o_list_record_remove");
    removeButton.click();
    removeButton.click();
    await clickSave();
    expect.verifySteps(["get_views", "web_read", "web_save"]);
});

test("many2many list with onchange and edition of a record", async () => {
    Partner._fields.turtles = fields.Many2many({
        relation: "turtle",
        relation_field: "turtle_trululu",
        onChange: function () {},
    });

    Turtle._views = {
        form: '<form string="Turtle Power"><field name="turtle_bar"/></form>',
    };
    onRpc((args) => {
        expect.step(args.method);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains("td.o_data_cell").click();
    expect.verifySteps(["get_views", "web_read"]);

    await contains(".modal-body input[type=checkbox]").click();
    await contains(".modal .modal-footer .btn-primary").click();
    expect.verifySteps(["web_save"]);
    expect(".o_form_button_save").not.toBeVisible();
});

test("many2many concurrency edition", async () => {
    Partner._fields.turtles = fields.Many2many({
        relation: "turtle",
        relation_field: "turtle_trululu",
        onChange: function () {},
    });
    Turtle._records.push({
        id: 4,
        name: "Bloop",
        turtle_bar: true,
        turtle_foo: "Bloop",
        partner_ids: [],
    });
    Partner._records[0].turtles = [1, 2, 3, 4];
    Turtle._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name" string="Name"/></search>',
    };

    const def = new Deferred();
    let firstOnChange = false;
    onRpc("onchange", async () => {
        if (!firstOnChange) {
            firstOnChange = true;
            await def;
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect(".o_data_row").toHaveCount(4);
    await contains(".o_data_row .o_list_record_remove").click();
    await contains(".o_data_row .o_list_record_remove").click();
    await contains(".o_field_x2many_list_row_add a").click();
    await contains(".modal .o_data_row td.o_data_cell:eq(0)").click();
    def.resolve();
    await animationFrame();
    expect(".o_data_row").toHaveCount(3);
});

test("many2many widget: creates a new record with a context containing the parentID", async () => {
    Turtle._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
        form: '<form string="Turtle Power"><field name="turtle_trululu"/></form>',
    };
    onRpc(({ args, method, kwargs }) => {
        expect.step(method);
        if (method === "onchange") {
            expect(kwargs.context.default_turtle_trululu).toBe(1);
            expect(args).toEqual([
                [],
                {},
                [],
                {
                    turtle_foo: {},
                    turtle_trululu: {
                        fields: {
                            display_name: {},
                        },
                    },
                },
            ]);
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles" widget="many2many" context="{'default_turtle_trululu': id}" >
                    <list>
                        <field name="turtle_foo"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains(".o_field_x2many_list_row_add a").click();
    expect.verifySteps(["get_views", "web_search_read", "has_group"]);

    await contains(".o_create_button").click();
    expect("[name='turtle_trululu'] input").toHaveValue("first record");
    expect.verifySteps(["get_views", "onchange"]);
});

test("onchange with 40+ commands for a many2many", async () => {
    // this test ensures that the basic_model correctly handles more LINK_TO
    // commands than the limit of the dataPoint (40 for x2many kanban)
    expect.assertions(10);

    // create a lot of partner_types that will be linked by the onchange
    const commands = [];
    for (var i = 0; i < 45; i++) {
        var id = 100 + i;
        PartnerType._records.push({ id: id, name: "type " + id });
        commands.push([4, id]);
    }
    Partner._fields.foo = fields.Char({
        default: "My little Foo Value",
        onChange: function (obj) {
            obj.timmy = commands;
        },
    });
    onRpc((args) => {
        expect.step(args.method);
        if (args.method === "web_save") {
            expect(args.args[1].timmy).toEqual(commands.map((c) => [c[0], c[1]]));
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="timmy">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    expect.verifySteps(["get_views", "web_read"]);

    await contains(".o_field_widget[name=foo] input").edit("trigger onchange");
    expect.verifySteps(["onchange"]);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(40);
    await contains(".o_field_widget[name=timmy] .o_pager_next:eq(0)").click();
    expect.verifySteps([]);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);

    await clickSave();

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(40);

    await contains(".o_field_widget[name=timmy] .o_pager_next:eq(0)").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);

    await contains(".o_field_widget[name=timmy] .o_pager_next:eq(0)").click();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(40);

    expect.verifySteps(["web_save", "web_read"]);
});

test.tags("desktop");
test("onchange with 40+ commands for a many2many on desktop", async () => {
    // this test ensures that the basic_model correctly handles more LINK_TO
    // commands than the limit of the dataPoint (40 for x2many kanban)

    // create a lot of partner_types that will be linked by the onchange
    const commands = [];
    for (var i = 0; i < 45; i++) {
        var id = 100 + i;
        PartnerType._records.push({ id: id, name: "type " + id });
        commands.push([4, id]);
    }
    Partner._fields.foo = fields.Char({
        default: "My little Foo Value",
        onChange: function (obj) {
            obj.timmy = commands;
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="timmy">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_widget[name=foo] input").edit("trigger onchange");
    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("1-40 / 45");
    await contains(".o_field_widget[name=timmy] .o_pager_next:eq(0)").click();
    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("41-45 / 45");

    await clickSave();

    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("1-40 / 45");

    await contains(".o_field_widget[name=timmy] .o_pager_next:eq(0)").click();
    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("41-45 / 45");

    await contains(".o_field_widget[name=timmy] .o_pager_next:eq(0)").click();
    expect(".o_x2m_control_panel .o_pager_counter").toHaveText("1-40 / 45");
});

test("default_get, onchange, onchange on m2m", async () => {
    expect.assertions(1);
    Partner._fields.int_field = fields.Integer({ onChange: function () {} });

    let firstOnChange = true;
    onRpc("onchange", (args) => {
        if (firstOnChange) {
            firstOnChange = false;
            return {
                value: {
                    timmy: [[1, 12, { name: "gold" }]],
                },
            };
        } else {
            expect(args.args[1]).toEqual({
                display_name: false,
                int_field: 2,
                timmy: [[1, 12, { name: "gold" }]],
            });
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <field name="timmy">
                        <list>
                            <field name="name"/>
                        </list>
                    </field>
                    <field name="int_field"/>
                </sheet>
            </form>`,
    });

    await contains(".o_field_widget[name=int_field] input").edit(2);
});

test("many2many list add *many* records, remove, re-add", async () => {
    Partner._fields.timmy = fields.Many2many({
        relation: "partner.type",
        string: "pokemon",
        domain: [["color", "=", 2]],
        onChange: true,
    });
    PartnerType._fields.product_ids = fields.Many2many({
        string: "Product",
        relation: "product.product",
    });

    for (let i = 0; i < 50; i++) {
        const new_record_partner_type = { id: 100 + i, name: "batch" + i, color: 2 };
        PartnerType._records.push(new_record_partner_type);
    }

    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/><field name="color"/></search>',
    };
    onRpc("get_formview_id", (args) => {
        expect(args.args[0]).toEqual([1]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many">
                    <list>
                        <field name="name"/>
                        <field name="product_ids" widget="many2many_tags"/>
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    // First round: add 51 records in batch
    await contains(".o_field_x2many_list_row_add a").click();

    expect(".modal-lg").toHaveCount(1);

    await contains("thead input[type=checkbox]:eq(0)").click();
    await animationFrame();

    await contains(".btn.btn-primary.o_select_button:eq(0)").click();

    expect(".o_data_row").toHaveCount(51); // the 50 in batch + 'gold'

    expect(
        ".o_field_many2many.o_field_widget .o_field_x2many.o_field_x2many_list .o_cp_pager"
    ).toHaveCount(0);

    await clickSave();

    expect(
        ".o_field_many2many.o_field_widget .o_field_x2many.o_field_x2many_list .o_cp_pager"
    ).toHaveCount(1);

    expect(
        ".o_field_many2many.o_field_widget .o_field_x2many.o_field_x2many_list .o_pager_value"
    ).toHaveText("1-40");

    // Secound round: remove one record
    await contains(
        ".o_field_many2many.o_field_widget .o_field_x2many.o_field_x2many_list .o_list_record_remove:eq(0)"
    ).click();
    expect(
        ".o_field_many2many.o_field_widget .o_field_x2many.o_field_x2many_list .o_pager_limit"
    ).toHaveText("50");

    // Third round: re-add 1 records
    await contains(".o_field_x2many_list_row_add a:eq(0)").click();

    expect(".modal-lg").toHaveCount(1);

    await contains("thead input[type=checkbox]:eq(0)").click();
    await animationFrame();

    await contains(".btn.btn-primary.o_select_button:eq(0)").click();

    expect(".o_data_row").toHaveCount(41);
});

test("many2many kanban: action/type attribute", async () => {
    Partner._records[0].timmy = [1];
    onRpc("a1", () => {
        expect.step(`action: a1`);
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy">
                    <kanban action="a1" type="object">
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>`,
        resId: 1,
    });
    await contains(".o_kanban_record").click();
    expect.verifySteps(["action: a1"]);
});

test("select create with _view_ref as text", async () => {
    PartnerType._views = {
        [["list", "my.little.string"]]: `<list><field name="name"/></list>`,
        search: `<search />`,
    };
    patchWithCleanup(Many2XAutocomplete.defaultProps, {
        searchLimit: 1,
    });
    let checkGetViews = false;
    onRpc("get_views", (args) => {
        if (checkGetViews) {
            expect.step("get_views");
            expect(args.kwargs.views).toEqual([
                [false, "list"],
                [false, "search"],
            ]);
            expect(args.kwargs.context.list_view_ref).toBe("my.little.string");
        }
    });

    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" context="{ 'list_view_ref': 'my.little.string' }"/>
            </form>`,
    });
    await contains(".o_field_many2many_selection input").click();
    checkGetViews = true;
    await contains(".o_m2o_dropdown_option_search_more").click();
    expect.verifySteps([`get_views`]);

    expect(".modal").toHaveCount(1);
    expect(".modal-title").toHaveText("Search: pokemon");
});

test("many2many basic keys in field evalcontext -- in list", async () => {
    expect.assertions(5);
    PartnerType._fields.partner_id = fields.Many2one({
        string: "Partners",
        relation: "partner",
    });
    Partner._records.push({ id: 7, name: "default partner" });
    PartnerType._views = {
        form: `<form><field name="partner_id" /></form>`,
    };

    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1 },
        { id: 2, name: "Herman's", sequence: 2 },
        { id: 1, name: "Heroes TM", sequence: 3 },
    ];
    onRpc("onchange", (args) => {
        expect(args.kwargs.context.uid).toBe(7);
        expect(args.kwargs.context.allowed_company_ids).toEqual([3]);
        expect(args.kwargs.context.company_id).toBe(3);
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="timmy" widget="many2many_tags" context="{ 'default_partner_id': uid, 'allowed_company_ids': allowed_company_ids, 'company_id': current_company_id}"/>
            </list>`,
    });

    await contains(".o_data_cell").click();
    await contains(".o_field_many2many_selection input").edit("indianapolis", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create_edit").click();
    expect(".modal .o_field_many2one").toHaveCount(1);
    expect(".modal .o_field_many2one input").toHaveValue("default partner");
});

test("many2many basic keys in field evalcontext -- in form", async () => {
    expect.assertions(5);
    PartnerType._fields.partner_id = fields.Many2one({
        string: "Partners",
        relation: "partner",
    });
    Partner._records.push({ id: 7, name: "default partner" });
    PartnerType._views = {
        form: `<form><field name="partner_id" /></form>`,
    };
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1 },
        { id: 2, name: "Herman's", sequence: 2 },
        { id: 1, name: "Heroes TM", sequence: 3 },
    ];

    onRpc("onchange", (args) => {
        expect(args.kwargs.context.default_partner_id).toBe(7);
        expect(args.kwargs.context.allowed_company_ids).toEqual([3]);
        expect(args.kwargs.context.company_id).toBe(3);
    });

    await mountView({
        type: "form",
        resId: 1,
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" context="{ 'default_partner_id': uid, 'allowed_company_ids': allowed_company_ids, 'company_id': current_company_id}"/>
            </form>`,
    });

    await contains(".o_field_many2many_selection input").edit("indianapolis", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create_edit").click();
    expect(".modal .o_field_many2one").toHaveCount(1);
    expect(".modal .o_field_many2one input").toHaveValue("default partner");
});

test("many2many basic keys in field evalcontext -- in a x2many in form", async () => {
    expect.assertions(5);
    PartnerType._fields.partner_id = fields.Many2one({
        string: "Partners",
        relation: "partner",
    });
    Partner._records.push({ id: 7, name: "default partner" });
    PartnerType._views = {
        form: `<form><field name="partner_id" /></form>`,
    };

    const rec = Partner._records.find(({ id }) => id === 2);
    rec.p = [1];
    serverState.companies = [
        { id: 3, name: "Hermit", sequence: 1 },
        { id: 2, name: "Herman's", sequence: 2 },
        { id: 1, name: "Heroes TM", sequence: 3 },
    ];
    onRpc("onchange", (args) => {
        expect(args.kwargs.context.default_partner_id).toBe(7);
        expect(args.kwargs.context.allowed_company_ids).toEqual([3]);
        expect(args.kwargs.context.company_id).toBe(3);
    });

    await mountView({
        type: "form",
        resId: 2,
        resModel: "partner",
        arch: `
                <form>
                <field name="p">
                    <list editable="top">
                        <field name="timmy" widget="many2many_tags" context="{ 'default_partner_id': uid, 'allowed_company_ids': allowed_company_ids, 'company_id': current_company_id}"/>
                    </list>
                </field>
                </form>`,
    });

    await contains(".o_data_cell").click();
    await contains(".o_field_many2many_selection input").edit("indianapolis", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create_edit").click();
    expect(".modal .o_field_many2one").toHaveCount(1);
    expect(".modal .o_field_many2one input").toHaveValue("default partner");
});

test("`this` inside rendererProps should reference the component", async () => {
    class CustomX2manyField extends X2ManyField {
        setup() {
            super.setup();
            this.selectCreate = (params) => {
                expect.step("selectCreate");
                expect(this.num).toBe(2);
            };
            this.num = 1;
        }

        async onAdd({ context, editable } = {}) {
            this.num = 2;
            expect.step("onAdd");
            super.onAdd(...arguments);
        }
    }

    const customX2ManyField = {
        ...x2ManyField,
        component: CustomX2manyField,
    };
    registry.category("fields").add("custom", customX2ManyField);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="timmy" widget="custom">
                        <list editable="top">
                            <field name="display_name"/>
                        </list>
                        <form>
                            <field name="display_name" />
                        </form>
                    </field>
                </form>`,
        resId: 1,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect.verifySteps(["onAdd", "selectCreate"]);
});
