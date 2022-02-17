/** @odoo-module **/

import { click, patchTimeZone, triggerEvent } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

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

        setupViewRegistries();

        // Date field should not have an offset as they are ignored.
        // However, in the test environement, a UTC timezone is set to run all tests. And if any code does not use the safe timezone method
        // provided by the framework (which happens in this case inside the date range picker lib), unexpected behavior kicks in as the timezone
        // of the dev machine collides with the timezone set by the test env.
        // To avoid failing test on dev's local machines, a hack is to apply an timezone offset greater than the difference between UTC and the dev's
        // machine timezone. For belgium, > 60 is enough. For India, > 5h30 is required, hence 330.
        patchTimeZone(330);
    });

    QUnit.module("DateRangeField");

    QUnit.skipWOWL("Datetime field without quickedit [REQUIRE FOCUS]", async function (assert) {
        assert.expect(21);

        serverData.models.partner.fields.datetime_end = { string: "Datetime End", type: "datetime" };
        serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                "<form>" +
                '<field name="datetime" widget="daterange" options="{\'related_end_date\': \'datetime_end\'}"/>' +
                '<field name="datetime_end" widget="daterange" options="{\'related_start_date\': \'datetime\'}"/>' +
                "</form>",
            resId: 1,
        });

        // Check date display correctly in readonly
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").innerText,
            "02/08/2017 15:30:00",
            "the start date should be correctly displayed in readonly"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").innerText,
            "03/13/2017 05:30:00",
            "the end date should be correctly displayed in readonly"
        );

        // Edit
        await click(form.el.querySelector(".o_form_button_edit"));

        // Check date range picker initialization
        assert.containsN(
            document.body,
            ".daterangepicker",
            2,
            "should initialize 2 date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child").style.display,
            "none",
            "first date range picker should be closed initially"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child").style.display,
            "none",
            "second date range picker should be closed initially"
        );

        // open the first one
        await click(form.el.querySelector(".o_field_date_range:first-child"));

        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child").style.display,
            "block",
            "first date range picker should be opened"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .drp-calendar.left .active.start-date").innerText,
            "8",
            "active start date should be '8' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .drp-calendar.left .hourselect").value,
            "15",
            "active start date hour should be '15' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .drp-calendar.left .minuteselect").value,
            "30",
            "active start date minute should be '30' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .drp-calendar.right .active.end-date").innerText,
            "13",
            "active end date should be '13' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .drp-calendar.right .hourselect").value,
            "5",
            "active end date hour should be '5' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .drp-calendar.right .minuteselect").value,
            "30",
            "active end date minute should be '30' in date range picker"
        );
        assert.containsN(
            form.el.querySelector(".daterangepicker:first-child .drp-calendar.left .minuteselect"),
            "option",
            12,
            "minute selection should contain 12 options (1 for each 5 minutes)"
        );
        // Close picker
        await click(form.el.querySelector(".daterangepicker:first-child .cancelBtn"));
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child").style.display,
            "none",
            "date range picker should be closed"
        );

        // Try to check with end date
        await click(form.el.querySelector(".o_field_date_range:last-child"));
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child").style.display,
            "block",
            "date range picker should be opened"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .drp-calendar.left .active.start-date").innerText,
            "8",
            "active start date should be '8' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .drp-calendar.left .hourselect").value,
            "15",
            "active start date hour should be '15' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .drp-calendar.left .minuteselect").value,
            "30",
            "active start date minute should be '30' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .drp-calendar.right .active.end-date").innerText,
            "13",
            "active end date should be '13' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .drp-calendar.right .hourselect").value,
            "5",
            "active end date hour should be '5' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .drp-calendar.right .minuteselect").value,
            "30",
            "active end date minute should be '30' in date range picker"
        );
    });

    QUnit.skipWOWL("Date field without quickedit [REQUIRE FOCUS]", async function (assert) {
        assert.expect(19);

        serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
        serverData.models.partner.records[0].date_end = "2017-02-08";

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                "<form>" +
                '<field name="date" widget="daterange" options="{\'related_end_date\': \'date_end\'}"/>' +
                '<field name="date_end" widget="daterange" options="{\'related_start_date\': \'date\'}"/>' +
                "</form>",
            resId: 1,
        });

        // Check date display correctly in readonly
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").innerText,
            "02/03/2017",
            "the start date should be correctly displayed in readonly"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").innerText,
            "02/08/2017",
            "the end date should be correctly displayed in readonly"
        );

        // Edit
        await click(form.el.querySelector(".o_form_button_edit"));

        // Check date range picker initialization
        assert.containsN(
            document.body,
            ".daterangepicker",
            2,
            "should initialize 2 date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child").style.display,
            "none",
            "first date range picker should be closed initially"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child").style.display,
            "none",
            "second date range picker should be closed initially"
        );

        // open the first one
        await click(form.el.querySelector(".o_field_date_range:first-child"));

        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child").style.display,
            "block",
            "first date range picker should be opened"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .active.start-date").innerText,
            "3",
            "active start date should be '3' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .active.end-date").innerText,
            "8",
            "active end date should be '8' in date range picker"
        );

        // Change date
        await triggerEvent(form.el, ".daterangepicker:first-child .drp-calendar.left .available:contains('16')", "mousedown");
        await triggerEvent(form.el, ".daterangepicker:first-child .drp-calendar.right .available:contains('12')", "mousedown");
        await click(form.el.querySelector(".daterangepicker:first-child .applyBtn"));

        // Check date after change
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child").style.display,
            "none",
            "date range picker should be closed"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").value,
            "02/16/2017",
            "the date should be '02/16/2017'"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").value,
            "03/12/2017",
            "'the date should be '03/12/2017'"
        );

        // Try to change range with end date
        await click(form.el.querySelector(".o_field_date_range:last-child"));
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child").style.display,
            "block",
            "date range picker should be opened"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .active.start-date").innerText,
            "16",
            "start date should be a 16 in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .active.end-date").innerText,
            "12",
            "end date should be a 12 in date range picker"
        );

        // Change date
        await triggerEvent(form.el, ".daterangepicker:first-child .drp-calendar.left .available:contains('13')", "mousedown");
        await triggerEvent(form.el, ".daterangepicker:first-child .drp-calendar.right .available:contains('18')", "mousedown");
        await click(form.el.querySelector(".daterangepicker:last-child .applyBtn"));

        // Check date after change
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child").style.display,
            "none",
            "date range picker should be closed"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").value,
            "02/13/2017",
            "the start date should be '02/13/2017'"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").value,
            "03/18/2017",
            "the end date should be '03/18/2017'"
        );

        // Save
        await click(form.el.querySelector(".o_form_button_save"));

        // Check date after save
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").innerText,
            "02/13/2017",
            "the start date should be '02/13/2017' after save"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").innerText,
            "03/18/2017",
            "the end date should be '03/18/2017' after save"
        );
    });

    QUnit.skipWOWL("Date field with quickedit [REQUIRE FOCUS]", async function (assert) {
        assert.expect(18);

        serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
        serverData.models.partner.records[0].date_end = "2017-02-08";

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                "<form>" +
                '<field name="date" widget="daterange" options="{\'related_end_date\': \'date_end\'}"/>' +
                '<field name="date_end" widget="daterange" options="{\'related_start_date\': \'date\'}"/>' +
                "</form>",
            resId: 1,
        });

        // Check date display correctly in readonly
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").innerText,
            "02/03/2017",
            "the start date should be correctly displayed in readonly"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").innerText,
            "02/08/2017",
            "the end date should be correctly displayed in readonly"
        );

        // open the first one with quick edit
        await click(form.el.querySelector(".o_field_date_range:first-child"));

        // Check date range picker initialization
        assert.containsN(
            document.body,
            ".daterangepicker",
            2,
            "should initialize 2 date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child").style.display,
            "block",
            "first date range picker should be opened initially"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child").style.display,
            "none",
            "second date range picker should be closed initially"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .active.start-date").innerText,
            "3",
            "active start date should be '3' in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child .active.end-date").innerText,
            "8",
            "active end date should be '8' in date range picker"
        );

        // Change date
        await triggerEvent(form.el, ".daterangepicker:first-child .drp-calendar.left .available:contains('16')", "mousedown");
        await triggerEvent(form.el, ".daterangepicker:first-child .drp-calendar.right .available:contains('12')", "mousedown");
        await click(form.el.querySelector(".daterangepicker:first-child .applyBtn"));

        // Check date after change
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:first-child").style.display,
            "none",
            "date range picker should be closed"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").value,
            "02/16/2017",
            "the date should be '02/16/2017'"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").value,
            "03/12/2017",
            "'the date should be '03/12/2017'"
        );

        // Try to change range with end date
        await click(form.el.querySelector(".o_field_date_range:last-child"));
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child").style.display,
            "block",
            "date range picker should be opened"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .active.start-date").innerText,
            "16",
            "start date should be a 16 in date range picker"
        );
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child .active.end-date").innerText,
            "12",
            "end date should be a 12 in date range picker"
        );

        // Change date
        await triggerEvent(form.el, ".daterangepicker:first-child .drp-calendar.left .available:contains('13')", "mousedown");
        await triggerEvent(form.el, ".daterangepicker:first-child .drp-calendar.right .available:contains('18')", "mousedown");
        await click(form.el.querySelector(".daterangepicker:last-child .applyBtn"));

        // Check date after change
        assert.strictEqual(
            form.el.querySelector(".daterangepicker:last-child").style.display,
            "none",
            "date range picker should be closed"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").value,
            "02/13/2017",
            "the start date should be '02/13/2017'"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").value,
            "03/18/2017",
            "the end date should be '03/18/2017'"
        );

        // Save
        await click(form.el.querySelector(".o_form_button_save"));

        // Check date after save
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:first-child").innerText,
            "02/13/2017",
            "the start date should be '02/13/2017' after save"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_date_range:last-child").innerText,
            "03/18/2017",
            "the end date should be '03/18/2017' after save"
        );
    });

    QUnit.skipWOWL(
        "daterangepicker should disappear on scrolling outside of it",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.fields.datetime_end = { string: "Datetime End", type: "datetime" };
            serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end'}"/>
                    <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime'}"/>
                </form>`,
                resId: 1,
            });

            await click(form.el.querySelector(".o_form_button_edit"));
            await click(form.el.querySelector(".o_field_date_range:first-child"));

            assert.isVisible(form.el.querySelector(".daterangepicker:first-child"), "date range picker should be opened");

            form.el.dispatchEvent(new Event("scroll"));
            assert.isNotVisible(form.el.querySelector(".daterangepicker:first-child"), "date range picker should be closed");
        }
    );

    QUnit.skipWOWL(
        "Datetime field manually input value should send utc value to server",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.fields.datetime_end = { string: "Datetime End", type: "datetime" };
            serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end'}"/>
                    <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime'}"/>
                </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(args.args[1], { datetime: "2017-02-08 06:00:00" });
                    }
                },
            });

            // check date display correctly in readonly
            assert.strictEqual(
                form.el.querySelector(".o_field_date_range:first-child").innerText,
                "02/08/2017 15:30:00",
                "the start date should be correctly displayed in readonly"
            );
            assert.strictEqual(
                form.el.querySelector(".o_field_date_range:last-child").innerText,
                "03/13/2017 05:30:00",
                "the end date should be correctly displayed in readonly"
            );

            // edit form
            await click(form.el.querySelector(".o_form_button_edit"));
            // update input for Datetime
            await editInput(form.el, ".o_field_date_range:first-child", "02/08/2017 11:30:00");
            // save form
            await click(form.el.querySelector(".o_form_button_save"));

            assert.strictEqual(
                form.el.querySelector(".o_field_date_range:first-child").innerText,
                "02/08/2017 11:30:00",
                "the start date should be correctly displayed in readonly after manual update"
            );
        }
    );

    QUnit.skipWOWL(
        "DateRangeField manually input wrong value should show toaster",
        async function (assert) {
            assert.expect(5);

            serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
            serverData.models.partner.records[0].date_end = "2017-02-08";

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
            <form>
                <field name="date" widget="daterange" options="{'related_end_date': 'date_end'}"/>
                <field name="date_end" widget="daterange" options="{'related_start_date': 'date'}"/>
            </form>`,
                interceptsPropagate: {
                    call_service: function (ev) {
                        if (ev.data.service === "notification") {
                            assert.strictEqual(ev.data.method, "notify");
                            assert.strictEqual(ev.data.args[0].title, "Invalid fields:");
                            assert.strictEqual(
                                ev.data.args[0].message.toString(),
                                "<ul><li>A date</li></ul>"
                            );
                        }
                    },
                },
            });

            await editInput(form.el, ".o_field_date_range:first-child", "blabla");
            // click outside daterange field
            await click(form.el);
            assert.hasClass(
                form.el.querySelector("input[name=date]"),
                "o_field_invalid",
                "date field should be displayed as invalid"
            );
            // update input date with right value
            await editInput(form.el, ".o_field_date_range:first-child", "02/08/2017");
            assert.doesNotHaveClass(
                form.el.querySelector("input[name=date]"),
                "o_field_invalid",
                "date field should not be displayed as invalid now"
            );

            // again enter wrong value and try to save should raise invalid fields value
            await editInput(form.el, ".o_field_date_range:first-child", "blabla");
            await click(form.el.querySelector(".o_form_button_save"));
        }
    );

    QUnit.skipWOWL("Datetime field with option format type is 'date'", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.datetime_end = { string: "Datetime End", type: "datetime" };
        serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form>
                    <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end', 'format_type': 'date'}"/>'
                    <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime', 'format_type': 'date'}"/>'
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            form.el.querySelector('.o_field_date_range[name="datetime"]').innerText,
            "02/08/2017",
            "the start date should only show date when option formatType is Date"
        );
        assert.strictEqual(
            form.el.querySelector('.o_field_date_range[name="datetime_end"]').innerText,
            "03/13/2017",
            "the end date should only show date when option formatType is Date"
        );
    });

    QUnit.skipWOWL("Date field with option format type is 'datetime'", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
        serverData.models.partner.records[0].date_end = "2017-03-13";

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form>
                    <field name="date" widget="daterange" options="{'related_end_date': 'date_end', 'format_type': 'datetime'}"/>
                    <field name="date_end" widget="daterange" options="{'related_start_date': 'date', 'format_type': 'datetime'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            form.el.querySelector('.o_field_date_range[name="date"]').innerText,
            "02/03/2017 05:30:00",
            "the start date should show date with time when option format_type is datatime"
        );
        assert.strictEqual(
            form.el.querySelector('.o_field_date_range[name="date_end"]').innerText,
            "03/13/2017 05:30:00",
            "the end date should show date with time when option format_type is datatime"
        );
    });
});
