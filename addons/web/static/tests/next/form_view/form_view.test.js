// Tests of the form view, copied from `views/form/form_view.test.js` and run
// against the form view of `next/`: the "form" view is replaced by it, so that
// the tests are kept as they are.

import { beforeEach, expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { formView } from "@web/next/form_view/form_view";

class Partner extends models.Model {
    name = fields.Char({ translate: true });
    foo = fields.Char({ default: "My little Foo Value" });
    bar = fields.Boolean();
    int_field = fields.Integer();
    float_field = fields.Float({ aggregator: "sum" });
    child_ids = fields.One2many({ string: "one2many field", relation: "partner" });
    parent_id = fields.Many2one({ relation: "partner" });
    type_ids = fields.Many2many({ relation: "partner.type" });
    product_id = fields.Many2one({ relation: "product" });
    product_ids = fields.One2many({ relation: "product" });
    state = fields.Selection({
        selection: [
            ["ab", "AB"],
            ["cd", "CD"],
            ["ef", "EF"],
        ],
    });
    date = fields.Date();
    datetime = fields.Datetime();
    reference = fields.Reference({
        selection: [
            ["product", "Product"],
            ["partner_type", "Partner Type"],
            ["partner", "Partner"],
        ],
    });
    user_id = fields.Many2one({ relation: "res.users" });

    _records = [
        {
            id: 1,
            name: "first record",
            product_id: 37,
            bar: true,
            foo: "yop",
            int_field: 10,
            float_field: 0.44,
            child_ids: [],
            type_ids: [],
            parent_id: 4,
            state: "ab",
            date: "2017-01-25",
            datetime: "2016-12-12 10:55:05",
        },
        {
            id: 2,
            name: "second record",
            bar: true,
            foo: "blip",
            int_field: 9,
            float_field: 13,
            child_ids: [],
            type_ids: [],
            parent_id: 1,
            state: "cd",
        },
        {
            id: 4,
            name: "aaa",
            state: "ef",
        },
        {
            id: 5,
            name: "aaa",
            foo: "",
            bar: false,
            state: "ef",
        },
    ];
}

class PartnerType extends models.Model {
    _name = "partner.type";

    name = fields.Char();
    color = fields.Integer();
    foo = fields.Char();

    _records = [
        { id: 12, name: "gold", color: 2 },
        { id: 14, name: "silver", color: 5 },
    ];
}

class Product extends models.Model {
    name = fields.Char();
    partner_type_id = fields.Many2one({ relation: "partner.type" });

    _records = [
        { id: 37, name: "xphone" },
        { id: 41, name: "xpad" },
    ];
}

class ResUsers extends models.Model {
    _name = "res.users";

    name = fields.Char();
    partner_ids = fields.One2many({ relation: "partner", relation_field: "user_id" });

    _records = [
        { id: 17, name: "Aline", partner_ids: [1] },
        { id: 19, name: "Christine" },
    ];
}

class ResCompany extends models.Model {
    _name = "res.company";
    name = fields.Char();
}

defineModels([Partner, PartnerType, Product, ResUsers, ResCompany]);

onRpc("has_group", () => true);

beforeEach(() => {
    registry.category("views").add("form", formView, { force: true });
});

test(`simple form rendering`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div class="test" style="opacity: 0.5;">some html<span>aa</span></div>
                <sheet>
                    <group>
                        <group style="background-color: red">
                            <field name="foo" style="color: blue;"/>
                            <field name="bar"/>
                            <field name="int_field" string="f3_description"/>
                            <field name="float_field"/>
                        </group>
                        <group>
                            <div class="hello"></div>
                        </group>
                    </group>
                    <notebook>
                        <page string="Partner Yo">
                            <field name="child_ids">
                                <list>
                                    <field name="foo"/>
                                    <field name="bar"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`div.test`).toHaveCount(1);
    expect(`div.test`).toHaveStyle({ opacity: "0.5" });
    expect(`label:contains(Foo)`).toHaveCount(1);
    expect(`.o_field_char input`).toHaveCount(1);
    expect(`.o_field_char input`).toHaveValue("blip");
    expect(`.o_group .o_inner_group:eq(0)`).toHaveStyle({ backgroundColor: "rgb(255, 0, 0)" });
    expect(`.o_field_widget[name=foo]`).toHaveStyle({ color: "rgb(0, 0, 255)" });
    expect(`label:contains(something_id)`).toHaveCount(0);
    expect(`label:contains(f3_description)`).toHaveCount(1);
    expect(`div.o_field_one2many table`).toHaveCount(1);
    expect(`div.o_cell:not(.o_list_record_selector) .o-checkbox input:checked`).toHaveCount(1);
    expect(`label.o_form_label_empty:contains(type_ids)`).toHaveCount(0);
});
