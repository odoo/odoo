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

    QUnit.module("BinaryField");

    QUnit.skip("BinaryField is correctly rendered", async function (assert) {
        assert.expect(16);

        // save the session function
        var oldGetFile = session.get_file;
        session.get_file = function (option) {
            assert.strictEqual(
                option.data.field,
                "document",
                "we should download the field document"
            );
            assert.strictEqual(
                option.data.data,
                "coucou==\n",
                "we should download the correct data"
            );
            option.complete();
            return Promise.resolve();
        };

        this.data.partner.records[0].foo = "coucou.txt";
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="document" filename="foo"/>' +
                '<field name="foo"/>' +
                "</form>",
            res_id: 1,
        });

        assert.containsOnce(
            form,
            'a.o_field_widget[name="document"] > .fa-download',
            "the binary field should be rendered as a downloadable link in readonly"
        );
        assert.strictEqual(
            form.$('a.o_field_widget[name="document"]').text().trim(),
            "coucou.txt",
            "the binary field should display the name of the file in the link"
        );
        assert.strictEqual(
            form.$(".o_field_char").text(),
            "coucou.txt",
            "the filename field should have the file name as value"
        );

        await testUtils.dom.click(form.$('a.o_field_widget[name="document"]'));

        await testUtils.form.clickEdit(form);

        assert.containsNone(
            form,
            'a.o_field_widget[name="document"] > .fa-download',
            "the binary field should not be rendered as a downloadable link in edit"
        );
        assert.strictEqual(
            form.$('div.o_field_binary_file[name="document"] > input').val(),
            "coucou.txt",
            "the binary field should display the file name in the input edit mode"
        );
        assert.hasAttrValue(
            form.$(".o_field_binary_file > input"),
            "readonly",
            "readonly",
            "the input should be readonly"
        );
        assert.containsOnce(
            form,
            ".o_field_binary_file > .o_clear_file_button",
            "there shoud be a button to clear the file"
        );
        assert.strictEqual(
            form.$("input.o_field_char").val(),
            "coucou.txt",
            "the filename field should have the file name as value"
        );

        await testUtils.dom.click(form.$(".o_field_binary_file > .o_clear_file_button"));

        assert.isNotVisible(form.$(".o_field_binary_file > input"), "the input should be hidden");
        assert.strictEqual(
            form.$(".o_field_binary_file > .o_select_file_button:not(.o_hidden)").length,
            1,
            "there shoud be a button to upload the file"
        );
        assert.strictEqual(
            form.$("input.o_field_char").val(),
            "",
            "the filename field should be empty since we removed the file"
        );

        await testUtils.form.clickSave(form);
        assert.containsNone(
            form,
            'a.o_field_widget[name="document"] > .fa-download',
            "the binary field should not render as a downloadable link since we removed the file"
        );
        assert.strictEqual(
            form.$('a.o_field_widget[name="document"]').text().trim(),
            "",
            "the binary field should not display a filename in the link since we removed the file"
        );
        assert.strictEqual(
            form.$(".o_field_char").text().trim(),
            "",
            "the filename field should be empty since we removed the file"
        );

        form.destroy();

        // restore the session function
        session.get_file = oldGetFile;
    });

    QUnit.skip("BinaryField: option accepted_file_extensions", async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form string="Partners">
                      <field name="document" widget="binary" options="{'accepted_file_extensions': '.dat,.bin'}"/>
                   </form>`,
        });
        assert.strictEqual(
            form.$("input.o_input_file").attr("accept"),
            ".dat,.bin",
            "the input should have the correct ``accept`` attribute"
        );
        form.destroy();
    });

    QUnit.skip(
        "BinaryField that is readonly in create mode does not download",
        async function (assert) {
            assert.expect(4);

            // save the session function
            var oldGetFile = session.get_file;
            session.get_file = function (option) {
                assert.step("We shouldn't be getting the file.");
                return oldGetFile.bind(session)(option);
            };

            this.data.partner.onchanges = {
                product_id: function (obj) {
                    obj.document = "onchange==\n";
                },
            };

            this.data.partner.fields.document.readonly = true;

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="product_id"/>' +
                    '<field name="document" filename="\'yooo\'"/>' +
                    "</form>",
                res_id: 1,
            });

            await testUtils.form.clickCreate(form);
            await testUtils.fields.many2one.clickOpenDropdown("product_id");
            await testUtils.fields.many2one.clickHighlightedItem("product_id");

            assert.containsOnce(
                form,
                'a.o_field_widget[name="document"]',
                "The link to download the binary should be present"
            );
            assert.containsNone(
                form,
                'a.o_field_widget[name="document"] > .fa-download',
                "The download icon should not be present"
            );

            var link = form.$('a.o_field_widget[name="document"]');
            assert.ok(link.is(":hidden"), "the link element should not be visible");

            // force visibility to test that the clicking has also been disabled
            link.removeClass("o_hidden");
            testUtils.dom.click(link);

            assert.verifySteps([]); // We shouldn't have passed through steps

            form.destroy();
            session.get_file = oldGetFile;
        }
    );
});
