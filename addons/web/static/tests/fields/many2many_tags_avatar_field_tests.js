/** @odoo-module **/

import { click, getFixture, selectDropdownItem } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;

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

    QUnit.module("Many2ManyTagsAvatarField");

    QUnit.test("widget many2many_tags_avatar", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: "turtle",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="partner_ids" widget="many2many_tags_avatar"/>
                    </sheet>
                </form>`,
            resId: 2,
        });

        assert.containsN(
            target,
            ".o_field_many2many_tags_avatar.o_field_widget .badge",
            2,
            "should have 2 records"
        );
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags_avatar.o_field_widget .badge img").dataset
                .src,
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image"
        );
    });

    QUnit.test("widget many2many_tags_avatar in list view", async function (assert) {
        assert.expect(17);

        const records = [];
        for (let id = 5; id <= 15; id++) {
            records.push({
                id,
                display_name: `record ${id}`,
            });
        }
        serverData.models.partner.records = serverData.models.partner.records.concat(records);

        serverData.models.turtle.records.push({
            id: 4,
            display_name: "crime master gogo",
            turtle_bar: true,
            turtle_foo: "yop",
            partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        });
        serverData.models.turtle.records[0].partner_ids = [1];
        serverData.models.turtle.records[1].partner_ids = [1, 2, 4, 5, 6, 7];
        serverData.models.turtle.records[2].partner_ids = [1, 2, 4, 5, 7];

        await makeView({
            type: "list",
            resModel: "turtle",
            serverData,
            arch:
                '<tree editable="bottom"><field name="partner_ids" widget="many2many_tags_avatar"/></tree>',
        });
        assert.strictEqual(
            target.querySelector(".o_data_row .o_field_many2many_tags_avatar img.o_m2m_avatar")
                .dataset.src,
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_data_row .o_many2many_tags_avatar_cell .o_field_many2many_tags_avatar"
                )
                .textContent.trim(),
            "first record",
            "should display like many2one avatar if there is only one record"
        );
        assert.containsN(
            target,
            ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_tag:not(.o_m2m_avatar_empty)",
            4,
            "should have 4 records"
        );
        assert.containsN(
            target,
            ".o_data_row:nth-child(3) .o_field_many2many_tags_avatar .o_tag:not(.o_m2m_avatar_empty)",
            5,
            "should have 5 records"
        );
        assert.containsOnce(
            target,
            ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
                )
                .textContent.trim(),
            "+2",
            "should have +2 in o_m2m_avatar_empty"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_tag:nth-child(2) img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_tag:nth-child(3) img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/4/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_tag:nth-child(4) img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/5/avatar_128",
            "should have correct avatar image"
        );
        assert.containsNone(
            target,
            ".o_data_row:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.containsN(
            target,
            ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_tag:not(.o_m2m_avatar_empty)",
            4,
            "should have 4 records"
        );
        assert.containsOnce(
            target,
            ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
                )
                .textContent.trim(),
            "+9",
            "should have +9 in o_m2m_avatar_empty"
        );

        // check data-tooltip attribute (used by the tooltip service)
        const tag = target.querySelector(
            ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
        );
        assert.strictEqual(
            tag.dataset["tooltip"],
            "record 6<br/>record 7",
            "shows a tooltip on hover"
        );

        await click(target.querySelector(".o_data_row .o_many2many_tags_avatar_cell"));
        assert.containsN(
            target,
            ".o_data_row.o_selected_row .o_many2many_tags_avatar_cell .badge",
            1,
            "should have 1 many2many badges in edit mode"
        );

        await selectDropdownItem(target, "partner_ids", "second record");
        //await testUtils.fields.many2one.clickOpenDropdown("partner_ids");
        //await testUtils.fields.many2one.clickItem("partner_ids", "second record");
        await click(target.querySelector(".o_list_button_save"));
        assert.containsN(
            target,
            ".o_data_row:first-child .o_field_many2many_tags_avatar .o_tag",
            2,
            "should have 2 records"
        );
    });

    QUnit.test("widget many2many_tags_avatar in kanban view", async function (assert) {
        assert.expect(12);

        const records = [];
        for (let id = 5; id <= 15; id++) {
            records.push({
                id,
                display_name: `record ${id}`,
            });
        }
        serverData.models.partner.records = serverData.models.partner.records.concat(records);

        serverData.models.turtle.records.push({
            id: 4,
            display_name: "crime master gogo",
            turtle_bar: true,
            turtle_foo: "yop",
            partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        });
        serverData.models.turtle.records[0].partner_ids = [1];
        serverData.models.turtle.records[1].partner_ids = [1, 2, 4];
        serverData.models.turtle.records[2].partner_ids = [1, 2, 4, 5];
        serverData.views = {
            "turtle,false,form": '<form><field name="display_name"/></form>',
        };

        await makeView({
            type: "kanban",
            resModel: "turtle",
            serverData,
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
            selectRecord(recordId) {
                assert.equal(
                    recordId,
                    1,
                    "should call its selectRecord prop with the clicked record"
                );
            },
        });
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:first-child .o_field_many2many_tags_avatar img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );

        assert.containsN(
            target,
            ".o_kanban_record:nth-child(2) .o_field_many2many_tags_avatar .o_tag",
            3,
            "should have 3 records"
        );
        assert.containsN(
            target,
            ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_tags_list > span:not(.o_m2m_avatar_empty)",
            2,
            "should have 2 records"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target.querySelectorAll(
                ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar img.o_m2m_avatar"
            )[1].dataset.src,
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
                )
                .textContent.trim(),
            "+2",
            "should have +2 in o_m2m_avatar_empty"
        );

        assert.containsN(
            target,
            ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_tags_list > span:not(.o_m2m_avatar_empty)",
            2,
            "should have 2 records"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
                )
                .textContent.trim(),
            "9+",
            "should have 9+ in o_m2m_avatar_empty"
        );

        // check data-tooltip attribute (used by the tooltip service)
        const tag = target.querySelector(
            ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
        );
        assert.strictEqual(
            tag.dataset["tooltip"],
            "aaa<br/>record 5",
            "shows a tooltip on hover with the right text"
        );

        await click(
            target.querySelector(".o_kanban_record .o_field_many2many_tags_avatar img.o_m2m_avatar")
        );
    });
});
