/** @odoo-module **/

import { getPickerCell, zoomOut } from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    click,
    clickCreate,
    clickDiscard,
    clickSave,
    editInput,
    getFixture,
    patchDate,
    patchTimeZone,
    patchWithCleanup,
    triggerEvent,
    triggerEvents,
    triggerScroll,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { localization } from "@web/core/l10n/localization";

let serverData;
let target;

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
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            display_name: "first record",
                            foo: "yop",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            foo: "blip",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                        },
                        { id: 3, foo: "gnap" },
                        { id: 5, foo: "blop" },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("DateField");

    QUnit.test("DateField: toggle datepicker", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo" />
                    <field name="date" />
                </form>`,
        });
        assert.containsNone(target, ".o_datetime_picker", "datepicker should be closed initially");

        await click(target, ".o_field_date input");
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should be opened");

        // focus another field
        await click(target, ".o_field_widget[name='foo'] input");
        assert.containsNone(
            target,
            ".o_datetime_picker",
            "datepicker should close itself when the user clicks outside"
        );
    });

    QUnit.test("DateField: toggle datepicker far in the future", async (assert) => {
        serverData.models.partner.records = [
            {
                id: 1,
                date: "9999-12-30",
                foo: "yop",
            },
        ];

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                    <form>
                        <field name="foo" />
                        <field name="date" />
                    </form>`,
        });

        assert.containsNone(target, ".o_datetime_picker", "datepicker should be closed initially");

        await click(target, ".o_field_date input");
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should be opened");

        // focus another field
        await click(target, ".o_field_widget[name='foo'] input");
        assert.containsNone(
            target,
            ".o_datetime_picker",
            "datepicker should close itself when the user clicks outside"
        );
    });

    QUnit.test("date field is empty if no date is set", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 4,
            serverData,
            arch: '<form><field name="date"/></form>',
        });

        assert.containsOnce(
            target,
            ".o_field_widget input",
            "should have one input in the form view"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "",
            "and it should be empty"
        );
    });

    QUnit.test("DateField: set an invalid date when the field is already set", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="date"/></form>',
        });

        const input = target.querySelector(".o_field_widget[name='date'] input");
        assert.strictEqual(input.value, "02/03/2017");

        input.value = "mmmh";
        await triggerEvent(input, null, "change");
        assert.strictEqual(input.value, "02/03/2017", "should have reset the original value");
    });

    QUnit.test("DateField: set an invalid date when the field is not set yet", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 4,
            serverData,
            arch: '<form><field name="date"/></form>',
        });

        const input = target.querySelector(".o_field_widget[name='date'] input");
        assert.strictEqual(input.value, "");

        input.value = "mmmh";
        await triggerEvent(input, null, "change");
        assert.strictEqual(input.value, "", "The date field should be empty");
    });

    QUnit.test("DateField value should not set on first click", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 4,
            serverData,
            arch: '<form><field name="date"/></form>',
        });

        await click(target, ".o_field_date input");
        // open datepicker and select a date
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='date'] input").value,
            "",
            "date field's input should be empty on first click"
        );
        await click(getPickerCell("22"));

        // re-open datepicker
        await click(target, ".o_field_date input");
        assert.strictEqual(
            target.querySelector(".o_date_item_cell.o_selected").textContent,
            "22",
            "datepicker should be highlight with 22nd day of month"
        );
    });

    QUnit.test("DateField in form view (with positive time zone offset)", async (assert) => {
        assert.expect(7);

        patchTimeZone(120); // Should be ignored by date fields

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="date"/></form>',
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.strictEqual(
                        args[1].date,
                        "2017-02-22",
                        "the correct value should be saved"
                    );
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            "02/03/2017",
            "the date should be correct in edit mode"
        );

        // open datepicker and select another value
        await click(target, ".o_field_date input");
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should be opened");
        assert.containsOnce(
            target,
            ".o_date_item_cell.o_selected",
            "datepicker should have a selected day"
        );
        // select 22 Feb 2017
        await zoomOut();
        await zoomOut();
        await click(getPickerCell("2017"));
        await click(getPickerCell("Feb"));
        await click(getPickerCell("22"));
        assert.containsNone(target, ".o_datetime_picker", "datepicker should be closed");
        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            "02/22/2017",
            "the selected date should be displayed in the input"
        );

        // save
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            "02/22/2017",
            "the selected date should be displayed after saving"
        );
    });

    QUnit.test("DateField in form view (with negative time zone offset)", async (assert) => {
        patchTimeZone(-120); // Should be ignored by date fields

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="date"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            "02/03/2017",
            "the date should be correct in edit mode"
        );
    });

    QUnit.test("DateField dropdown doesn't disappear on scroll", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <div class="scrollable" style="height: 2000px;">
                        <field name="date" />
                    </div>
                </form>`,
        });

        await click(target, ".o_field_date input");
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should be opened");

        await triggerScroll(target, { top: 50 });
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should still be opened");
    });

    QUnit.test("DateField with label opens datepicker on click", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <label for="date" string="What date is it" />
                    <field name="date" />
                </form>`,
        });

        await click(target.querySelector("label.o_form_label"));
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should be opened");
    });

    QUnit.test("DateField with warn_future option", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 4,
            serverData,
            arch: `
                <form>
                    <field name="date" options="{'warn_future': true}" />
                </form>`,
        });

        // open datepicker and select another value
        await click(target, ".o_field_date input");
        await zoomOut();
        await zoomOut();
        await click(getPickerCell("2030"));
        await click(getPickerCell("Dec"));
        await click(getPickerCell("31"));

        assert.containsOnce(
            target,
            ".fa-exclamation-triangle",
            "should have a warning in the form view"
        );

        await editInput(target, ".o_field_widget[name='date'] input", "");

        assert.containsNone(
            target,
            ".fa-exclamation-triangle",
            "the warning in the form view should be hidden"
        );
    });

    QUnit.test(
        "DateField with warn_future option: do not overwrite datepicker option",
        async (assert) => {
            // Making sure we don't have a legit default value
            // or any onchange that would set the value
            serverData.models.partner.fields.date.default = undefined;
            serverData.models.partner.onchanges = {};

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="foo" /> <!-- Do not let the date field get the focus in the first place -->
                        <field name="date" options="{'warn_future': true}" />
                    </form>`,
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget[name='date'] input").value,
                "02/03/2017",
                "The existing record should have a value for the date field"
            );

            //Create a new record
            await clickCreate(target);
            assert.notOk(
                target.querySelector(".o_field_widget[name='date'] input").value,
                "The new record should not have a value that the framework would have set"
            );
        }
    );

    QUnit.test("DateField in editable list view", async (assert) => {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: '<tree editable="bottom"><field name="date"/></tree>',
        });

        const cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.strictEqual(
            cell.textContent,
            "02/03/2017",
            "the date should be displayed correctly in readonly"
        );
        await click(cell);

        assert.containsOnce(
            target,
            ".o_field_date input",
            "the view should have a date input for editable mode"
        );

        assert.strictEqual(
            target.querySelector(".o_field_date input"),
            document.activeElement,
            "date input should have the focus"
        );

        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            "02/03/2017",
            "the date should be correct in edit mode"
        );

        // open datepicker and select another value
        await click(target, ".o_field_date input");
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should be opened");
        await zoomOut();
        await zoomOut();
        await click(getPickerCell("2017"));
        await click(getPickerCell("Feb"));
        await click(getPickerCell("22"));
        assert.containsNone(target, ".o_datetime_picker", "datepicker should be closed");
        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            "02/22/2017",
            "the selected date should be displayed in the input"
        );

        // save
        await clickSave(target);
        assert.strictEqual(
            target.querySelector("tr.o_data_row td:not(.o_list_record_selector)").textContent,
            "02/22/2017",
            "the selected date should be displayed after saving"
        );
    });

    QUnit.test("multi edition of DateField in list view: clear date in input", async (assert) => {
        serverData.models.partner.records[1].date = "2017-02-03";

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree multi_edit="1"><field name="date"/></tree>',
        });

        const rows = target.querySelectorAll(".o_data_row");

        // select two records and edit them
        await click(rows[0], ".o_list_record_selector input");
        await click(rows[1], ".o_list_record_selector input");

        await click(rows[0], ".o_data_cell");

        assert.containsOnce(target, ".o_field_date input");
        await editInput(target, ".o_field_date input", "");

        assert.containsOnce(target, ".modal");
        await click(target, ".modal .modal-footer .btn-primary");

        assert.strictEqual(
            target.querySelector(".o_data_row:first-child .o_data_cell").textContent,
            ""
        );
        assert.strictEqual(
            target.querySelector(".o_data_row:nth-child(2) .o_data_cell").textContent,
            ""
        );
    });

    QUnit.test("DateField remove value", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="date"/></form>',
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    assert.strictEqual(args[1].date, false, "the correct value should be saved");
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            "02/03/2017",
            "the date should be correct in edit mode"
        );

        const input = target.querySelector(".o_field_date input");
        input.value = "";
        await triggerEvents(input, null, ["input", "change", "focusout"]);
        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            "",
            "should have correctly removed the value"
        );

        // save
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_date").textContent,
            "",
            "the selected date should be displayed after saving"
        );
    });

    QUnit.test("field date should select its content onclick when there is one", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="date"/></form>',
        });

        const input = target.querySelector(".o_field_date input");
        await click(input);
        input.focus();

        assert.containsOnce(target, ".o_datetime_picker");
        const active = document.activeElement;
        assert.strictEqual(active.tagName, "INPUT", "The datepicker input should be focused");
        assert.strictEqual(
            active.value.slice(active.selectionStart, active.selectionEnd),
            "02/03/2017",
            "The whole input of the date field should have been selected"
        );
    });

    QUnit.test("DateField supports custom format", async (assert) => {
        patchWithCleanup(localization, {
            dateFormat: "dd-MM-yyyy",
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="date"/></form>',
            resId: 1,
        });

        const dateViewForm = target.querySelector(".o_field_date input").value;
        await click(target, ".o_field_date input");

        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            dateViewForm,
            "input date field should be the same as it was in the view form"
        );
        await click(getPickerCell("22"));
        const dateEditForm = target.querySelector(".o_field_date input").value;
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            dateEditForm,
            "date field should be the same as the one selected in the view form"
        );
    });

    QUnit.test("DateField supports internationalization", async (assert) => {
        patchWithCleanup(luxon.Settings, {
            defaultLocale: "nb-NO",
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="date"/></form>',
            resId: 1,
        });

        const dateViewForm = target.querySelector(".o_field_date input").value;
        await click(target, ".o_field_date input");

        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            dateViewForm,
            "input date field should be the same as it was in the view form"
        );
        assert.strictEqual(
            target.querySelector(".o_zoom_out strong").textContent,
            "februar 2017",
            "Norwegian locale should be correctly applied"
        );
        await click(getPickerCell("22"));
        const dateEditForm = target.querySelector(".o_field_date input").value;
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_date input").value,
            dateEditForm,
            "date field should be the same as the one selected in the view form"
        );
    });

    QUnit.test("DateField: hit enter should update value", async (assert) => {
        patchTimeZone(120);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="date"/></form>',
        });

        const year = new Date().getFullYear();
        const input = target.querySelector(".o_field_widget[name='date'] input");

        input.value = "01/08";
        await triggerEvent(input, null, "change");
        await triggerEvent(input, null, "keydown", { key: "Enter" });
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='date'] input").value,
            `01/08/${year}`
        );

        input.value = "08/01";
        await triggerEvent(input, null, "change");
        await triggerEvent(input, null, "keydown", { key: "Enter" });
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='date'] input").value,
            `08/01/${year}`
        );
    });

    QUnit.test("DateField: allow to use compute dates (+5d for instance)", async (assert) => {
        patchDate(2021, 1, 15, 10, 0, 0); // current date : 15 Feb 2021 10:00:00
        serverData.models.partner.fields.date.default = "2019-09-15";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="date"></field></form>',
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "09/15/2019"); // default date

        // Calculate a new date from current date + 5 days
        await editInput(target, ".o_field_widget[name=date] input", "+5d");
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "02/20/2021");

        // Discard and do it again
        await clickDiscard(target);
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "09/15/2019"); // default date
        await editInput(target, ".o_field_widget[name=date] input", "+5d");
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "02/20/2021");

        // Save and do it again
        await clickSave(target);
        // new computed date (current date + 5 days) is saved
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "02/20/2021");
        await editInput(target, ".o_field_widget[name=date] input", "+5d");
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "02/20/2021");
    });
});
