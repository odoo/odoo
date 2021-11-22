/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeUserService } from "../helpers/mock_services";
import { click, patchDate, triggerEvents } from "../helpers/utils";
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

    QUnit.module("RemainingDaysField");

    QUnit.test("RemainingDaysField on a date field in list view", async function (assert) {
        assert.expect(16);

        patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
        serverData.models.partner.records = [
            { id: 1, date: "2017-10-08" }, // today
            { id: 2, date: "2017-10-09" }, // tomorrow
            { id: 3, date: "2017-10-07" }, // yesterday
            { id: 4, date: "2017-10-10" }, // + 2 days
            { id: 5, date: "2017-10-05" }, // - 3 days
            { id: 6, date: "2018-02-08" }, // + 4 months (diff >= 100 days)
            { id: 7, date: "2017-06-08" }, // - 4 months (diff >= 100 days)
            { id: 8, date: false },
        ];

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree>
                    <field name="date" widget="remaining_days" />
                </tree>
            `,
        });

        const cells = list.el.querySelectorAll(".o_data_cell");
        assert.strictEqual(cells[0].textContent, "Today");
        assert.strictEqual(cells[1].textContent, "Tomorrow");
        assert.strictEqual(cells[2].textContent, "Yesterday");
        assert.strictEqual(cells[3].textContent, "In 2 days");
        assert.strictEqual(cells[4].textContent, "3 days ago");
        assert.strictEqual(cells[5].textContent, "02/08/2018");
        assert.strictEqual(cells[6].textContent, "06/08/2017");
        assert.strictEqual(cells[7].textContent, "");

        assert.hasAttrValue(cells[0].querySelector(".o_field_widget"), "title", "10/08/2017");

        assert.hasClass(cells[0].querySelector("div"), "font-weight-bold text-warning");
        assert.doesNotHaveClass(
            cells[1].querySelector("div"),
            "font-weight-bold text-warning text-danger"
        );
        assert.hasClass(cells[2].querySelector("div"), "font-weight-bold text-danger");
        assert.doesNotHaveClass(
            cells[3].querySelector("div"),
            "font-weight-bold text-warning text-danger"
        );
        assert.hasClass(cells[4].querySelector("div"), "font-weight-bold text-danger");
        assert.doesNotHaveClass(
            cells[5].querySelector("div"),
            "font-weight-bold text-warning text-danger"
        );
        assert.hasClass(cells[6].querySelector("div"), "font-weight-bold text-danger");
    });

    QUnit.skip(
        "RemainingDaysField on a date field in multi edit list view",
        async function (assert) {
            assert.expect(7);

            patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
            serverData.models.partner.records = [
                { id: 1, date: "2017-10-08" }, // today
                { id: 2, date: "2017-10-09" }, // tomorrow
                { id: 8, date: false },
            ];

            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                    <tree multi_edit="1">
                        <field name="date" widget="remaining_days" />
                    </tree>
                `,
            });

            const cells = list.el.querySelectorAll(".o_data_cell");
            const rows = list.el.querySelectorAll(".o_data_row");

            assert.strictEqual(cells[0].textContent, "Today");
            assert.strictEqual(cells[1].textContent, "Tomorrow");

            // select two records and edit them
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");

            await click(rows[0], ".o_data_cell");
            assert.containsOnce(
                list.el,
                "input.o_datepicker_input",
                "should have date picker input"
            );

            const input = list.el.querySelector(".o_datepicker_input");
            input.value = "blabla";
            await triggerEvents(input, null, ["input", "change"]);
            await click(list.el);

            assert.containsNone(document.body, ".modal");
            assert.strictEqual(
                document.querySelector(".modal .o_field_widget").textContent,
                "In 2 days",
                "should have 'In 2 days' value to change"
            );
            await click(document.body, ".modal .modal-footer .btn-primary");

            assert.strictEqual(
                rows[0].querySelector(".o_data_cell").textContent,
                "In 2 days",
                "should have 'In 2 days' as date field value"
            );
            assert.strictEqual(
                rows[1].querySelector(".o_data_cell").textContent,
                "In 2 days",
                "should have 'In 2 days' as date field value"
            );
        }
    );

    QUnit.skip(
        "RemainingDaysField, enter wrong value manually in multi edit list view",
        async function (assert) {
            assert.expect(6);

            patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
            serverData.models.partner.records = [
                { id: 1, date: "2017-10-08" }, // today
                { id: 2, date: "2017-10-09" }, // tomorrow
                { id: 8, date: false },
            ];

            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                    <tree multi_edit="1">
                        <field name="date" widget="remaining_days" />
                    </tree>
                `,
            });

            const cells = list.el.querySelectorAll(".o_data_cell");
            const rows = list.el.querySelectorAll(".o_data_row");

            assert.strictEqual(cells[0].textContent, "Today");
            assert.strictEqual(cells[1].textContent, "Tomorrow");

            // select two records and edit them
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");

            await click(rows[0], ".o_data_cell");
            assert.containsOnce(
                list.el,
                "input.o_datepicker_input",
                "should have date picker input"
            );

            const input = list.el.querySelector(".o_datepicker_input");
            input.value = "blabla";
            await triggerEvents(input, null, ["input", "change"]);
            await click(list.el);

            assert.containsNone(document.body, ".modal");
            assert.strictEqual(cells[0].textContent, "Today");
            assert.strictEqual(cells[1].textContent, "Tomorrow");
        }
    );

    QUnit.test("RemainingDaysField on a date field in form view", async function (assert) {
        assert.expect(8);

        patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
        serverData.models.partner.records = [
            { id: 1, date: "2017-10-08" }, // today
        ];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="date" widget="remaining_days" />
                </form>
            `,
        });

        assert.strictEqual(form.el.querySelector(".o_field_widget").textContent, "Today");
        assert.hasClass(form.el.querySelector(".o_field_widget"), "font-weight-bold text-warning");

        // in edit mode, this widget should be editable.
        await click(form.el, ".o_form_button_edit");

        assert.containsOnce(form.el, ".o_form_editable");
        assert.containsOnce(form.el, "div.o_field_widget[name='date'] .o_datepicker");

        await click(form.el.querySelector(".o_datepicker .o_datepicker_input"));
        assert.containsOnce(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should be opened"
        );

        await click(document.body, ".bootstrap-datetimepicker-widget .day[data-day='10/09/2017']");
        await click(form.el, ".o_form_button_save");
        assert.strictEqual(form.el.querySelector(".o_field_widget").textContent, "Tomorrow");

        await click(form.el, ".o_form_button_edit");
        await click(form.el.querySelector(".o_datepicker .o_datepicker_input"));
        await click(document.body, ".bootstrap-datetimepicker-widget .day[data-day='10/07/2017']");
        await click(form.el, ".o_form_button_save");
        assert.strictEqual(form.el.querySelector(".o_field_widget").textContent, "Yesterday");
        assert.hasClass(form.el.querySelector(".o_field_widget"), "text-danger");
    });

    QUnit.test("RemainingDaysField on a datetime field in form view", async function (assert) {
        assert.expect(6);

        patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
        serverData.models.partner.records = [
            { id: 1, datetime: "2017-10-08 10:00:00" }, // today
        ];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="datetime" widget="remaining_days" />
                </form>
            `,
        });
        assert.strictEqual(form.el.querySelector(".o_field_widget").textContent, "Today");
        assert.hasClass(form.el.querySelector(".o_field_widget"), "text-warning");

        // in edit mode, this widget should be editable.
        await click(form.el, ".o_form_button_edit");

        assert.containsOnce(form.el, ".o_form_editable");
        assert.containsOnce(form.el, "div.o_field_widget[name='datetime'] .o_datepicker");

        await click(form.el.querySelector(".o_datepicker .o_datepicker_input"));
        assert.containsOnce(
            document.body,
            ".bootstrap-datetimepicker-widget",
            "datepicker should be opened"
        );

        await click(document.body, ".bootstrap-datetimepicker-widget .day[data-day='10/09/2017']");
        await click(document.body, "a[data-action='close']");
        await click(form.el, ".o_form_button_save");
        assert.strictEqual(form.el.querySelector(".o_field_widget").textContent, "Tomorrow");
    });

    QUnit.skip(
        "RemainingDaysField on a datetime field in list view in UTC",
        async function (assert) {
            assert.expect(16);

            patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
            serverData.models.partner.records = [
                { id: 1, datetime: "2017-10-08 20:00:00" }, // today
                { id: 2, datetime: "2017-10-09 08:00:00" }, // tomorrow
                { id: 3, datetime: "2017-10-07 18:00:00" }, // yesterday
                { id: 4, datetime: "2017-10-10 22:00:00" }, // + 2 days
                { id: 5, datetime: "2017-10-05 04:00:00" }, // - 3 days
                { id: 6, datetime: "2018-02-08 04:00:00" }, // + 4 months (diff >= 100 days)
                { id: 7, datetime: "2017-06-08 04:00:00" }, // - 4 months (diff >= 100 days)
                { id: 8, datetime: false },
            ];

            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                    <tree>
                        <field name="datetime" widget="remaining_days" />
                    </tree>
                `,
                session: {
                    getTZOffset: () => 0,
                },
            });

            assert.strictEqual(list.$(".o_data_cell:nth(0)").text(), "Today");
            assert.strictEqual(list.$(".o_data_cell:nth(1)").text(), "Tomorrow");
            assert.strictEqual(list.$(".o_data_cell:nth(2)").text(), "Yesterday");
            assert.strictEqual(list.$(".o_data_cell:nth(3)").text(), "In 2 days");
            assert.strictEqual(list.$(".o_data_cell:nth(4)").text(), "3 days ago");
            assert.strictEqual(list.$(".o_data_cell:nth(5)").text(), "02/08/2018");
            assert.strictEqual(list.$(".o_data_cell:nth(6)").text(), "06/08/2017");
            assert.strictEqual(list.$(".o_data_cell:nth(7)").text(), "");

            assert.strictEqual(
                list.$(".o_data_cell:nth(0) .o_field_widget").attr("title"),
                "10/08/2017"
            );

            assert.hasClass(list.$(".o_data_cell:nth(0) div"), "font-weight-bold text-warning");
            assert.doesNotHaveClass(
                list.$(".o_data_cell:nth(1) div"),
                "font-weight-bold text-warning text-danger"
            );
            assert.hasClass(list.$(".o_data_cell:nth(2) div"), "font-weight-bold text-danger");
            assert.doesNotHaveClass(
                list.$(".o_data_cell:nth(3) div"),
                "font-weight-bold text-warning text-danger"
            );
            assert.hasClass(list.$(".o_data_cell:nth(4) div"), "font-weight-bold text-danger");
            assert.doesNotHaveClass(
                list.$(".o_data_cell:nth(5) div"),
                "font-weight-bold text-warning text-danger"
            );
            assert.hasClass(list.$(".o_data_cell:nth(6) div"), "font-weight-bold text-danger");
        }
    );

    QUnit.skip(
        "RemainingDaysField on a datetime field in list view in UTC+6",
        async function (assert) {
            assert.expect(6);

            patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11, UTC+6
            serverData.models.partner.records = [
                { id: 1, datetime: "2017-10-08 20:00:00" }, // tomorrow
                { id: 2, datetime: "2017-10-09 08:00:00" }, // tomorrow
                { id: 3, datetime: "2017-10-07 18:30:00" }, // today
                { id: 4, datetime: "2017-10-07 12:00:00" }, // yesterday
                { id: 5, datetime: "2017-10-09 20:00:00" }, // + 2 days
            ];

            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                    <tree>
                        <field name="datetime" widget="remaining_days" />
                    </tree>
                `,
                session: {
                    getTZOffset: () => 360,
                },
            });

            assert.strictEqual(list.$(".o_data_cell:nth(0)").text(), "Tomorrow");
            assert.strictEqual(list.$(".o_data_cell:nth(1)").text(), "Tomorrow");
            assert.strictEqual(list.$(".o_data_cell:nth(2)").text(), "Today");
            assert.strictEqual(list.$(".o_data_cell:nth(3)").text(), "Yesterday");
            assert.strictEqual(list.$(".o_data_cell:nth(4)").text(), "In 2 days");

            assert.strictEqual(
                list.$(".o_data_cell:nth(0) .o_field_widget").attr("title"),
                "10/09/2017"
            );
        }
    );

    QUnit.skip("RemainingDaysField on a date field in list view in UTC-6", async function (assert) {
        assert.expect(6);

        patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
        serverData.models.partner.records = [
            { id: 1, date: "2017-10-08" }, // today
            { id: 2, date: "2017-10-09" }, // tomorrow
            { id: 3, date: "2017-10-07" }, // yesterday
            { id: 4, date: "2017-10-10" }, // + 2 days
            { id: 5, date: "2017-10-05" }, // - 3 days
        ];

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree>
                    <field name="date" widget="remaining_days" />
                </tree>
            `,
            session: {
                getTZOffset: () => -360,
            },
        });

        assert.strictEqual(list.$(".o_data_cell:nth(0)").text(), "Today");
        assert.strictEqual(list.$(".o_data_cell:nth(1)").text(), "Tomorrow");
        assert.strictEqual(list.$(".o_data_cell:nth(2)").text(), "Yesterday");
        assert.strictEqual(list.$(".o_data_cell:nth(3)").text(), "In 2 days");
        assert.strictEqual(list.$(".o_data_cell:nth(4)").text(), "3 days ago");

        assert.strictEqual(
            list.$(".o_data_cell:nth(0) .o_field_widget").attr("title"),
            "10/08/2017"
        );
    });

    QUnit.skip(
        "RemainingDaysField on a datetime field in list view in UTC-8",
        async function (assert) {
            assert.expect(5);

            patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11, UTC-8
            serverData.models.partner.records = [
                { id: 1, datetime: "2017-10-08 20:00:00" }, // today
                { id: 2, datetime: "2017-10-09 07:00:00" }, // today
                { id: 3, datetime: "2017-10-09 10:00:00" }, // tomorrow
                { id: 4, datetime: "2017-10-08 06:00:00" }, // yesterday
                { id: 5, datetime: "2017-10-07 02:00:00" }, // - 2 days
            ];

            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                    <tree>
                        <field name="datetime" widget="remaining_days" />
                    </tree>
                `,
                session: {
                    getTZOffset: () => -560,
                },
            });

            assert.strictEqual(list.$(".o_data_cell:nth(0)").text(), "Today");
            assert.strictEqual(list.$(".o_data_cell:nth(1)").text(), "Today");
            assert.strictEqual(list.$(".o_data_cell:nth(2)").text(), "Tomorrow");
            assert.strictEqual(list.$(".o_data_cell:nth(3)").text(), "Yesterday");
            assert.strictEqual(list.$(".o_data_cell:nth(4)").text(), "2 days ago");
        }
    );
});
