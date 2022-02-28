/** @odoo-module **/

import { click, getFixture } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;
const FR_FLAG_URL = "/base/static/img/country_flags/fr.png";
const EN_FLAG_URL = "/base/static/img/country_flags/gb.png";

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
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

        setupViewRegistries();
    });

    /**
     * Same tests than for Image fields, but for Char fields with image_url widget.
     */
    QUnit.module("ImageUrlField", {
        beforeEach: function () {
            // specific sixth partner data for image_url widget tests
            serverData.models.partner.records.push({
                id: 6,
                bar: false,
                foo: FR_FLAG_URL,
                int_field: 5,
                qux: 0.0,
                timmy: [],
            });
        },
    });

    QUnit.test("image fields are correctly rendered", async function (assert) {
        assert.expect(6);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
                </form>`,
            resId: 6,
        });

        assert.hasClass(
            target.querySelector('div[name="foo"]'),
            "o_field_image_url",
            "the widget should have the correct class"
        );
        assert.containsOnce(form, 'div[name="foo"] > img', "the widget should contain an image");
        assert.strictEqual(
            target.querySelector('div[name="foo"] > img')[0].dataset.src,
            FR_FLAG_URL,
            "the image should have the correct src"
        );
        assert.hasClass(
            target.querySelector('div[name="foo"] > img'),
            "img-fluid",
            "the image should have the correct class"
        );
        assert.hasAttrValue(
            target.querySelector('div[name="foo"] > img'),
            "width",
            "90",
            "the image should correctly set its attributes"
        );
        assert.strictEqual(
            target.querySelector('div[name="foo"] > img').style.maxWidth,
            "90px",
            "the image should correctly set its attributes"
        );
    });

    QUnit.skipWOWL("ImageUrlField in subviews are loaded correctly", async function (assert) {
        assert.expect(4);

        serverData.models.partner_type.fields.image = { name: "image", type: "char" };
        serverData.models.partner_type.records[0].image = EN_FLAG_URL;
        serverData.models.partner.records[5].timmy = [12];

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
                    <field name="timmy" widget="many2many" mode="kanban">
                    <!-- use kanban view as the tree will trigger edit mode -->
                    <!-- and thus won't display the field -->
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
                            <field name="image" widget="image_url"/>
                        </form>
                    </field>
                </form>`,
            resId: 6,
        });

        assert.ok(
            document.querySelector(`img[data-src="${FR_FLAG_URL}"]`),
            "The view's image is in the DOM"
        );
        assert.containsOnce(
            form,
            ".o_kanban_record.oe_kanban_global_click",
            "There should be one record in the many2many"
        );

        // Actual flow: click on an element of the m2m to get its form view
        await click(target.querySelector(".oe_kanban_global_click"));
        assert.containsOnce(document.body, ".modal", "The modal should have opened");

        assert.ok(
            document.querySelector(`img[data-src="${EN_FLAG_URL}"]`),
            "The dialog's image is in the DOM"
        );
    });

    QUnit.test("image fields in x2many list are loaded correctly", async function (assert) {
        assert.expect(2);

        serverData.models.partner_type.fields.image = { name: "image", type: "char" };
        serverData.models.partner_type.records[0].image = EN_FLAG_URL;
        serverData.models.partner.records[5].timmy = [12];

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="timmy" widget="many2many">
                        <tree>
                            <field name="image" widget="image_url"/>
                        </tree>
                    </field>
                </form>`,
            resId: 6,
        });

        assert.containsOnce(form, "tr.o_data_row", "There should be one record in the many2many");
        assert.ok(
            document.querySelector(`img[data-src="${EN_FLAG_URL}"]`),
            "The list's image is in the DOM"
        );
    });
});
