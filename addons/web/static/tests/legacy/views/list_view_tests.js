/** @odoo-module alias=@web/../tests/views/list_view_tests default=false */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { uiService } from "@web/core/ui/ui_service";
import {
    click,
    dragAndDrop,
    editInput,
    getFixture,
    getNodesTextContent,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerEvents,
    triggerHotkey,
} from "../helpers/utils";
import { makeView, setupViewRegistries } from "./helpers";

const serviceRegistry = registry.category("services");

let serverData;
let target;

function getGroup(position) {
    return target.querySelectorAll(".o_group_header")[position - 1];
}

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        date: { string: "Some Date", type: "date" },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            aggregator: "sum",
                        },
                        text: { string: "text field", type: "text" },
                        qux: { string: "my float", type: "float", aggregator: "sum" },
                        m2o: { string: "M2O field", type: "many2one", relation: "bar" },
                        o2m: { string: "O2M field", type: "one2many", relation: "bar" },
                        m2m: { string: "M2M field", type: "many2many", relation: "bar" },
                        amount: { string: "Monetary field", type: "monetary", aggregator: "sum" },
                        amount_currency: {
                            string: "Monetary field (currency)",
                            type: "monetary",
                            currency_field: "company_currency_id",
                        },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "res_currency",
                            default: 1,
                        },
                        currency_test: {
                            string: "Currency",
                            type: "many2one",
                            relation: "res_currency",
                            default: 1,
                        },
                        company_currency_id: {
                            string: "Company Currency",
                            type: "many2one",
                            relation: "res_currency",
                            default: 2,
                        },
                        datetime: { string: "Datetime Field", type: "datetime" },
                        reference: {
                            string: "Reference Field",
                            type: "reference",
                            selection: [
                                ["bar", "Bar"],
                                ["res_currency", "Currency"],
                                ["event", "Event"],
                            ],
                        },
                        properties: {
                            type: "properties",
                            definition_record: "m2o",
                            definition_record_field: "definitions",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.4,
                            m2o: 1,
                            m2m: [1, 2],
                            amount: 1200,
                            amount_currency: 1100,
                            currency_id: 2,
                            company_currency_id: 1,
                            date: "2017-01-25",
                            datetime: "2016-12-12 10:55:05",
                            reference: "bar,1",
                            properties: [],
                        },
                        {
                            id: 2,
                            bar: true,
                            foo: "blip",
                            int_field: 9,
                            qux: 13,
                            m2o: 2,
                            m2m: [1, 2, 3],
                            amount: 500,
                            reference: "res_currency,1",
                            properties: [],
                        },
                        {
                            id: 3,
                            bar: true,
                            foo: "gnap",
                            int_field: 17,
                            qux: -3,
                            m2o: 1,
                            m2m: [],
                            amount: 300,
                            reference: "res_currency,2",
                            properties: [],
                        },
                        {
                            id: 4,
                            bar: false,
                            foo: "blip",
                            int_field: -4,
                            qux: 9,
                            m2o: 1,
                            m2m: [1],
                            amount: 0,
                            properties: [],
                        },
                    ],
                },
                bar: {
                    fields: {
                        definitions: { type: "properties_definitions" },
                    },
                    records: [
                        { id: 1, display_name: "Value 1", definitions: [] },
                        { id: 2, display_name: "Value 2", definitions: [] },
                        { id: 3, display_name: "Value 3", definitions: [] },
                    ],
                },
                res_currency: {
                    fields: {
                        symbol: { string: "Symbol", type: "char" },
                        position: {
                            string: "Position",
                            type: "selection",
                            selection: [
                                ["after", "A"],
                                ["before", "B"],
                            ],
                        },
                    },
                    records: [
                        { id: 1, display_name: "USD", symbol: "$", position: "before" },
                        { id: 2, display_name: "EUR", symbol: "€", position: "after" },
                    ],
                },
                event: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "name", type: "char" },
                    },
                    records: [{ id: "2-20170808020000", name: "virtual" }],
                },
            },
        };
        setupViewRegistries();
        serviceRegistry.add("tooltip", tooltipService);
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
        target = getFixture();
        serviceRegistry.add("ui", uiService);
    });

    QUnit.module("ListView");

    QUnit.test(
        "multi_edit: edit a required field with invalid value and click 'Ok' of alert dialog",
        async function (assert) {
            serverData.models.foo.fields.foo.required = true;

            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <list multi_edit="1">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </list>
                `,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });
            assert.containsN(target, ".o_data_row", 4);
            assert.verifySteps(["get_views", "web_search_read"]);

            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[0].querySelector(".o_data_cell"));
            await editInput(target, "[name='foo'] input", "");
            await click(target, ".o_list_view");
            assert.containsOnce(target, ".modal");
            assert.strictEqual(target.querySelector(".modal .btn").textContent, "Ok");

            await click(target.querySelector(".modal .btn"));
            assert.strictEqual(
                target.querySelector(".o_data_row .o_data_cell[name='foo']").textContent,
                "yop"
            );
            assert.hasClass(target.querySelector(".o_data_row"), "o_data_row_selected");

            assert.verifySteps([]);
        }
    );

    QUnit.test(
        "multi_edit: edit a required field with invalid value and dismiss alert dialog",
        async function (assert) {
            serverData.models.foo.fields.foo.required = true;
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <list multi_edit="1">
                    <field name="foo"/>
                    <field name="int_field"/>
                </list>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });
            assert.containsN(target, ".o_data_row", 4);
            assert.verifySteps(["get_views", "web_search_read"]);

            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[0].querySelector(".o_data_cell"));
            await editInput(target, "[name='foo'] input", "");
            await click(target, ".o_list_view");

            assert.containsOnce(target, ".modal");
            await click(target.querySelector(".modal-header .btn-close"));
            assert.strictEqual(
                target.querySelector(".o_data_row .o_data_cell[name='foo']").textContent,
                "yop"
            );
            assert.hasClass(target.querySelector(".o_data_row"), "o_data_row_selected");
            assert.verifySteps([]);
        }
    );

    QUnit.test("column widths are re-computed on window resize", async function (assert) {
        serverData.models.foo.records[0].text =
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
            "Sed blandit, justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus " +
            "ipsum purus bibendum est.";

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <list editable="bottom">
                    <field name="datetime"/>
                    <field name="text"/>
                </list>`,
        });

        const initialTextWidth = target.querySelectorAll('th[data-name="text"]')[0].offsetWidth;
        const selectorWidth = target.querySelectorAll("th.o_list_record_selector")[0].offsetWidth;

        // simulate a window resize
        target.style.width = target.getBoundingClientRect().width / 2 + "px";
        window.dispatchEvent(new Event("resize"));

        const postResizeTextWidth = target.querySelectorAll('th[data-name="text"]')[0].offsetWidth;
        const postResizeSelectorWidth = target.querySelectorAll("th.o_list_record_selector")[0]
            .offsetWidth;
        assert.ok(postResizeTextWidth < initialTextWidth);
        assert.strictEqual(selectorWidth, postResizeSelectorWidth);
    });

    QUnit.test(
        "editable list view: multi edition error and cancellation handling",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                    <list multi_edit="1">
                        <field name="foo" required="1"/>
                        <field name="int_field"/>
                    </list>`,
            });

            assert.containsN(target, ".o_list_record_selector input:enabled", 5);

            // select two records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");

            // edit a line and cancel
            await click(rows[0].querySelector(".o_data_cell"));
            assert.containsNone(target, ".o_list_record_selector input:enabled");
            await editInput(target, ".o_selected_row [name=foo] input", "abc");
            await click(target, ".modal .btn.btn-secondary");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "yop10",
                "first cell should have discarded any change"
            );
            assert.containsN(target, ".o_list_record_selector input:enabled", 5);

            // edit a line with an invalid format type
            await click(rows[0].querySelectorAll(".o_data_cell")[1]);
            assert.containsNone(target, ".o_list_record_selector input:enabled");

            await editInput(target, ".o_selected_row [name=int_field] input", "hahaha");
            assert.containsOnce(target, ".modal", "there should be an opened modal");

            await click(target, ".modal .btn-primary");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "yop10",
                "changes should be discarded"
            );
            assert.containsN(target, ".o_list_record_selector input:enabled", 5);

            // edit a line with an invalid value
            await click(rows[0].querySelector(".o_data_cell"));
            assert.containsNone(target, ".o_list_record_selector input:enabled");

            await editInput(target, ".o_selected_row [name=foo] input", "");
            assert.containsOnce(target, ".modal", "there should be an opened modal");
            await click(target, ".modal .btn-primary");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "yop10",
                "changes should be discarded"
            );
            assert.containsN(target, ".o_list_record_selector input:enabled", 5);
        }
    );

    QUnit.test(
        'editable list view: mousedown on "Discard", mouseup somewhere else (no multi-edit)',
        async function (assert) {
            await makeView({
                type: "list",
                arch: `
                    <list editable="top">
                        <field name="foo"/>
                    </list>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
                serverData,
                resModel: "foo",
            });

            // select two records
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");
            await click(rows[1], ".o_list_record_selector input");
            await click(rows[0].querySelector(".o_data_cell"));
            target.querySelector(".o_data_row .o_data_cell input").value = "oof";

            await triggerEvents($(".o_list_button_discard:visible").get(0), null, ["mousedown"]);
            await triggerEvents(target, ".o_data_row .o_data_cell input", [
                "change",
                "blur",
                "focusout",
            ]);
            await triggerEvents(target, null, ["focus"]);
            await triggerEvents(target, null, ["mouseup"]);
            await click(target);

            assert.containsNone(document.body, ".modal", "should not open modal");
            assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
                "oof",
                "blip",
                "gnap",
                "blip",
            ]);
            assert.verifySteps(["get_views", "web_search_read", "web_save"]);
        }
    );

    QUnit.test(
        "editable readonly list view: single edition does not behave like a multi-edition",
        async function (assert) {
            await makeView({
                type: "list",
                arch: `
                    <list multi_edit="1">
                        <field name="foo" required="1"/>
                    </list>`,
                serverData,
                resModel: "foo",
            });

            // select a record
            const rows = target.querySelectorAll(".o_data_row");
            await click(rows[0], ".o_list_record_selector input");

            // edit a field (invalid input)
            await click(rows[0].querySelector(".o_data_cell"));
            await editInput(target, ".o_data_row [name=foo] input", "");
            assert.containsOnce(target, ".modal", "should have a modal (invalid fields)");

            await click(target, ".modal button.btn");

            // edit a field
            await click(rows[0].querySelector(".o_data_cell"));
            await editInput(target, ".o_data_row [name=foo] input", "bar");
            assert.containsNone(target, ".modal", "should not have a modal");
            assert.strictEqual(
                $(target).find(".o_data_row:eq(0) .o_data_cell").text(),
                "bar",
                "the first row should be updated"
            );
        }
    );

    QUnit.test(
        "pressing ESC in editable grouped list should discard the current line changes",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<list editable="top"><field name="foo"/><field name="bar"/></list>',
                groupBy: ["bar"],
            });

            await click(target.querySelectorAll(".o_group_header")[1]); // open second group
            assert.containsN(target, "tr.o_data_row", 3);

            await click(target.querySelector(".o_data_cell"));

            // update foo field of edited row
            await editInput(target, ".o_data_cell [name=foo] input", "new_value");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_data_cell [name=foo] input")
            );
            // discard by pressing ESC
            triggerHotkey("Escape");
            await nextTick();
            assert.containsNone(target, ".modal");

            assert.containsOnce(target, "tbody tr td:contains(yop)");
            assert.containsN(target, "tr.o_data_row", 3);
            assert.containsNone(target, "tr.o_data_row.o_selected_row");
            assert.isNotVisible(target.querySelector(".o_list_button_save"));
        }
    );

    QUnit.test("editing then pressing TAB in editable grouped list", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<list editable="bottom"><field name="foo"/></list>',
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
            groupBy: ["bar"],
        });

        // open two groups
        await click(getGroup(1));
        assert.containsN(target, ".o_data_row", 1, "first group contains 1 rows");
        await click(getGroup(2));
        assert.containsN(target, ".o_data_row", 4, "first group contains 3 row");

        // select and edit last row of first group
        await click(target.querySelector(".o_data_row").querySelector(".o_data_cell"));
        assert.hasClass($(target).find(".o_data_row:nth(0)"), "o_selected_row");
        await editInput(target, '.o_selected_row [name="foo"] input', "new value");

        // Press 'Tab' -> should create a new record as we edited the previous one
        triggerHotkey("Tab");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.hasClass($(target).find(".o_data_row:nth(1)"), "o_selected_row");

        // fill foo field for the new record and press 'tab' -> should create another record
        await editInput(target, '.o_selected_row [name="foo"] input', "new record");
        triggerHotkey("Tab");
        await nextTick();

        assert.containsN(target, ".o_data_row", 6);
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        // leave this new row empty and press tab -> should discard the new record and move to the
        // next group
        triggerHotkey("Tab");
        await nextTick();
        assert.containsN(target, ".o_data_row", 5);
        assert.hasClass($(target).find(".o_data_row:nth(2)"), "o_selected_row");

        assert.verifySteps([
            "get_views",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "web_save",
            "onchange",
            "web_save",
            "onchange",
        ]);
    });

    QUnit.test("cell-level keyboard navigation in editable grouped list", async function (assert) {
        serverData.models.foo.records[0].bar = false;
        serverData.models.foo.records[1].bar = false;
        serverData.models.foo.records[2].bar = false;
        serverData.models.foo.records[3].bar = true;

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <list editable="bottom">
                    <field name="foo" required="1"/>
                </list>`,
            groupBy: ["bar"],
        });

        await click(target.querySelector(".o_group_name"));
        const secondDataRow = target.querySelectorAll(".o_data_row")[1];
        await click(secondDataRow, "[name=foo]");
        assert.hasClass(secondDataRow, "o_selected_row");

        await editInput(secondDataRow, "[name=foo] input", "blipbloup");

        triggerHotkey("Escape");
        await nextTick();

        assert.containsNone(document.body, ".modal");

        assert.doesNotHaveClass(secondDataRow, "o_selected_row");

        assert.strictEqual(document.activeElement, secondDataRow.querySelector("[name=foo]"));

        assert.strictEqual(document.activeElement.textContent, "blip");

        triggerHotkey("ArrowLeft");

        assert.strictEqual(
            document.activeElement,
            secondDataRow.querySelector("input[type=checkbox]")
        );

        triggerHotkey("ArrowUp");
        triggerHotkey("ArrowRight");

        const firstDataRow = target.querySelector(".o_data_row");
        assert.strictEqual(document.activeElement, firstDataRow.querySelector("[name=foo]"));

        triggerHotkey("Enter");
        await nextTick();

        assert.hasClass(firstDataRow, "o_selected_row");
        await editInput(firstDataRow, "[name=foo] input", "Zipadeedoodah");

        triggerHotkey("Enter");
        await nextTick();

        assert.strictEqual(firstDataRow.querySelector("[name=foo]").innerText, "Zipadeedoodah");
        assert.doesNotHaveClass(firstDataRow, "o_selected_row");
        assert.hasClass(secondDataRow, "o_selected_row");
        assert.strictEqual(document.activeElement, secondDataRow.querySelector("[name=foo] input"));
        assert.strictEqual(document.activeElement.value, "blip");

        triggerHotkey("ArrowUp");
        triggerHotkey("ArrowRight");
        await nextTick();

        assert.strictEqual(document.activeElement, secondDataRow.querySelector("[name=foo] input"));
        assert.strictEqual(document.activeElement.value, "blip");

        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowLeft");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            secondDataRow.querySelector("td[name=foo] input")
        );
        assert.strictEqual(document.activeElement.value, "blip");

        triggerHotkey("Escape");
        await nextTick();

        assert.doesNotHaveClass(secondDataRow, "o_selected_row");

        assert.strictEqual(document.activeElement, secondDataRow.querySelector("td[name=foo]"));

        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_field_row_add a")
        );

        triggerHotkey("ArrowDown");

        const secondGroupHeader = target.querySelectorAll(".o_group_name")[1];
        assert.strictEqual(document.activeElement, secondGroupHeader);

        assert.containsN(target, ".o_data_row", 3);

        triggerHotkey("Enter");
        await nextTick();

        assert.containsN(target, ".o_data_row", 4);

        assert.strictEqual(document.activeElement, secondGroupHeader);

        triggerHotkey("ArrowDown");

        const fourthDataRow = target.querySelectorAll(".o_data_row")[3];
        assert.strictEqual(document.activeElement, fourthDataRow.querySelector("[name=foo]"));

        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelectorAll(".o_group_field_row_add a")[1]
        );

        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelectorAll(".o_group_field_row_add a")[1]
        );

        // default Enter on a A tag
        const event = await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
        assert.ok(!event.defaultPrevented);
        await click(target.querySelectorAll(".o_group_field_row_add a")[1]);

        const fifthDataRow = target.querySelectorAll(".o_data_row")[4];
        assert.strictEqual(document.activeElement, fifthDataRow.querySelector("[name=foo] input"));

        await editInput(
            fifthDataRow.querySelector("[name=foo] input"),
            null,
            "cheateur arrete de cheater"
        );

        triggerHotkey("Enter");
        await nextTick();

        assert.containsN(target, ".o_data_row", 6);

        triggerHotkey("Escape");
        await nextTick();

        assert.strictEqual(
            document.activeElement,
            target.querySelectorAll(".o_group_field_row_add a")[1]
        );

        // come back to the top
        for (let i = 0; i < 9; i++) {
            triggerHotkey("ArrowUp");
        }

        assert.strictEqual(document.activeElement, target.querySelector("thead th:nth-child(2)"));

        triggerHotkey("ArrowLeft");

        assert.strictEqual(
            document.activeElement,
            target.querySelector("thead th.o_list_record_selector input")
        );

        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowDown");
        triggerHotkey("ArrowRight");

        assert.strictEqual(document.activeElement, firstDataRow.querySelector("td[name=foo]"));

        triggerHotkey("ArrowUp");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        assert.containsN(target, ".o_data_row", 5);

        triggerHotkey("Enter");
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowRight");
        await nextTick();

        assert.containsN(target, ".o_data_row", 5);

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowRight");
        await nextTick();

        assert.containsN(target, ".o_data_row", 5);

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowLeft");
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowLeft");
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(1) .o_group_name")
        );

        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_header:nth-child(2) .o_group_name")
        );

        triggerHotkey("ArrowDown");

        const firstVisibleDataRow = target.querySelector(".o_data_row");
        assert.strictEqual(document.activeElement, firstVisibleDataRow.querySelector("[name=foo]"));

        triggerHotkey("ArrowDown");

        const secondVisibleDataRow = target.querySelectorAll(".o_data_row")[1];
        assert.strictEqual(
            document.activeElement,
            secondVisibleDataRow.querySelector("[name=foo]")
        );

        triggerHotkey("ArrowDown");

        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o_group_field_row_add a")
        );

        triggerHotkey("ArrowUp");

        assert.strictEqual(
            document.activeElement,
            secondVisibleDataRow.querySelector("[name=foo]")
        );

        triggerHotkey("ArrowUp");
        assert.strictEqual(document.activeElement, firstVisibleDataRow.querySelector("[name=foo]"));
    });

    QUnit.test("editable list: resize column headers", async function (assert) {
        // This test will ensure that, on resize list header,
        // the resized element have the correct size and other elements are not resized
        serverData.models.foo.records[0].foo = "a".repeat(200);

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: `
                <list editable="top">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="reference" optional="hide"/>
                </list>`,
        });

        // Target handle
        const th = target.querySelector("th:nth-child(2)");
        const thNext = target.querySelector("th:nth-child(3)");
        const resizeHandle = th.querySelector(".o_resize");
        const nextResizeHandle = thNext.querySelector(".o_resize");
        const thOriginalWidth = th.getBoundingClientRect().width;
        const thNextOriginalWidth = thNext.getBoundingClientRect().width;
        const thExpectedWidth = thOriginalWidth + thNextOriginalWidth;

        await dragAndDrop(resizeHandle, nextResizeHandle);

        const thFinalWidth = th.getBoundingClientRect().width;
        const thNextFinalWidth = thNext.getBoundingClientRect().width;

        assert.ok(
            Math.abs(Math.floor(thFinalWidth) - Math.floor(thExpectedWidth)) <= 1,
            `Wrong width on resize (final: ${thFinalWidth}, expected: ${thExpectedWidth})`
        );
        assert.strictEqual(
            Math.floor(thNextOriginalWidth),
            Math.floor(thNextFinalWidth),
            "Width must not have been changed"
        );
    });

    QUnit.test(
        "continue creating new lines in editable=top on keyboard nav",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: `
                <list editable="top">
                    <field name="int_field"/>
                </list>`,
            });

            const initialRowCount = $(".o_data_cell[name=int_field]").length;

            // click on int_field cell of first row
            await click($(".o_list_button_add:visible").get(0));

            await editInput(target, ".o_data_cell[name=int_field] input", "1");
            triggerHotkey("Tab");
            await nextTick();

            await editInput(target, ".o_data_cell[name=int_field] input", "2");
            triggerHotkey("Enter");
            await nextTick();

            // 3 new rows: the two created ("1" and "2", and a new still in edit mode)
            assert.strictEqual($(".o_data_cell[name=int_field]").length, initialRowCount + 3);
        }
    );
});
