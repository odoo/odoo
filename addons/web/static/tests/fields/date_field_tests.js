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
                        resId: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            resId: 37,
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

    QUnit.test("DateField: toggle datepicker [REQUIRE FOCUS]", async function (assert) {
        assert.expect(3);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo" />
                    <field name="date" />
                </form>
            `,
        });
        assert.containsNone(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should be closed initially"
        );

        await click(form.el, ".o_datepicker input");
        assert.containsOnce(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should be opened"
        );

        // focus another field
        form.el.querySelector(".o_field_widget[name='foo']").focus();
        assert.containsNone(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should close itself when the user clicks outside"
        );
    });

    QUnit.test("DateField: toggle datepicker far in the future", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records = [
            {
                id: 1,
                date: "9999-12-30",
                foo: "yop",
            },
        ];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" />
                    <field name="date" />
                </form>
            `,
        });

        await click(form.el, ".o_form_button_edit");
        assert.containsNone(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should be closed initially"
        );

        await click(form.el, ".o_datepicker input");
        assert.containsOnce(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should be opened"
        );

        // focus another field
        form.el.querySelector(".o_field_widget[name='foo']").focus();
        assert.containsNone(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should close itself when the user clicks outside"
        );
    });

    QUnit.test("date field is empty if no date is set", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 4,
            serverData,
            arch: `
                <form>
                    <field name="date" />
                </form>
            `,
        });

        assert.containsOnce(
            form.el,
            "span.o_field_widget",
            "should have one span in the form view"
        );
        assert.strictEqual(
            form.el.querySelector("span.o_field_widget").textContent,
            "",
            "and it should be empty"
        );
    });

    QUnit.test(
        "DateField: set an invalid date when the field is already set",
        async function (assert) {
            assert.expect(2);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="date" />
                    </form>
                `,
            });
            await click(form.el, ".o_form_button_edit");

            const input = form.el.querySelector(".o_field_widget[name='date'] input");
            assert.strictEqual(input.value, "02/03/2017");

            input.value = "mmmh";
            await triggerEvent(input, null, "change");
            assert.strictEqual(input.value, "02/03/2017", "should have reset the original value");
        }
    );

    QUnit.test(
        "DateField: set an invalid date when the field is not set yet",
        async function (assert) {
            assert.expect(2);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 4,
                serverData,
                arch: `
                    <form>
                        <field name="date" />
                    </form>
                `,
            });
            await click(form.el, ".o_form_button_edit");

            const input = form.el.querySelector(".o_field_widget[name='date'] input");
            assert.strictEqual(input.value, "");

            input.value = "mmmh";
            await triggerEvent(input, null, "change");
            assert.strictEqual(input.value, "", "The date field should be empty");
        }
    );

    QUnit.test("DateField value should not set on first click", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 4,
            serverData,
            arch: `
                <form>
                    <field name="date" />
                </form>
            `,
        });
        await click(form.el, ".o_form_button_edit");

        await click(form.el, ".o_datepicker input");
        // open datepicker and select a date
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='date'] input").value,
            "",
            "date field's input should be empty on first click"
        );
        await click(document.body, ".day[data-day*='/22/']");

        // re-open datepicker
        await click(form.el, ".o_datepicker input");
        assert.strictEqual(
            document.body.querySelector(".day.active").textContent,
            "22",
            "datepicker should be highlight with 22nd day of month"
        );
    });

    QUnit.skip("DateField in form view (with positive time zone offset)", async function (assert) {
        assert.expect(8);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="date"/></form>',
            resId: 1,
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

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="date"/></form>',
            resId: 1,
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

    QUnit.test("DateField dropdown disappears on scroll", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <div class="scrollable" style="height: 2000px;">
                        <field name="date" />
                    </div>
                </form>
            `,
        });
        await click(form.el, ".o_form_button_edit");

        await click(form.el, ".o_datepicker input");
        assert.containsOnce(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should be opened"
        );

        await triggerEvent(form.el, null, "scroll");
        assert.containsNone(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should be closed"
        );
    });

    QUnit.test("DateField with warn_future option", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 4,
            serverData,
            arch: `
                <form>
                    <field name="date" options="{ 'datepicker': { 'warn_future': true } }" />
                </form>
            `,
        });
        // switch to edit mode
        await click(form.el, ".o_form_button_edit");

        // open datepicker and select another value
        await click(form.el, ".o_datepicker input");
        await click(
            document.body.querySelectorAll(".bootstrap-datetimepicker-widget .picker-switch")[0]
        );
        await click(
            document.body.querySelectorAll(".bootstrap-datetimepicker-widget .picker-switch")[1]
        );
        await click(document.body.querySelectorAll(".bootstrap-datetimepicker-widget .year")[11]);
        await click(document.body.querySelectorAll(".bootstrap-datetimepicker-widget .month")[11]);
        await click(document.body, ".day[data-day*='/31/']");

        assert.containsOnce(
            form.el,
            ".o_datepicker_warning",
            "should have a warning in the form view"
        );

        const input = form.el.querySelector(".o_field_widget[name='date'] input");
        input.value = "";
        await triggerEvent(input, null, "change"); // remove the value

        assert.containsNone(
            form.el,
            ".o_datepicker_warning",
            "the warning in the form view should be hidden"
        );
    });

    QUnit.test(
        "DateField with warn_future option: do not overwrite datepicker option",
        async function (assert) {
            assert.expect(2);

            // Making sure we don't have a legit default value
            // or any onchange that would set the value
            serverData.models.partner.fields.date.default = undefined;
            serverData.models.partner.onchanges = {};

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="foo" /> <!-- Do not let the date field get the focus in the first place -->
                        <field name="date" options="{ 'datepicker': { 'warn_future': true } }" />
                    </form>
                `,
            });
            // switch to edit mode
            await click(form.el, ".o_form_button_edit");

            assert.strictEqual(
                form.el.querySelector(".o_field_widget[name='date'] input").value,
                "02/03/2017",
                "The existing record should have a value for the date field"
            );

            // save with no changes
            await click(form.el, ".o_form_button_save");

            //Create a new record
            await click(form.el, ".o_form_button_create");
            assert.notOk(
                form.el.querySelector(".o_field_widget[name='date'] input").value,
                "The new record should not have a value that the framework would have set"
            );
        }
    );

    QUnit.skip("DateField in editable list view", async function (assert) {
        assert.expect(8);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
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

    QUnit.test("DateField remove value", async function (assert) {
        assert.expect(4);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="date" />
                </form>
            `,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(args[1].date, false, "the correct value should be saved");
                }
            },
        });
        // switch to edit mode
        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector(".o_datepicker_input").value,
            "02/03/2017",
            "the date should be correct in edit mode"
        );

        const input = form.el.querySelector(".o_datepicker_input");
        input.value = "";
        await triggerEvents(input, null, ["input", "change", "focusout"]);
        assert.strictEqual(
            form.el.querySelector(".o_datepicker_input").value,
            "",
            "should have correctly removed the value"
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.strictEqual(
            form.el.querySelector(".o_field_date").textContent,
            "",
            "the selected date should be displayed after saving"
        );
    });

    QUnit.test(
        "do not trigger a field_changed for datetime field with date widget",
        async function (assert) {
            assert.expect(3);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="datetime" widget="date" />
                    </form>
                `,
                mockRPC(route, { method }) {
                    assert.step(method);
                },
            });
            await click(form.el, ".o_form_button_edit");

            assert.strictEqual(
                form.el.querySelector(".o_datepicker_input").value,
                "02/08/2017",
                "the date should be correct"
            );

            const input = form.el.querySelector(".o_field_widget[name='datetime'] input");
            input.value = "02/08/2017";
            await triggerEvents(input, null, ["input", "change", "focusout"]);
            await click(form.el, ".o_form_button_save");

            assert.verifySteps(["read"]); // should not have save as nothing changed
        }
    );

    QUnit.test(
        "field date should select its content onclick when there is one",
        async function (assert) {
            assert.expect(3);
            const done = assert.async();

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="date" />
                    </form>
                `,
            });
            await click(form.el, ".o_form_button_edit");

            $(form.el).on("show.datetimepicker", () => {
                assert.containsOnce(
                    document.body,
                    ".bootstrap-datetimepicker-widget",
                    "bootstrap-datetimepicker is visible"
                );
                const active = document.activeElement;
                assert.strictEqual(
                    active.tagName,
                    "INPUT",
                    "The datepicker input should be focused"
                );
                assert.strictEqual(
                    active.value.slice(active.selectionStart, active.selectionEnd),
                    "02/03/2017",
                    "The whole input of the date field should have been selected"
                );
                done();
            });

            await click(form.el, ".o_datepicker input");
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

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="date"/></form>',
            resId: 1,
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

    QUnit.test("DateField: hit enter should update value", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="date" />
                </form>
            `,
        });
        await click(form.el, ".o_form_button_edit");

        const year = new Date().getFullYear();
        const input = form.el.querySelector(".o_field_widget[name='date'] input");

        input.value = "01/08";
        await triggerEvent(input, null, "change");
        await triggerEvent(input, null, "keydown", { key: "Enter" });
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='date'] input").value,
            `01/08/${year}`
        );

        input.value = "08/01";
        await triggerEvent(input, null, "change");
        await triggerEvent(input, null, "keydown", { key: "Enter" });
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='date'] input").value,
            `08/01/${year}`
        );
    });
});
