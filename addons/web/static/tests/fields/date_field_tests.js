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

    QUnit.module("DateField");

    QUnit.skip("DateField: toggle datepicker [REQUIRE FOCUS]", async function (assert) {
        assert.expect(3);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="foo"/><field name="date"/></form>',
            translateParameters: {
                // Avoid issues due to localization formats
                date_format: "%m/%d/%Y",
            },
        });

        assert.strictEqual(
            $(".bootstrap-datetimepicker-widget:visible").length,
            0,
            "datepicker should be closed initially"
        );

        await testUtils.dom.openDatepicker(form.$(".o_datepicker"));

        assert.strictEqual(
            $(".bootstrap-datetimepicker-widget:visible").length,
            1,
            "datepicker should be opened"
        );

        // focus another field
        await testUtils.dom.click(form.$(".o_field_widget[name=foo]").focus().mouseenter());

        assert.strictEqual(
            $(".bootstrap-datetimepicker-widget:visible").length,
            0,
            "datepicker should close itself when the user clicks outside"
        );

        form.destroy();
    });

    QUnit.skip("DateField: toggle datepicker far in the future", async function (assert) {
        assert.expect(3);

        this.data.partner.records = [
            {
                id: 1,
                date: "9999-12-30",
                foo: "yop",
            },
        ];

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="foo"/><field name="date"/></form>',
            translateParameters: {
                // Avoid issues due to localization formats
                date_format: "%m/%d/%Y",
            },
            res_id: 1,
            viewOptions: {
                mode: "edit",
            },
        });

        assert.strictEqual(
            $(".bootstrap-datetimepicker-widget:visible").length,
            0,
            "datepicker should be closed initially"
        );

        testUtils.dom.openDatepicker(form.$(".o_datepicker"));

        assert.strictEqual(
            $(".bootstrap-datetimepicker-widget:visible").length,
            1,
            "datepicker should be opened"
        );

        // focus another field
        form.$(".o_field_widget[name=foo]").click().focus();

        assert.strictEqual(
            $(".bootstrap-datetimepicker-widget:visible").length,
            0,
            "datepicker should close itself when the user clicks outside"
        );

        form.destroy();
    });

    QUnit.skip("date field is empty if no date is set", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="date"/></form>',
            res_id: 4,
        });
        var $span = form.$("span.o_field_widget");
        assert.strictEqual($span.length, 1, "should have one span in the form view");
        assert.strictEqual($span.text(), "", "and it should be empty");
        form.destroy();
    });

    QUnit.skip(
        "DateField: set an invalid date when the field is already set",
        async function (assert) {
            assert.expect(2);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: '<form string="Partners"><field name="date"/></form>',
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            var $input = form.$(".o_field_widget[name=date] input");

            assert.strictEqual($input.val(), "02/03/2017");

            $input.val("mmmh").trigger("change");
            assert.strictEqual($input.val(), "02/03/2017", "should have reset the original value");

            form.destroy();
        }
    );

    QUnit.skip(
        "DateField: set an invalid date when the field is not set yet",
        async function (assert) {
            assert.expect(2);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: '<form string="Partners"><field name="date"/></form>',
                res_id: 4,
                viewOptions: {
                    mode: "edit",
                },
            });

            var $input = form.$(".o_field_widget[name=date] input");

            assert.strictEqual($input.text(), "");

            $input.val("mmmh").trigger("change");
            assert.strictEqual($input.text(), "", "The date field should be empty");

            form.destroy();
        }
    );

    QUnit.skip("DateField value should not set on first click", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="date"/></form>',
            res_id: 4,
        });

        await testUtils.form.clickEdit(form);

        // open datepicker and select a date
        testUtils.dom.openDatepicker(form.$(".o_datepicker"));
        assert.strictEqual(
            form.$(".o_datepicker_input").val(),
            "",
            "date field's input should be empty on first click"
        );
        testUtils.dom.click($(".day:contains(22)"));

        // re-open datepicker
        testUtils.dom.openDatepicker(form.$(".o_datepicker"));
        assert.strictEqual(
            $(".day.active").text(),
            "22",
            "datepicker should be highlight with 22nd day of month"
        );

        form.destroy();
    });

    QUnit.skip("DateField in form view (with positive time zone offset)", async function (assert) {
        assert.expect(8);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="date"/></form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(
                        args.args[1].date,
                        "2017-02-22",
                        "the correct value should be saved"
                    );
                }
                return this._super.apply(this, arguments);
            },
            translateParameters: {
                // Avoid issues due to localization formats
                date_format: "%m/%d/%Y",
            },
            session: {
                getTZOffset: function () {
                    return 120; // Should be ignored by date fields
                },
            },
        });

        assert.strictEqual(
            form.$(".o_field_date").text(),
            "02/03/2017",
            "the date should be correctly displayed in readonly"
        );

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_datepicker_input").val(),
            "02/03/2017",
            "the date should be correct in edit mode"
        );

        // open datepicker and select another value
        testUtils.dom.openDatepicker(form.$(".o_datepicker"));
        assert.ok($(".bootstrap-datetimepicker-widget").length, "datepicker should be open");
        assert.strictEqual(
            $(".day.active").data("day"),
            "02/03/2017",
            "datepicker should be highlight February 3"
        );
        testUtils.dom.click($(".bootstrap-datetimepicker-widget .picker-switch").first());
        testUtils.dom.click($(".bootstrap-datetimepicker-widget .picker-switch:eq(1)").first());
        testUtils.dom.click($(".bootstrap-datetimepicker-widget .year:contains(2017)"));
        testUtils.dom.click($(".bootstrap-datetimepicker-widget .month").eq(1));
        testUtils.dom.click($(".day:contains(22)"));
        assert.ok(!$(".bootstrap-datetimepicker-widget").length, "datepicker should be closed");
        assert.strictEqual(
            form.$(".o_datepicker_input").val(),
            "02/22/2017",
            "the selected date should be displayed in the input"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_date").text(),
            "02/22/2017",
            "the selected date should be displayed after saving"
        );
        form.destroy();
    });

    QUnit.skip("DateField in form view (with negative time zone offset)", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="date"/></form>',
            res_id: 1,
            translateParameters: {
                // Avoid issues due to localization formats
                date_format: "%m/%d/%Y",
            },
            session: {
                getTZOffset: function () {
                    return -120; // Should be ignored by date fields
                },
            },
        });

        assert.strictEqual(
            form.$(".o_field_date").text(),
            "02/03/2017",
            "the date should be correctly displayed in readonly"
        );

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_datepicker_input").val(),
            "02/03/2017",
            "the date should be correct in edit mode"
        );

        form.destroy();
    });

    QUnit.skip("DateField dropdown disappears on scroll", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<div class="scrollable" style="height: 2000px;">' +
                '<field name="date"/>' +
                "</div>" +
                "</form>",
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        await testUtils.dom.openDatepicker(form.$(".o_datepicker"));

        assert.containsOnce(
            $("body"),
            ".bootstrap-datetimepicker-widget",
            "datepicker should be opened"
        );

        form.el.dispatchEvent(new Event("wheel"));
        assert.containsNone(
            $("body"),
            ".bootstrap-datetimepicker-widget",
            "datepicker should be closed"
        );

        form.destroy();
    });

    QUnit.skip("DateField with warn_future option", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<field name=\"date\" options=\"{'datepicker': {'warn_future': true}}\"/>" +
                "</form>",
            res_id: 4,
        });

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        // open datepicker and select another value
        await testUtils.dom.openDatepicker(form.$(".o_datepicker"));
        await testUtils.dom.click($(".bootstrap-datetimepicker-widget .picker-switch").first());
        await testUtils.dom.click($(".bootstrap-datetimepicker-widget .picker-switch:eq(1)"));
        await testUtils.dom.click($(".bootstrap-datetimepicker-widget .year").eq(11));
        await testUtils.dom.click($(".bootstrap-datetimepicker-widget .month").eq(11));
        await testUtils.dom.click($(".day:contains(31)"));

        var $warn = form.$(".o_datepicker_warning:visible");
        assert.strictEqual($warn.length, 1, "should have a warning in the form view");

        await testUtils.fields.editSelect(form.$(".o_field_widget[name=date] input"), ""); // remove the value

        $warn = form.$(".o_datepicker_warning:visible");
        assert.strictEqual($warn.length, 0, "the warning in the form view should be hidden");

        form.destroy();
    });

    QUnit.skip(
        "DateField with warn_future option: do not overwrite datepicker option",
        async function (assert) {
            assert.expect(2);

            // Making sure we don't have a legit default value
            // or any onchange that would set the value
            this.data.partner.fields.date.default = undefined;
            this.data.partner.onchanges = {};

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="foo" />' + // Do not let the date field get the focus in the first place
                    "<field name=\"date\" options=\"{'datepicker': {'warn_future': true}}\"/>" +
                    "</form>",
                res_id: 1,
            });

            // switch to edit mode
            await testUtils.form.clickEdit(form);
            assert.strictEqual(
                form.$('input[name="date"]').val(),
                "02/03/2017",
                "The existing record should have a value for the date field"
            );

            // save with no changes
            await testUtils.form.clickSave(form);

            //Create a new record
            await testUtils.form.clickCreate(form);

            assert.notOk(
                form.$('input[name="date"]').val(),
                "The new record should not have a value that the framework would have set"
            );

            form.destroy();
        }
    );

    QUnit.skip("DateField in editable list view", async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom">' + '<field name="date"/>' + "</tree>",
            translateParameters: {
                // Avoid issues due to localization formats
                date_format: "%m/%d/%Y",
            },
            session: {
                getTZOffset: function () {
                    return 0;
                },
            },
        });

        var $cell = list.$("tr.o_data_row td:not(.o_list_record_selector)").first();
        assert.strictEqual(
            $cell.text(),
            "02/03/2017",
            "the date should be displayed correctly in readonly"
        );
        await testUtils.dom.click($cell);

        assert.containsOnce(
            list,
            "input.o_datepicker_input",
            "the view should have a date input for editable mode"
        );

        assert.strictEqual(
            list.$("input.o_datepicker_input").get(0),
            document.activeElement,
            "date input should have the focus"
        );

        assert.strictEqual(
            list.$("input.o_datepicker_input").val(),
            "02/03/2017",
            "the date should be correct in edit mode"
        );

        // open datepicker and select another value
        await testUtils.dom.openDatepicker(list.$(".o_datepicker"));
        assert.ok($(".bootstrap-datetimepicker-widget").length, "datepicker should be open");
        await testUtils.dom.click($(".bootstrap-datetimepicker-widget .picker-switch").first());
        await testUtils.dom.click($(".bootstrap-datetimepicker-widget .picker-switch:eq(1)"));
        await testUtils.dom.click($(".bootstrap-datetimepicker-widget .year:contains(2017)"));
        await testUtils.dom.click($(".bootstrap-datetimepicker-widget .month").eq(1));
        await testUtils.dom.click($(".day:contains(22)"));
        assert.ok(!$(".bootstrap-datetimepicker-widget").length, "datepicker should be closed");
        assert.strictEqual(
            list.$(".o_datepicker_input").val(),
            "02/22/2017",
            "the selected date should be displayed in the input"
        );

        // save
        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.strictEqual(
            list.$("tr.o_data_row td:not(.o_list_record_selector)").text(),
            "02/22/2017",
            "the selected date should be displayed after saving"
        );

        list.destroy();
    });

    QUnit.skip("DateField remove value", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="date"/></form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(
                        args.args[1].date,
                        false,
                        "the correct value should be saved"
                    );
                }
                return this._super.apply(this, arguments);
            },
            translateParameters: {
                // Avoid issues due to localization formats
                date_format: "%m/%d/%Y",
            },
        });

        // switch to edit mode
        await testUtils.form.clickEdit(form);
        assert.strictEqual(
            form.$(".o_datepicker_input").val(),
            "02/03/2017",
            "the date should be correct in edit mode"
        );

        await testUtils.fields.editAndTrigger(form.$(".o_datepicker_input"), "", [
            "input",
            "change",
            "focusout",
        ]);
        assert.strictEqual(
            form.$(".o_datepicker_input").val(),
            "",
            "should have correctly removed the value"
        );

        // save
        await testUtils.form.clickSave(form);
        assert.strictEqual(
            form.$(".o_field_date").text(),
            "",
            "the selected date should be displayed after saving"
        );

        form.destroy();
    });

    QUnit.skip(
        "do not trigger a field_changed for datetime field with date widget",
        async function (assert) {
            assert.expect(3);

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: '<form string="Partners"><field name="datetime" widget="date"/></form>',
                translateParameters: {
                    // Avoid issues due to localization formats
                    date_format: "%m/%d/%Y",
                    time_format: "%H:%M:%S",
                },
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            assert.strictEqual(
                form.$(".o_datepicker_input").val(),
                "02/08/2017",
                "the date should be correct"
            );

            testUtils.fields.editAndTrigger(form.$('input[name="datetime"]'), "02/08/2017", [
                "input",
                "change",
                "focusout",
            ]);
            await testUtils.form.clickSave(form);

            assert.verifySteps(["read"]); // should not have save as nothing changed

            form.destroy();
        }
    );

    QUnit.skip(
        "field date should select its content onclick when there is one",
        async function (assert) {
            assert.expect(3);
            var done = assert.async();

            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: '<form><field name="date"/></form>',
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            form.$el.on({
                "show.datetimepicker": function () {
                    assert.ok(
                        $(".bootstrap-datetimepicker-widget").is(":visible"),
                        "bootstrap-datetimepicker is visible"
                    );
                    const active = document.activeElement;
                    assert.equal(active.tagName, "INPUT", "The datepicker input should be focused");
                    const sel = active.value.slice(active.selectionStart, active.selectionEnd);
                    assert.strictEqual(
                        sel,
                        "02/03/2017",
                        "The whole input of the date field should have been selected"
                    );
                    done();
                },
            });

            testUtils.dom.openDatepicker(form.$(".o_datepicker"));

            form.destroy();
        }
    );

    QUnit.skip("DateField support internalization", async function (assert) {
        assert.expect(2);

        var originalLocale = moment.locale();
        var originalParameters = _.clone(core._t.database.parameters);

        _.extend(core._t.database.parameters, {
            date_format: "%d. %b %Y",
            time_format: "%H:%M:%S",
        });
        moment.defineLocale("norvegianForTest", {
            monthsShort: "jan._feb._mars_april_mai_juni_juli_aug._sep._okt._nov._des.".split("_"),
            monthsParseExact: true,
            dayOfMonthOrdinalParse: /\d{1,2}\./,
            ordinal: "%d.",
        });

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="date"/></form>',
            res_id: 1,
        });

        var dateViewForm = form.$(".o_field_date").text();
        await testUtils.dom.click(form.$buttons.find(".o_form_button_edit"));
        await testUtils.dom.openDatepicker(form.$(".o_datepicker"));
        assert.strictEqual(
            form.$(".o_datepicker_input").val(),
            dateViewForm,
            "input date field should be the same as it was in the view form"
        );

        await testUtils.dom.click($(".day:contains(30)"));
        var dateEditForm = form.$(".o_datepicker_input").val();
        await testUtils.dom.click(form.$buttons.find(".o_form_button_save"));
        assert.strictEqual(
            form.$(".o_field_date").text(),
            dateEditForm,
            "date field should be the same as the one selected in the view form"
        );

        moment.locale(originalLocale);
        moment.updateLocale("norvegianForTest", null);
        core._t.database.parameters = originalParameters;

        form.destroy();
    });

    QUnit.skip("DateField: hit enter should update value", async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form string="Partners"><field name="date"/></form>',
            res_id: 1,
            translateParameters: {
                // Avoid issues due to localization formats
                date_format: "%m/%d/%Y",
            },
            viewOptions: {
                mode: "edit",
            },
        });

        const year = new Date().getFullYear();

        await testUtils.fields.editInput(form.el.querySelector('input[name="date"]'), "01/08");
        await testUtils.fields.triggerKeydown(form.el.querySelector('input[name="date"]'), "enter");
        assert.strictEqual(form.el.querySelector('input[name="date"]').value, "01/08/" + year);

        await testUtils.fields.editInput(form.el.querySelector('input[name="date"]'), "08/01");
        await testUtils.fields.triggerKeydown(form.el.querySelector('input[name="date"]'), "enter");
        assert.strictEqual(form.el.querySelector('input[name="date"]').value, "08/01/" + year);

        form.destroy();
    });
});
