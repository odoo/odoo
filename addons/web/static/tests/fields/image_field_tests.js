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

    QUnit.module("ImageField");

    QUnit.skip("ImageField is correctly rendered", async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].__last_update = "2017-02-08 10:00:00";
        this.data.partner.records[0].document = MY_IMAGE;

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="document" widget="image" options="{\'size\': [90, 90]}"/> ' +
                "</form>",
            res_id: 1,
            async mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/read") {
                    assert.deepEqual(
                        args.args[1],
                        ["document", "__last_update", "display_name"],
                        "The fields document, display_name and __last_update should be present when reading an image"
                    );
                }
                if (route === `data:image/png;base64,${MY_IMAGE}`) {
                    assert.ok(true, "should called the correct route");
                    return "wow";
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.hasClass(
            form.$('div[name="document"]'),
            "o_field_image",
            "the widget should have the correct class"
        );
        assert.containsOnce(
            form,
            'div[name="document"] > img',
            "the widget should contain an image"
        );
        assert.hasClass(
            form.$('div[name="document"] > img'),
            "img-fluid",
            "the image should have the correct class"
        );
        assert.hasAttrValue(
            form.$('div[name="document"] > img'),
            "width",
            "90",
            "the image should correctly set its attributes"
        );
        assert.strictEqual(
            form.$('div[name="document"] > img').css("max-width"),
            "90px",
            "the image should correctly set its attributes"
        );
        form.destroy();
    });

    QUnit.skip(
        "ImageField is correctly replaced when given an incorrect value",
        async function (assert) {
            assert.expect(7);

            this.data.partner.records[0].__last_update = "2017-02-08 10:00:00";
            this.data.partner.records[0].document = "incorrect_base64_value";

            testUtils.mock.patch(basicFields.FieldBinaryImage, {
                // Delay the _render function: this will ensure that the error triggered
                // by the incorrect base64 value is dispatched before the src is replaced
                // (see test_utils_mock.removeSrcAttribute), since that function is called
                // when the element is inserted into the DOM.
                async _render() {
                    const result = this._super.apply(this, arguments);
                    await concurrency.delay(100);
                    return result;
                },
            });

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `
                <form string="Partners">
                    <field name="document" widget="image" options="{'size': [90, 90]}"/>
                </form>`,
                res_id: 1,
                async mockRPC(route, args) {
                    const _super = this._super;
                    if (route === "/web/static/img/placeholder.png") {
                        assert.step("call placeholder route");
                    }
                    return _super.apply(this, arguments);
                },
            });

            assert.hasClass(
                form.$('div[name="document"]'),
                "o_field_image",
                "the widget should have the correct class"
            );
            assert.containsOnce(
                form,
                'div[name="document"] > img',
                "the widget should contain an image"
            );
            assert.hasClass(
                form.$('div[name="document"] > img'),
                "img-fluid",
                "the image should have the correct class"
            );
            assert.hasAttrValue(
                form.$('div[name="document"] > img'),
                "width",
                "90",
                "the image should correctly set its attributes"
            );
            assert.strictEqual(
                form.$('div[name="document"] > img').css("max-width"),
                "90px",
                "the image should correctly set its attributes"
            );

            assert.verifySteps(["call placeholder route"]);

            form.destroy();
            testUtils.mock.unpatch(basicFields.FieldBinaryImage);
        }
    );

    QUnit.skip("ImageField: option accepted_file_extensions", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form string="Partners">
                      <field name="document" widget="image" options="{'accepted_file_extensions': '.png,.jpeg'}"/>
                   </form>`,
        });
        assert.strictEqual(
            form.$("input.o_input_file").attr("accept"),
            ".png,.jpeg",
            "the input should have the correct ``accept`` attribute"
        );
        form.destroy();

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form string="Partners">
                      <field name="document" widget="image"/>
                   </form>`,
        });
        assert.strictEqual(
            form.$("input.o_input_file").attr("accept"),
            "image/*",
            'the default value for the attribute "accept" on the "image" widget must be "image/*"'
        );
        form.destroy();
    });

    QUnit.skip("ImageField in subviews is loaded correctly", async function (assert) {
        assert.expect(6);

        this.data.partner.records[0].__last_update = "2017-02-08 10:00:00";
        this.data.partner.records[0].document = MY_IMAGE;
        this.data.partner_type.fields.image = { name: "image", type: "binary" };
        this.data.partner_type.records[0].image = PRODUCT_IMAGE;
        this.data.partner.records[0].timmy = [12];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="document" widget="image" options="{\'size\': [90, 90]}"/>' +
                '<field name="timmy" widget="many2many" mode="kanban">' +
                // use kanban view as the tree will trigger edit mode
                // and thus won't display the field
                "<kanban>" +
                '<field name="display_name"/>' +
                "<templates>" +
                '<t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click">' +
                '<span><t t-esc="record.display_name.value"/></span>' +
                "</div>" +
                "</t>" +
                "</templates>" +
                "</kanban>" +
                "<form>" +
                '<field name="image" widget="image"/>' +
                "</form>" +
                "</field>" +
                "</form>",
            res_id: 1,
            async mockRPC(route) {
                if (route === `data:image/png;base64,${MY_IMAGE}`) {
                    assert.step("The view's image should have been fetched");
                    return "wow";
                }
                if (route === `data:image/gif;base64,${PRODUCT_IMAGE}`) {
                    assert.step("The dialog's image should have been fetched");
                    return;
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.verifySteps(["The view's image should have been fetched"]);

        assert.containsOnce(
            form,
            ".o_kanban_record.oe_kanban_global_click",
            "There should be one record in the many2many"
        );

        // Actual flow: click on an element of the m2m to get its form view
        await testUtils.dom.click(form.$(".oe_kanban_global_click"));
        assert.strictEqual($(".modal").length, 1, "The modal should have opened");
        assert.verifySteps(["The dialog's image should have been fetched"]);

        form.destroy();
    });

    QUnit.skip("ImageField in x2many list is loaded correctly", async function (assert) {
        assert.expect(2);

        this.data.partner_type.fields.image = { name: "image", type: "binary" };
        this.data.partner_type.records[0].image = PRODUCT_IMAGE;
        this.data.partner.records[0].timmy = [12];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="timmy" widget="many2many">' +
                "<tree>" +
                '<field name="image" widget="image"/>' +
                "</tree>" +
                "</field>" +
                "</form>",
            res_id: 1,
            async mockRPC(route) {
                if (route === `data:image/gif;base64,${PRODUCT_IMAGE}`) {
                    assert.ok(true, "The list's image should have been fetched");
                    return;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(form, "tr.o_data_row", "There should be one record in the many2many");

        form.destroy();
    });

    QUnit.skip("ImageField with required attribute", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="document" required="1" widget="image"/>' +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "create") {
                    throw new Error("Should not do a create RPC with unset required image field");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.form.clickSave(form);

        assert.hasClass(
            form.$(".o_form_view"),
            "o_form_editable",
            "form view should still be editable"
        );
        assert.hasClass(
            form.$(".o_field_widget"),
            "o_field_invalid",
            "image field should be displayed as invalid"
        );

        form.destroy();
    });
});
