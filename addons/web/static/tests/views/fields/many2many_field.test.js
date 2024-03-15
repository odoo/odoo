import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";

import {
    Command,
    MockServer,
    clickModalButton,
    clickSave,
    clickViewButton,
    contains,
    defineModels,
    fieldInput,
    fields,
    clickKanbanRecord,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "res.partner";

    name = fields.Char();
    foo = fields.Char({ default: "My little Foo Value" });
    bar = fields.Boolean({ default: true });
    int_field = fields.Integer();
    p = fields.Many2many({ relation: "res.partner", relation_field: "trululu" });
    turtles = fields.One2many({ relation: "turtle", relation_field: "turtle_trululu" });
    trululu = fields.Many2one({ relation: "res.partner" });
    timmy = fields.Many2many({ relation: "res.partner.type", string: "pokemon" });
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
            ["res.partner.type", "Partner Type"],
            ["res.partner", "Partner"],
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
    _name = "res.partner.type";

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
    turtle_trululu = fields.Many2one({ relation: "res.partner" });
    turtle_ref = fields.Reference({
        selection: [
            ["product.product", "Product"],
            ["res.partner", "Partner"],
        ],
    });
    product_id = fields.Many2one({ relation: "product.product", required: true });
    partner_ids = fields.Many2many({ relation: "res.partner" });

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
    partner_ids = fields.One2many({ relation: "res.partner", relation_field: "user_id" });

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

test.tags("desktop")("many2many kanban: edition", async () => {
    expect.assertions(24);

    onRpc("res.partner.type", "web_save", ({ args }) => {
        if (args[0].length) {
            expect(args[1].name).toBe("new name");
        } else {
            expect(args[1].name).toBe("A new type");
        }
    });
    onRpc("res.partner", "web_save", ({ args }) => {
        const commands = args[1].timmy;
        const [record] = MockServer.env["res.partner.type"].search_read([
            ["display_name", "=", "A new type"],
        ]);
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
            <tree>
                <field name="name" />
            </tree>
        `,
        search: /* xml */ `
            <search>
                <field name="name" string="Name" />
            </search>
        `,
    };

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="timmy">
                    <kanban>
                        <field name="display_name" />
                        <templates>
                            <t t-name="kanban-box">
                                <div class="oe_kanban_global_click">
                                    <a
                                        t-if="!read_only_mode"
                                        type="delete"
                                        class="fa fa-times float-end delete_icon"
                                    />
                                    <span>
                                        <t t-esc="record.display_name.value" />
                                    </span>
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
