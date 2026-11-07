/** @odoo-module **/

import {
    getPickerApplyButton,
    getPickerCell,
    getTimePickers,
    zoomOut,
} from "@web/../tests/core/datetime/datetime_test_helpers";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import {
    click,
    clickSave,
    editInput,
    editSelect,
    getFixture,
    patchTimeZone,
    patchWithCleanup,
    triggerEvent,
    triggerEvents,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

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
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            p: [],
                        },
                        {
                            id: 2,
                            date: false,
                            datetime: false,
                        },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("DatetimeField");

    QUnit.test("DatetimeField in form view", async (assert) => {
        patchTimeZone(120);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="datetime"/></form>',
        });

        const expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            expectedDateString,
            "the datetime should be correctly displayed"
        );

        // datepicker should not open on focus
        assert.containsNone(target, ".o_datetime_picker");

        await click(target, ".o_field_datetime input");
        assert.containsOnce(target, ".o_datetime_picker");

        // select 22 April 2018 at 8:25
        await zoomOut();
        await zoomOut();
        await click(getPickerCell("2018"));
        await click(getPickerCell("Apr"));
        await click(getPickerCell("22"));
        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "8");
        await editSelect(minuteSelect, null, "25");
        // Close the datepicker
        await click(target, ".o_form_view_container");

        assert.containsNone(target, ".o_datetime_picker", "datepicker should be closed");

        const newExpectedDateString = "04/22/2018 08:25:00";
        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            newExpectedDateString,
            "the selected date should be displayed in the input"
        );

        // save
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            newExpectedDateString,
            "the selected date should be displayed after saving"
        );
    });

    QUnit.test(
        "DatetimeField only triggers fieldChange when a day is picked and when an hour/minute is selected",
        async (assert) => {
            patchTimeZone(120);

            serverData.models.partner.onchanges = {
                datetime() {},
            };
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: '<form><field name="datetime"/></form>',
                mockRPC(route, { method }) {
                    if (method === "onchange") {
                        assert.step("onchange");
                    }
                },
            });

            await click(target, ".o_field_datetime input");

            assert.containsOnce(target, ".o_datetime_picker");

            // select 22 April 2018 at 8:25
            await zoomOut();
            await zoomOut();
            await click(getPickerCell("2018"));
            await click(getPickerCell("Apr"));
            await click(getPickerCell("22"));

            assert.verifySteps([]);

            const [hourSelect, minuteSelect] = getTimePickers().at(0);
            await editSelect(hourSelect, null, "8");
            await editSelect(minuteSelect, null, "25");

            assert.verifySteps([]);

            // Close the datepicker
            await click(target);

            assert.containsNone(target, ".o_datetime_picker");
            assert.strictEqual(
                target.querySelector(".o_field_datetime input").value,
                "04/22/2018 08:25:00"
            );
            assert.verifySteps(["onchange"]);
        }
    );

    QUnit.test("DatetimeField with datetime formatted without second", async (assert) => {
        patchTimeZone(0);

        serverData.models.partner.fields.datetime.default = "2017-08-02 12:00:05";
        serverData.models.partner.fields.datetime.required = true;

        registry.category("services").add(
            "localization",
            makeFakeLocalizationService({
                dateFormat: "MM/dd/yyyy",
                timeFormat: "HH:mm",
                dateTimeFormat: "MM/dd/yyyy HH:mm",
            }),
            { force: true }
        );

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="datetime"/></form>',
        });

        const expectedDateString = "08/02/2017 12:00";
        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            expectedDateString,
            "the datetime should be correctly displayed"
        );

        await click(target, ".o_form_button_cancel");
        assert.containsNone(target, ".modal", "there should not be a Warning dialog");
    });
    QUnit.test("DatetimeField in editable list view", async (assert) => {
        patchTimeZone(120);

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: `<tree editable="bottom"><field name="datetime"/></tree>`,
        });

        const expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
        const cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.strictEqual(
            cell.textContent,
            expectedDateString,
            "the datetime should be correctly displayed"
        );

        // switch to edit mode
        await click(target.querySelector(".o_data_row .o_data_cell"));

        assert.containsOnce(
            target,
            ".o_field_datetime input",
            "the view should have a date input for editable mode"
        );
        assert.strictEqual(
            target.querySelector(".o_field_datetime input"),
            document.activeElement,
            "date input should have the focus"
        );

        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            expectedDateString,
            "the date should be correct in edit mode"
        );

        assert.containsNone(target, ".o_datetime_picker");

        await click(target, ".o_field_datetime input");

        assert.containsOnce(target, ".o_datetime_picker");

        // select 22 April 2018 at 8:25
        await zoomOut();
        await zoomOut();
        await click(getPickerCell("2018"));
        await click(getPickerCell("Apr"));
        await click(getPickerCell("22"));
        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "8");
        await editSelect(minuteSelect, null, "25");
        // Apply changes
        await click(getPickerApplyButton());

        assert.containsNone(target, ".o_datetime_picker", "datepicker should be closed");

        const newExpectedDateString = "04/22/2018 08:25:00";
        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            newExpectedDateString,
            "the date should be updated in the input"
        );

        // save
        await clickSave(target);
        assert.strictEqual(
            target.querySelector("tr.o_data_row td:not(.o_list_record_selector)").textContent,
            newExpectedDateString,
            "the selected datetime should be displayed after saving"
        );
    });

    QUnit.test(
        "multi edition of DatetimeField in list view: edit date in input",
        async (assert) => {
            await makeView({
                serverData,
                type: "list",
                resModel: "partner",
                arch: '<tree multi_edit="1"><field name="datetime"/></tree>',
            });

            const rows = target.querySelectorAll(".o_data_row");

            // select two records and edit them
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");

            await click(rows[0], ".o_data_cell");

            assert.containsOnce(target, ".o_field_datetime input");

            await editInput(target, ".o_field_datetime input", "10/02/2019 09:00:00");

            assert.containsOnce(target, ".modal");

            await click(target.querySelector(".modal .modal-footer .btn-primary"));

            assert.strictEqual(
                target.querySelector(".o_data_row:first-child .o_data_cell").textContent,
                "10/02/2019 09:00:00"
            );
            assert.strictEqual(
                target.querySelector(".o_data_row:nth-child(2) .o_data_cell").textContent,
                "10/02/2019 09:00:00"
            );
        }
    );

    QUnit.test(
        "multi edition of DatetimeField in list view: clear date in input",
        async (assert) => {
            serverData.models.partner.records[1].datetime = "2017-02-08 10:00:00";

            await makeView({
                serverData,
                type: "list",
                resModel: "partner",
                arch: '<tree multi_edit="1"><field name="datetime"/></tree>',
            });

            const rows = target.querySelectorAll(".o_data_row");

            // select two records and edit them
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");

            await click(rows[0], ".o_data_cell");

            assert.containsOnce(target, ".o_field_datetime input");

            await editInput(target, ".o_field_datetime input", "");

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
        }
    );

    QUnit.test("DatetimeField remove value", async (assert) => {
        assert.expect(4);

        patchTimeZone(120);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="datetime"/></form>',
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.strictEqual(
                        args[1].datetime,
                        false,
                        "the correct value should be saved"
                    );
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            "02/08/2017 12:00:00",
            "the date time should be correct in edit mode"
        );

        const input = target.querySelector(".o_field_datetime input");
        input.value = "";
        await triggerEvents(input, null, ["input", "change", "focusout"]);
        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            "",
            "should have an empty input"
        );

        // save
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_datetime").textContent,
            "",
            "the selected date should be displayed after saving"
        );
    });

    QUnit.test(
        "DatetimeField with date/datetime widget (with day change) does not care about widget",
        async (assert) => {
            patchTimeZone(-240);

            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[1].datetime = "2017-02-08 02:00:00"; // UTC

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="datetime" />
                            </tree>
                            <form>
                                <field name="datetime" widget="date" />
                            </form>
                        </field>
                    </form>`,
            });

            const expectedDateString = "02/07/2017 22:00:00"; // local time zone
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='p'] .o_data_cell").textContent,
                expectedDateString,
                "the datetime (datetime widget) should be correctly displayed in tree view"
            );

            // switch to form view
            await click(target, ".o_field_widget[name='p'] .o_data_cell");
            assert.strictEqual(
                target.querySelector(".modal .o_field_date[name='datetime'] input").value,
                "02/07/2017 22:00:00",
                "the datetime (date widget) should be correctly displayed in form view"
            );
        }
    );

    QUnit.test(
        "DatetimeField with date/datetime widget (without day change) does not care about widget",
        async (assert) => {
            patchTimeZone(-240);

            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.records[1].datetime = "2017-02-08 10:00:00"; // without timezone

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="datetime" />
                            </tree>
                            <form>
                                <field name="datetime" widget="date" />
                            </form>
                        </field>
                    </form>`,
            });

            const expectedDateString = "02/08/2017 06:00:00"; // with timezone
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='p'] .o_data_cell").textContent,
                expectedDateString,
                "the datetime (datetime widget) should be correctly displayed in tree view"
            );

            // switch to form view
            await click(target, ".o_field_widget[name='p'] .o_data_cell");
            assert.strictEqual(
                target.querySelector(".modal .o_field_date[name='datetime'] input").value,
                "02/08/2017 06:00:00",
                "the datetime (date widget) should be correctly displayed in form view"
            );
        }
    );

    QUnit.test("datetime field: hit enter should update value", async (assert) => {
        // This test verifies that the field datetime is correctly computed when:
        //     - we press enter to validate our entry
        //     - we click outside the field to validate our entry
        //     - we save
        patchTimeZone(120);

        registry.category("services").add(
            "localization",
            makeFakeLocalizationService({
                dateFormat: "%m/%d/%Y",
                timeFormat: "%H:%M:%S",
            }),
            { force: true }
        );

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="datetime"/></form>',
            resId: 1,
        });

        const datetime = target.querySelector(".o_field_datetime input");

        // Enter a beginning of date and press enter to validate
        await editInput(datetime, null, "01/08/22 14:30:40");
        await triggerEvent(datetime, null, "keydown", { key: "Enter" });

        const datetimeValue = `01/08/2022 14:30:40`;

        assert.strictEqual(datetime.value, datetimeValue);

        // Click outside the field to check that the field is not changed
        await click(target);
        assert.strictEqual(datetime.value, datetimeValue);

        // Save and check that it's still ok
        await clickSave(target);

        const { value } = target.querySelector(".o_field_datetime input");
        assert.strictEqual(value, datetimeValue);
    });

    QUnit.test("DateTimeField with label opens datepicker on click", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <label for="datetime" string="When is it" />
                    <field name="datetime" />
                </form>`,
        });

        await click(target.querySelector("label.o_form_label"));
        assert.containsOnce(target, ".o_datetime_picker", "datepicker should be opened");
    });

    QUnit.test("datetime field: use picker with arabic numbering system", async (assert) => {
        patchWithCleanup(luxon.Settings, {
            defaultLocale: "ar-001",
            defaultNumberingSystem: "arab",
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: /* xml */ `
                <form string="Partners">
                    <field name="datetime" />
                </form>
            `,
        });

        const getInput = () => target.querySelector("[name=datetime] input");

        assert.strictEqual(getInput().value, "٠٢/٠٨/٢٠١٧ ١١:٠٠:٠٠");

        await click(getInput());
        await editSelect(getTimePickers()[0][1], null, 45);

        assert.strictEqual(getInput().value, "٠٢/٠٨/٢٠١٧ ١١:٤٥:٠٠");
    });

    QUnit.test("list datetime with date widget test", async (assert) => {
        await makeView({
            type: "list",
            resModel: "partner",
            arch: /* xml */ `
                <tree editable="bottom">
                    <field name="datetime" widget="datetime" options="{'show_time': false}"/>
                    <field name="datetime" widget="datetime"/>
                </tree>`,
            serverData,
        });

        const dates = target.querySelectorAll(".o_field_cell");

        assert.strictEqual(
            dates[0].textContent,
            "02/08/2017",
            "for datetime field only date should be visible with show_time as false and readonly"
        );
        assert.strictEqual(
            dates[1].textContent,
            "02/08/2017 11:00:00",
            "for datetime field both date and time should be visible with show_time by default true"
        );
        await click(dates[0]);
        assert.strictEqual(
            target.querySelector(".o_field_datetime input").value,
            "02/08/2017 11:00:00",
            "for datetime field both date and time should be visible with show_time as false and edit"
        );
    });
});
