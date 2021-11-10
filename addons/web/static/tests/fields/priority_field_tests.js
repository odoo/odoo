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

    QUnit.module("PriorityField");

    QUnit.skip("PriorityField when not set", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="selection" widget="priority"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 2,
        });

        assert.strictEqual(
            form.$(".o_field_widget.o_priority:not(.o_field_empty)").length,
            1,
            "widget should be considered set, even though there is no value for this field"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star").length,
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star").length,
            0,
            "should have no full star since there is no value"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star-o").length,
            2,
            "should have two empty stars since there is no value"
        );

        form.destroy();
    });

    QUnit.skip("PriorityField in form view", async function (assert) {
        assert.expect(22);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="selection" widget="priority"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        assert.strictEqual(
            form.$(".o_field_widget.o_priority:not(.o_field_empty)").length,
            1,
            "widget should be considered set"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star").length,
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star").length,
            1,
            "should have one full star since the value is the second value"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star-o").length,
            1,
            "should have one empty star since the value is the second value"
        );

        // hover last star
        form.$(".o_field_widget.o_priority a.o_priority_star.fa-star-o")
            .last()
            .trigger("mouseover");
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star").length,
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star").length,
            2,
            "should temporary have two full stars since we are hovering the third value"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star-o").length,
            0,
            "should temporary have no empty star since we are hovering the third value"
        );

        // Here we should test with mouseout, but currently the effect associated with it
        // occurs in a setTimeout after 200ms so it's not trivial to test it here.

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star").length,
            1,
            "should still have one full star since the value is the second value"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star-o").length,
            1,
            "should still have one empty star since the value is the second value"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star").length,
            1,
            "should still have one full star since the value is the second value"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star-o").length,
            1,
            "should still have one empty star since the value is the second value"
        );

        // switch to edit mode to check that the new value was properly written
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star").length,
            1,
            "should still have one full star since the value is the second value"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star-o").length,
            1,
            "should still have one empty star since the value is the second value"
        );

        // click on the second star in edit mode
        await testUtils.dom.click(
            form.$(".o_field_widget.o_priority a.o_priority_star.fa-star-o").last()
        );

        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star").length,
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star-o").length,
            0,
            "should now have no empty star since the value is the third value"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star").length,
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.strictEqual(
            form.$(".o_field_widget.o_priority").find("a.o_priority_star.fa-star-o").length,
            0,
            "should now have no empty star since the value is the third value"
        );

        form.destroy();
    });

    QUnit.skip("PriorityField in editable list view", async function (assert) {
        assert.expect(25);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom"><field name="selection" widget="priority"/></tree>',
        });

        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority:not(.o_field_empty)").length,
            1,
            "widget should be considered set"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star").length,
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star").length,
            1,
            "should have one full star since the value is the second value"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star-o").length,
            1,
            "should have one empty star since the value is the second value"
        );

        // Here we should test with mouseout, but currently the effect associated with it
        // occurs in a setTimeout after 200ms so it's not trivial to test it here.

        // switch to edit mode and check the result
        var $cell = list.$("tbody td:not(.o_list_record_selector)").first();
        await testUtils.dom.click($cell);
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star").length,
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star").length,
            1,
            "should have one full star since the value is the second value"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star-o").length,
            1,
            "should have one empty star since the value is the second value"
        );

        // save
        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star").length,
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star").length,
            1,
            "should have one full star since the value is the second value"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star-o").length,
            1,
            "should have one empty star since the value is the second value"
        );

        // hover last star
        list.$(".o_data_row .o_priority a.o_priority_star.fa-star-o").first().trigger("mouseenter");
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star").length,
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find("a.o_priority_star.fa-star").length,
            2,
            "should temporary have two full stars since we are hovering the third value"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find("a.o_priority_star.fa-star-o").length,
            0,
            "should temporary have no empty star since we are hovering the third value"
        );

        // click on the first star in readonly mode
        await testUtils.dom.click(list.$(".o_priority a.o_priority_star.fa-star").first());

        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star").length,
            0,
            "should now have no full star since the value is the first value"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star-o").length,
            2,
            "should now have two empty stars since the value is the first value"
        );

        // re-enter edit mode to force re-rendering the widget to check if the value was correctly saved
        $cell = list.$("tbody td:not(.o_list_record_selector)").first();
        await testUtils.dom.click($cell);

        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star").length,
            0,
            "should now only have no full star since the value is the first value"
        );
        assert.strictEqual(
            list.$(".o_data_row").first().find(".o_priority a.o_priority_star.fa-star-o").length,
            2,
            "should now have two empty stars since the value is the first value"
        );

        // Click on second star in edit mode
        await testUtils.dom.click(list.$(".o_priority a.o_priority_star.fa-star-o").last());

        assert.strictEqual(
            list.$(".o_data_row").last().find(".o_priority a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            list.$(".o_data_row").last().find(".o_priority a.o_priority_star.fa-star").length,
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.strictEqual(
            list.$(".o_data_row").last().find(".o_priority a.o_priority_star.fa-star-o").length,
            0,
            "should now have no empty star since the value is the third value"
        );

        // save
        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.strictEqual(
            list.$(".o_data_row").last().find(".o_priority a.o_priority_star").length,
            2,
            "should still have two stars"
        );
        assert.strictEqual(
            list.$(".o_data_row").last().find(".o_priority a.o_priority_star.fa-star").length,
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.strictEqual(
            list.$(".o_data_row").last().find(".o_priority a.o_priority_star.fa-star-o").length,
            0,
            "should now have no empty star since the value is the third value"
        );

        list.destroy();
    });

    QUnit.skip("PriorityField with readonly attribute", async function (assert) {
        assert.expect(1);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form>
                    <field name="selection" widget="priority" readonly="1"/>
                </form>`,
            res_id: 2,
        });

        assert.containsN(
            form,
            ".o_field_widget.o_priority span",
            2,
            "stars of priority widget should rendered with span tag if readonly"
        );

        form.destroy();
    });

    QUnit.skip(
        'PriorityField edited by the smart action "Set priority..."',
        async function (assert) {
            assert.expect(4);

            const legacyEnv = makeTestEnvironment({ bus: core.bus });
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

            const views = {
                "partner,false,form":
                    "<form>" + '<field name="selection" widget="priority"/>' + "</form>",
                "partner,false,search": "<search></search>",
            };
            const serverData = { models: this.data, views };
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                res_id: 1,
                type: "ir.actions.act_window",
                target: "current",
                res_model: "partner",
                view_mode: "form",
                views: [[false, "form"]],
            });
            assert.containsOnce(webClient, ".fa-star");

            triggerHotkey("control+k");
            await nextTick();
            const idx = [...webClient.el.querySelectorAll(".o_command")]
                .map((el) => el.textContent)
                .indexOf("Set priority...ALT + R");
            assert.ok(idx >= 0);

            await click([...webClient.el.querySelectorAll(".o_command")][idx]);
            await nextTick();
            assert.deepEqual(
                [...webClient.el.querySelectorAll(".o_command")].map((el) => el.textContent),
                ["Normal", "Blocked", "Done"]
            );
            await click(webClient.el, "#o_command_2");
            await legacyExtraNextTick();
            assert.containsN(webClient, ".fa-star", 2);
        }
    );
});
