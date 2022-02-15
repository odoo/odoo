/** @odoo-module **/

import { setupViewRegistries } from "../views/helpers";

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

    QUnit.module("DateRangeField");

    QUnit.skipWOWL("Datetime field without quickedit [REQUIRE FOCUS]", async function (assert) {
        assert.expect(21);

        this.data.partner.fields.datetime_end = { string: "Datetime End", type: "datetime" };
        this.data.partner.records[0].datetime_end = "2017-03-13 00:00:00";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="datetime" widget="daterange" options="{\'related_end_date\': \'datetime_end\'}"/>' +
                '<field name="datetime_end" widget="daterange" options="{\'related_start_date\': \'datetime\'}"/>' +
                "</form>",
            res_id: 1,
            session: {
                getTZOffset: function () {
                    return 330;
                },
            },
        });

        // Check date display correctly in readonly
        assert.strictEqual(
            form.$(".o_field_date_range:first").text(),
            "02/08/2017 15:30:00",
            "the start date should be correctly displayed in readonly"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").text(),
            "03/13/2017 05:30:00",
            "the end date should be correctly displayed in readonly"
        );

        // Edit
        await testUtils.form.clickEdit(form);

        // Check date range picker initialization
        assert.containsN(
            document.body,
            ".daterangepicker",
            2,
            "should initialize 2 date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first").css("display"),
            "none",
            "first date range picker should be closed initially"
        );
        assert.strictEqual(
            $(".daterangepicker:last").css("display"),
            "none",
            "second date range picker should be closed initially"
        );

        // open the first one
        await testUtils.dom.click(form.$(".o_field_date_range:first"));

        assert.strictEqual(
            $(".daterangepicker:first").css("display"),
            "block",
            "first date range picker should be opened"
        );
        assert.strictEqual(
            $(".daterangepicker:first .drp-calendar.left .active.start-date").text(),
            "8",
            "active start date should be '8' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first .drp-calendar.left .hourselect").val(),
            "15",
            "active start date hour should be '15' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first .drp-calendar.left .minuteselect").val(),
            "30",
            "active start date minute should be '30' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first .drp-calendar.right .active.end-date").text(),
            "13",
            "active end date should be '13' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first .drp-calendar.right .hourselect").val(),
            "5",
            "active end date hour should be '5' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first .drp-calendar.right .minuteselect").val(),
            "30",
            "active end date minute should be '30' in date range picker"
        );
        assert.containsN(
            $(".daterangepicker:first .drp-calendar.left .minuteselect"),
            "option",
            12,
            "minute selection should contain 12 options (1 for each 5 minutes)"
        );
        // Close picker
        await testUtils.dom.click($(".daterangepicker:first .cancelBtn"));
        assert.strictEqual(
            $(".daterangepicker:first").css("display"),
            "none",
            "date range picker should be closed"
        );

        // Try to check with end date
        await testUtils.dom.click(form.$(".o_field_date_range:last"));
        assert.strictEqual(
            $(".daterangepicker:last").css("display"),
            "block",
            "date range picker should be opened"
        );
        assert.strictEqual(
            $(".daterangepicker:last .drp-calendar.left .active.start-date").text(),
            "8",
            "active start date should be '8' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:last .drp-calendar.left .hourselect").val(),
            "15",
            "active start date hour should be '15' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:last .drp-calendar.left .minuteselect").val(),
            "30",
            "active start date minute should be '30' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:last .drp-calendar.right .active.end-date").text(),
            "13",
            "active end date should be '13' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:last .drp-calendar.right .hourselect").val(),
            "5",
            "active end date hour should be '5' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:last .drp-calendar.right .minuteselect").val(),
            "30",
            "active end date minute should be '30' in date range picker"
        );

        form.destroy();
    });

    QUnit.skipWOWL("Date field without quickedit [REQUIRE FOCUS]", async function (assert) {
        assert.expect(19);

        this.data.partner.fields.date_end = { string: "Date End", type: "date" };
        this.data.partner.records[0].date_end = "2017-02-08";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="date" widget="daterange" options="{\'related_end_date\': \'date_end\'}"/>' +
                '<field name="date_end" widget="daterange" options="{\'related_start_date\': \'date\'}"/>' +
                "</form>",
            res_id: 1,
            session: {
                getTZOffset: function () {
                    return 330;
                },
            },
        });

        // Check date display correctly in readonly
        assert.strictEqual(
            form.$(".o_field_date_range:first").text(),
            "02/03/2017",
            "the start date should be correctly displayed in readonly"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").text(),
            "02/08/2017",
            "the end date should be correctly displayed in readonly"
        );

        // Edit
        await testUtils.form.clickEdit(form);

        // Check date range picker initialization
        assert.containsN(
            document.body,
            ".daterangepicker",
            2,
            "should initialize 2 date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first").css("display"),
            "none",
            "first date range picker should be closed initially"
        );
        assert.strictEqual(
            $(".daterangepicker:last").css("display"),
            "none",
            "second date range picker should be closed initially"
        );

        // open the first one
        await testUtils.dom.click(form.$(".o_field_date_range:first"));

        assert.strictEqual(
            $(".daterangepicker:first").css("display"),
            "block",
            "first date range picker should be opened"
        );
        assert.strictEqual(
            $(".daterangepicker:first .active.start-date").text(),
            "3",
            "active start date should be '3' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first .active.end-date").text(),
            "8",
            "active end date should be '8' in date range picker"
        );

        // Change date
        await testUtils.dom.triggerMouseEvent(
            $('.daterangepicker:first .drp-calendar.left .available:contains("16")'),
            "mousedown"
        );
        await testUtils.dom.triggerMouseEvent(
            $('.daterangepicker:first .drp-calendar.right .available:contains("12")'),
            "mousedown"
        );
        await testUtils.dom.click($(".daterangepicker:first .applyBtn"));

        // Check date after change
        assert.strictEqual(
            $(".daterangepicker:first").css("display"),
            "none",
            "date range picker should be closed"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:first").val(),
            "02/16/2017",
            "the date should be '02/16/2017'"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").val(),
            "03/12/2017",
            "'the date should be '03/12/2017'"
        );

        // Try to change range with end date
        await testUtils.dom.click(form.$(".o_field_date_range:last"));
        assert.strictEqual(
            $(".daterangepicker:last").css("display"),
            "block",
            "date range picker should be opened"
        );
        assert.strictEqual(
            $(".daterangepicker:last .active.start-date").text(),
            "16",
            "start date should be a 16 in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:last .active.end-date").text(),
            "12",
            "end date should be a 12 in date range picker"
        );

        // Change date
        await testUtils.dom.triggerMouseEvent(
            $('.daterangepicker:last .drp-calendar.left .available:contains("13")'),
            "mousedown"
        );
        await testUtils.dom.triggerMouseEvent(
            $('.daterangepicker:last .drp-calendar.right .available:contains("18")'),
            "mousedown"
        );
        await testUtils.dom.click($(".daterangepicker:last .applyBtn"));

        // Check date after change
        assert.strictEqual(
            $(".daterangepicker:last").css("display"),
            "none",
            "date range picker should be closed"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:first").val(),
            "02/13/2017",
            "the start date should be '02/13/2017'"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").val(),
            "03/18/2017",
            "the end date should be '03/18/2017'"
        );

        // Save
        await testUtils.form.clickSave(form);

        // Check date after save
        assert.strictEqual(
            form.$(".o_field_date_range:first").text(),
            "02/13/2017",
            "the start date should be '02/13/2017' after save"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").text(),
            "03/18/2017",
            "the end date should be '03/18/2017' after save"
        );

        form.destroy();
    });

    QUnit.skipWOWL("Date field with quickedit [REQUIRE FOCUS]", async function (assert) {
        assert.expect(18);

        this.data.partner.fields.date_end = { string: "Date End", type: "date" };
        this.data.partner.records[0].date_end = "2017-02-08";

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                "<form>" +
                '<field name="date" widget="daterange" options="{\'related_end_date\': \'date_end\'}"/>' +
                '<field name="date_end" widget="daterange" options="{\'related_start_date\': \'date\'}"/>' +
                "</form>",
            res_id: 1,
            session: {
                // #tzoffset_daterange
                // Date field should not have an offset as they are ignored.
                // However, in the test environement, a UTC timezone is set to run all tests. And if any code does not use the safe timezone method
                // provided by the framework (which happens in this case inside the date range picker lib), unexpected behavior kicks in as the timezone
                // of the dev machine collides with the timezone set by the test env.
                // To avoid failing test on dev's local machines, a hack is to apply an timezone offset greater than the difference between UTC and the dev's
                // machine timezone. For belgium, > 60 is enough. For India, > 5h30 is required, hence 330.
                // Note that prod and runbot will never have a problem with this, it only happens as you mock the getTZOffset method (like in tests).
                getTZOffset: function () {
                    return 330;
                },
            },
        });

        // Check date display correctly in readonly
        assert.strictEqual(
            form.$(".o_field_date_range:first").text(),
            "02/03/2017",
            "the start date should be correctly displayed in readonly"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").text(),
            "02/08/2017",
            "the end date should be correctly displayed in readonly"
        );

        // open the first one with quick edit
        await testUtils.dom.click(form.$(".o_field_date_range:first"));

        // Check date range picker initialization
        assert.containsN(
            document.body,
            ".daterangepicker",
            2,
            "should initialize 2 date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first").css("display"),
            "block",
            "first date range picker should be opened initially"
        );
        assert.strictEqual(
            $(".daterangepicker:last").css("display"),
            "none",
            "second date range picker should be closed initially"
        );
        assert.strictEqual(
            $(".daterangepicker:first .active.start-date").text(),
            "3",
            "active start date should be '3' in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:first .active.end-date").text(),
            "8",
            "active end date should be '8' in date range picker"
        );

        // Change date
        await testUtils.dom.triggerMouseEvent(
            $('.daterangepicker:first .drp-calendar.left .available:contains("16")'),
            "mousedown"
        );
        await testUtils.dom.triggerMouseEvent(
            $('.daterangepicker:first .drp-calendar.right .available:contains("12")'),
            "mousedown"
        );
        await testUtils.dom.click($(".daterangepicker:first .applyBtn"));

        // Check date after change
        assert.strictEqual(
            $(".daterangepicker:first").css("display"),
            "none",
            "date range picker should be closed"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:first").val(),
            "02/16/2017",
            "the date should be '02/16/2017'"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").val(),
            "03/12/2017",
            "'the date should be '03/12/2017'"
        );

        // Try to change range with end date
        await testUtils.dom.click(form.$(".o_field_date_range:last"));
        assert.strictEqual(
            $(".daterangepicker:last").css("display"),
            "block",
            "date range picker should be opened"
        );
        assert.strictEqual(
            $(".daterangepicker:last .active.start-date").text(),
            "16",
            "start date should be a 16 in date range picker"
        );
        assert.strictEqual(
            $(".daterangepicker:last .active.end-date").text(),
            "12",
            "end date should be a 12 in date range picker"
        );

        // Change date
        await testUtils.dom.triggerMouseEvent(
            $('.daterangepicker:last .drp-calendar.left .available:contains("13")'),
            "mousedown"
        );
        await testUtils.dom.triggerMouseEvent(
            $('.daterangepicker:last .drp-calendar.right .available:contains("18")'),
            "mousedown"
        );
        await testUtils.dom.click($(".daterangepicker:last .applyBtn"));

        // Check date after change
        assert.strictEqual(
            $(".daterangepicker:last").css("display"),
            "none",
            "date range picker should be closed"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:first").val(),
            "02/13/2017",
            "the start date should be '02/13/2017'"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").val(),
            "03/18/2017",
            "the end date should be '03/18/2017'"
        );

        // Save
        await testUtils.form.clickSave(form);

        // Check date after save
        assert.strictEqual(
            form.$(".o_field_date_range:first").text(),
            "02/13/2017",
            "the start date should be '02/13/2017' after save"
        );
        assert.strictEqual(
            form.$(".o_field_date_range:last").text(),
            "03/18/2017",
            "the end date should be '03/18/2017' after save"
        );

        form.destroy();
    });

    QUnit.skipWOWL(
        "daterangepicker should disappear on scrolling outside of it",
        async function (assert) {
            assert.expect(2);

            this.data.partner.fields.datetime_end = { string: "Datetime End", type: "datetime" };
            this.data.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end'}"/>
                    <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime'}"/>
                </form>`,
                res_id: 1,
            });

            await testUtils.form.clickEdit(form);
            await testUtils.dom.click(form.$(".o_field_date_range:first"));

            assert.isVisible($(".daterangepicker:first"), "date range picker should be opened");

            form.el.dispatchEvent(new Event("scroll"));
            assert.isNotVisible($(".daterangepicker:first"), "date range picker should be closed");

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "Datetime field manually input value should send utc value to server",
        async function (assert) {
            assert.expect(4);

            this.data.partner.fields.datetime_end = { string: "Datetime End", type: "datetime" };
            this.data.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end'}"/>
                    <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime'}"/>
                </form>`,
                res_id: 1,
                session: {
                    getTZOffset: function () {
                        return 330;
                    },
                },
                mockRPC: function (route, args) {
                    if (args.method === "write") {
                        assert.deepEqual(args.args[1], { datetime: "2017-02-08 06:00:00" });
                    }
                    return this._super(...arguments);
                },
            });

            // check date display correctly in readonly
            assert.strictEqual(
                form.$(".o_field_date_range:first").text(),
                "02/08/2017 15:30:00",
                "the start date should be correctly displayed in readonly"
            );
            assert.strictEqual(
                form.$(".o_field_date_range:last").text(),
                "03/13/2017 05:30:00",
                "the end date should be correctly displayed in readonly"
            );

            // edit form
            await testUtils.form.clickEdit(form);
            // update input for Datetime
            await testUtils.fields.editInput(
                form.$(".o_field_date_range:first"),
                "02/08/2017 11:30:00"
            );
            // save form
            await testUtils.form.clickSave(form);

            assert.strictEqual(
                form.$(".o_field_date_range:first").text(),
                "02/08/2017 11:30:00",
                "the start date should be correctly displayed in readonly after manual update"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "DateRangeField manually input wrong value should show toaster",
        async function (assert) {
            assert.expect(5);

            this.data.partner.fields.date_end = { string: "Date End", type: "date" };
            this.data.partner.records[0].date_end = "2017-02-08";

            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
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

            await testUtils.fields.editInput(form.$(".o_field_date_range:first"), "blabla");
            // click outside daterange field
            await testUtils.dom.click(form.$el);
            assert.hasClass(
                form.$("input[name=date]"),
                "o_field_invalid",
                "date field should be displayed as invalid"
            );
            // update input date with right value
            await testUtils.fields.editInput(form.$(".o_field_date_range:first"), "02/08/2017");
            assert.doesNotHaveClass(
                form.$("input[name=date]"),
                "o_field_invalid",
                "date field should not be displayed as invalid now"
            );

            // again enter wrong value and try to save should raise invalid fields value
            await testUtils.fields.editInput(form.$(".o_field_date_range:first"), "blabla");
            await testUtils.form.clickSave(form);

            form.destroy();
        }
    );

    QUnit.skipWOWL("Datetime field with option format type is 'date'", async function (assert) {
        assert.expect(2);

        this.data.partner.fields.datetime_end = { string: "Datetime End", type: "datetime" };
        this.data.partner.records[0].datetime_end = "2017-03-13 00:00:00";

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form>
                    <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end', 'format_type': 'date'}"/>'
                    <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime', 'format_type': 'date'}"/>'
                </form>`,
            res_id: 1,
            session: {
                getTZOffset() {
                    return 330;
                },
            },
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

        form.destroy();
    });

    QUnit.skipWOWL("Date field with option format type is 'datetime'", async function (assert) {
        assert.expect(2);

        this.data.partner.fields.date_end = { string: "Date End", type: "date" };
        this.data.partner.records[0].date_end = "2017-03-13";

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `<form>
                    <field name="date" widget="daterange" options="{'related_end_date': 'date_end', 'format_type': 'datetime'}"/>
                    <field name="date_end" widget="daterange" options="{'related_start_date': 'date', 'format_type': 'datetime'}"/>
                </form>`,
            res_id: 1,
            session: {
                getTZOffset() {
                    return 330;
                },
            },
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

        form.destroy();
    });
});
