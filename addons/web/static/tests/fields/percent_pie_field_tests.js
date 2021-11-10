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

    QUnit.module("PercentPieField");

    QUnit.skip("PercentPieField in form view with value < 50%", async function (assert) {
        assert.expect(12);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="int_field" widget="percentpie"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        assert.containsOnce(
            form,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value").text(),
            "10%",
            "should have 10% as pie value since int_field=10"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").first().attr("style"),
                "transform: rotate(180deg);"
            ),
            "left mask should be covering the whole left side of the pie"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").last().attr("style"),
                "transform: rotate(36deg);"
            ),
            "right mask should be rotated from 360*(10/100) = 36 degrees"
        );

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value").text(),
            "10%",
            "should have 10% as pie value since int_field=10"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").first().attr("style"),
                "transform: rotate(180deg);"
            ),
            "left mask should be covering the whole left side of the pie"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").last().attr("style"),
                "transform: rotate(36deg);"
            ),
            "right mask should be rotated from 360*(10/100) = 36 degrees"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(
            form,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value").text(),
            "10%",
            "should have 10% as pie value since int_field=10"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").first().attr("style"),
                "transform: rotate(180deg);"
            ),
            "left mask should be covering the whole left side of the pie"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").last().attr("style"),
                "transform: rotate(36deg);"
            ),
            "right mask should be rotated from 360*(10/100) = 36 degrees"
        );

        form.destroy();
    });

    QUnit.skip("PercentPieField in form view with value > 50%", async function (assert) {
        assert.expect(12);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="int_field" widget="percentpie"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 3,
        });

        assert.containsOnce(
            form,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value").text(),
            "80%",
            "should have 80% as pie value since int_field=80"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").first().attr("style"),
                "transform: rotate(288deg);"
            ),
            "left mask should be rotated from 360*(80/100) = 288 degrees"
        );
        assert.hasClass(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").last(),
            "o_full",
            "right mask should be hidden since the value > 50%"
        );

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value").text(),
            "80%",
            "should have 80% as pie value since int_field=80"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").first().attr("style"),
                "transform: rotate(288deg);"
            ),
            "left mask should be rotated from 360*(80/100) = 288 degrees"
        );
        assert.hasClass(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").last(),
            "o_full",
            "right mask should be hidden since the value > 50%"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(
            form,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value").text(),
            "80%",
            "should have 80% as pie value since int_field=80"
        );
        assert.ok(
            _.str.include(
                form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").first().attr("style"),
                "transform: rotate(288deg);"
            ),
            "left mask should be rotated from 360*(80/100) = 288 degrees"
        );
        assert.hasClass(
            form.$(".o_field_percent_pie.o_field_widget .o_pie .o_mask").last(),
            "o_full",
            "right mask should be hidden since the value > 50%"
        );

        form.destroy();
    });

    // TODO: This test would pass without any issue since all the classes and
    //       custom style attributes are correctly set on the widget in list
    //       view, but since the scss itself for this widget currently only
    //       applies inside the form view, the widget is unusable. This test can
    //       be uncommented when we refactor the scss files so that this widget
    //       stylesheet applies in both form and list view.
    // QUnit.skip('percentpie widget in editable list view', async function(assert) {
    //     assert.expect(10);
    //
    //     var list = await createView({
    //         View: ListView,
    //         model: 'partner',
    //         data: this.data,
    //         arch: '<tree editable="bottom">' +
    //                 '<field name="foo"/>' +
    //                 '<field name="int_field" widget="percentpie"/>' +
    //               '</tree>',
    //     });
    //
    //     assert.containsN(list, '.o_field_percent_pie .o_pie', 5,
    //         "should have five pie charts");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole left side of the pie");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     // switch to edit mode and check the result
    //    testUtils.dom.click(     list.$('tbody td:not(.o_list_record_selector)').first());
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole right side of the pie");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     // save
    //    testUtils.dom.click(     list.$buttons.find('.o_list_button_save'));
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_pie_value').first().text(),
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').first().attr('style'),
    //         'transform: rotate(180deg);', "left mask should be covering the whole right side of the pie");
    //     assert.strictEqual(list.$('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'transform: rotate(36deg);', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     list.destroy();
    // });
});
