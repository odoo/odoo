/** @odoo-module **/

import { makeFakeDialogService } from "@web/../tests/helpers/mock_services";
import {
    click,
    clickSave,
    drag,
    dragAndDrop,
    editInput,
    getFixture,
    getNodesTextContent,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import {
    getFacetTexts,
    getPagerLimit,
    getPagerValue,
    pagerNext,
    toggleFilterMenu,
    validateSearch,
} from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { dialogService } from "@web/core/dialog/dialog_service";
import { makeErrorFromResponse, RPCError } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { nbsp } from "@web/core/utils/strings";
import { getNextTabableElement } from "@web/core/utils/ui";
import { session } from "@web/session";
import { KanbanAnimatedNumber } from "@web/views/kanban/kanban_animated_number";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { DynamicRecordList } from "@web/views/relational_model";
import { ViewButton } from "@web/views/view_button/view_button";
import AbstractField from "web.AbstractField";
import legacyFieldRegistry from "web.field_registry";

const { Component, onWillStart, xml } = owl;

const serviceRegistry = registry.category("services");
const viewWidgetRegistry = registry.category("view_widgets");

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

function patchDialog(addDialog) {
    serviceRegistry.add("dialog", makeFakeDialogService(addDialog), { force: true });
}

// Kanban
// WOWL remove this helper and use the control panel instead
async function reload(kanban, params = {}) {
    kanban.env.searchModel.reload(params);
    kanban.env.searchModel.search();
    await nextTick();
}

function getCard(cardIndex = 0) {
    return target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")[cardIndex];
}

function getColumn(groupIndex = 0, ignoreFolded = false) {
    let selector = ".o_kanban_group";
    if (ignoreFolded) {
        selector += ":not(.o_column_folded)";
    }
    return target.querySelectorAll(selector)[groupIndex];
}

function getCardTexts(groupIndex) {
    const root = groupIndex >= 0 ? getColumn(groupIndex) : target;
    return [...root.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")]
        .map((card) => card.innerText.trim())
        .filter(Boolean);
}

function getCounters() {
    return [...target.querySelectorAll(".o_kanban_counter_side")].map(
        (counter) => counter.innerText
    );
}

function getProgressBars(columnIndex) {
    const column = getColumn(columnIndex);
    return [...column.querySelectorAll(".o_kanban_counter_progress .progress-bar")];
}

function getTooltips(groupIndex) {
    const root = groupIndex >= 0 ? getColumn(groupIndex) : target;
    return [...root.querySelectorAll(".o_kanban_counter_progress .progress-bar")]
        .map((card) => card.dataset.tooltip)
        .filter(Boolean);
}

// Record
async function createRecord() {
    await click(target, "button.o-kanban-button-new");
}

async function quickCreateRecord(groupIndex, position = "top") {
    if (position === "top") {
        await click(getColumn(groupIndex), ".o_kanban_quick_add");
    } else if (position === "bottom") {
        await click(getColumn(groupIndex), ".o_kanban_quick_add_bottom");
    }
}

async function editQuickCreateInput(field, value) {
    await editInput(target, `.o_kanban_quick_create .o_field_widget[name=${field}] input`, value);
}

async function validateRecord() {
    await click(target, ".o_kanban_quick_create .o_kanban_add");
}

async function editRecord() {
    await click(target, ".o_kanban_quick_create .o_kanban_edit");
}

async function discardRecord() {
    await click(target, ".o_kanban_quick_create .o_kanban_cancel");
}

async function toggleRecordDropdown(recordIndex) {
    const group = target.querySelectorAll(`.o_kanban_record`)[recordIndex];
    await click(group, ".o_dropdown_kanban .dropdown-toggle");
}

// Column
async function createColumn() {
    await click(target, ".o_column_quick_create > .o_quick_create_folded");
}

async function editColumnName(value) {
    await editInput(target, ".o_column_quick_create input", value);
}

async function validateColumn() {
    await click(target, ".o_column_quick_create .o_kanban_add");
}

async function toggleColumnActions(columnIndex) {
    const group = getColumn(columnIndex);
    await click(group, ".o_kanban_config .dropdown-toggle");
    const buttons = group.querySelectorAll(".o_kanban_config .dropdown-menu .dropdown-item");
    return (buttonText) => {
        const re = new RegExp(`\\b${buttonText}\\b`, "i");
        const button = [...buttons].find((b) => re.test(b.innerText));
        return click(button);
    };
}

async function loadMore(columnIndex) {
    await click(getColumn(columnIndex), ".o_kanban_load_more button");
}

let serverData;
let target;

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(KanbanAnimatedNumber, { enableAnimations: false });
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        qux: { string: "my float", type: "float" },
                        product_id: {
                            string: "something_id",
                            type: "many2one",
                            relation: "product",
                        },
                        category_ids: {
                            string: "categories",
                            type: "many2many",
                            relation: "category",
                        },
                        sequence: { type: "integer" },
                        state: {
                            string: "State",
                            type: "selection",
                            selection: [
                                ["abc", "ABC"],
                                ["def", "DEF"],
                                ["ghi", "GHI"],
                            ],
                        },
                        date: { string: "Date Field", type: "date" },
                        datetime: { string: "Datetime Field", type: "datetime" },
                        image: { string: "Image", type: "binary" },
                        displayed_image_id: {
                            string: "cover",
                            type: "many2one",
                            relation: "ir.attachment",
                        },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            default: 1,
                        },
                        salary: { string: "Monetary field", type: "monetary" },
                    },
                    records: [
                        {
                            id: 1,
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.4,
                            product_id: 3,
                            state: "abc",
                            category_ids: [],
                            image: "R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==",
                            salary: 1750,
                            currency_id: 1,
                        },
                        {
                            id: 2,
                            bar: true,
                            foo: "blip",
                            int_field: 9,
                            qux: 13,
                            product_id: 5,
                            state: "def",
                            category_ids: [6],
                            salary: 1500,
                            currency_id: 1,
                        },
                        {
                            id: 3,
                            bar: true,
                            foo: "gnap",
                            int_field: 17,
                            qux: -3,
                            product_id: 3,
                            state: "ghi",
                            category_ids: [7],
                            salary: 2000,
                            currency_id: 2,
                        },
                        {
                            id: 4,
                            bar: false,
                            foo: "blip",
                            int_field: -4,
                            qux: 9,
                            product_id: 5,
                            state: "ghi",
                            category_ids: [],
                            salary: 2222,
                            currency_id: 1,
                        },
                    ],
                },
                product: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Display Name", type: "char" },
                    },
                    records: [
                        { id: 3, name: "hello" },
                        { id: 5, name: "xmo" },
                    ],
                },
                category: {
                    fields: {
                        name: { string: "Category Name", type: "char" },
                        color: { string: "Color index", type: "integer" },
                    },
                    records: [
                        { id: 6, name: "gold", color: 2 },
                        { id: 7, name: "silver", color: 5 },
                    ],
                },
                "ir.attachment": {
                    fields: {
                        mimetype: { type: "char" },
                        name: { type: "char" },
                        res_model: { type: "char" },
                        res_id: { type: "integer" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "1.png",
                            mimetype: "image/png",
                            res_model: "partner",
                            res_id: 1,
                        },
                        {
                            id: 2,
                            name: "2.png",
                            mimetype: "image/png",
                            res_model: "partner",
                            res_id: 2,
                        },
                    ],
                },
                currency: {
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
            },
            views: {},
        };
        target = getFixture();

        setupViewRegistries();
    });

    QUnit.module("KanbanView");

    QUnit.test("basic ungrouped rendering", async (assert) => {
        assert.expect(6);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban class="o_kanban_test">
                    <templates><t t-name="kanban-box">
                        <div>
                            <t t-esc="record.foo.value"/>
                            <field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>`,
            mockRPC(route, args) {
                if (args.method === "web_search_read") {
                    assert.ok(
                        args.kwargs.context.bin_size,
                        "should not request direct binary payload"
                    );
                }
            },
        });

        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_ungrouped");
        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_test");
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);
        assert.containsN(target, ".o_kanban_ghost", 6);
        assert.containsOnce(target, ".o_kanban_record:contains(gnap)");
    });

    QUnit.test("basic grouped rendering", async (assert) => {
        assert.expect(13);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban class="o_kanban_test">
                    <field name="bar" />
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["bar"],
            async mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    // the lazy option is important, so the server can fill in
                    // the empty groups
                    assert.ok(args.kwargs.lazy, "should use lazy read_group");
                }
            },
        });

        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_test");
        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);

        await toggleColumnActions(0);

        // check available actions in kanban header's config dropdown
        assert.containsOnce(
            target,
            ".o_kanban_header:first-child .o_kanban_config .o_kanban_toggle_fold"
        );
        assert.containsNone(target, ".o_kanban_header:first-child .o_kanban_config .o_column_edit");
        assert.containsNone(
            target,
            ".o_kanban_header:first-child .o_kanban_config .o_column_delete"
        );
        assert.containsNone(
            target,
            ".o_kanban_header:first-child .o_kanban_config .o_column_archive_records"
        );
        assert.containsNone(
            target,
            ".o_kanban_header:first-child .o_kanban_config .o_column_unarchive_records"
        );

        // the next line makes sure that reload works properly.  It looks useless,
        // but it actually test that a grouped local record can be reloaded without
        // changing its result.
        await validateSearch(target);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);
    });

    QUnit.test(
        "basic grouped rendering with active field (archivable by default)",
        async (assert) => {
            // add active field on partner model and make all records active
            serverData.models.partner.fields.active = {
                string: "Active",
                type: "char",
                default: true,
            };

            patchDialog((_cls, props) => {
                assert.step("open-dialog");
                props.confirm();
            });

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<field name="active"/>' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["bar"],
            });

            const clickColumnAction = await toggleColumnActions(1);

            // check archive/restore all actions in kanban header's config dropdown
            assert.containsOnce(
                target,
                ".o_kanban_group:last-child .o_kanban_header .o_kanban_config .o_column_archive_records"
            );
            assert.containsOnce(
                target,
                ".o_kanban_group:last-child .o_kanban_header .o_kanban_config .o_column_unarchive_records"
            );
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
            assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 3);
            assert.verifySteps([]);

            await clickColumnAction("Archive All");

            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsOnce(getColumn(0), ".o_kanban_record");
            assert.containsNone(getColumn(1), ".o_kanban_record");
            assert.verifySteps(["open-dialog"]);
        }
    );

    QUnit.test(
        "basic grouped rendering with active field and archive enabled (archivable true)",
        async (assert) => {
            // add active field on partner model and make all records active
            serverData.models.partner.fields.active = {
                string: "Active",
                type: "char",
                default: true,
            };

            patchDialog((_cls, props) => {
                assert.step("open-dialog");
                props.confirm();
            });

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban archivable="true">' +
                    '<field name="active"/>' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["bar"],
            });

            const clickColumnAction = await toggleColumnActions(0);

            // check archive/restore all actions in kanban header's config dropdown
            assert.containsOnce(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_archive_records"
            );
            assert.containsOnce(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_unarchive_records"
            );
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
            assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 3);
            assert.verifySteps([]);

            await clickColumnAction("Archive All");

            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsNone(getColumn(0), ".o_kanban_record");
            assert.containsN(getColumn(1), ".o_kanban_record", 3);
            assert.verifySteps(["open-dialog"]);
        }
    );

    QUnit.test(
        "basic grouped rendering with active field and hidden archive buttons (archivable false)",
        async (assert) => {
            // add active field on partner model and make all records active
            serverData.models.partner.fields.active = {
                string: "Active",
                type: "char",
                default: true,
            };

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban archivable="false">' +
                    '<field name="active"/>' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["bar"],
            });

            await toggleColumnActions(0);

            // check archive/restore all actions in kanban header's config dropdown
            assert.containsNone(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_archive_records"
            );
            assert.containsNone(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_unarchive_records"
            );
        }
    );

    QUnit.test(
        "m2m grouped rendering with active field and archive enabled (archivable true)",
        async (assert) => {
            // add active field on partner model and make all records active
            serverData.models.partner.fields.active = {
                string: "Active",
                type: "char",
                default: true,
            };

            // more many2many data
            serverData.models.partner.records[0].category_ids = [6, 7];
            serverData.models.partner.records[3].foo = "blork";
            serverData.models.partner.records[3].category_ids = [];

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                <kanban archivable="true">
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
                groupBy: ["category_ids"],
            });

            assert.containsN(target, ".o_kanban_group", 3);
            assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
            assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 2);

            assert.deepEqual(
                [...target.querySelectorAll(".o_kanban_group")].map((el) =>
                    el.innerText.replace(/\s/g, " ")
                ),
                ["None (1)", "gold yop blip", "silver yop gnap"]
            );

            await click(getColumn(0));
            await toggleColumnActions(0);

            // check archive/restore all actions in kanban header's config dropdown
            // despite the fact that the kanban view is configured to be archivable,
            // the actions should not be there as it is grouped by an m2m field.
            assert.containsNone(
                target,
                ".o_kanban_header .o_kanban_config .o_column_archive_records",
                "should not be able to archive all the records"
            );
            assert.containsNone(
                target,
                ".o_kanban_header .o_kanban_config .o_column_unarchive_records",
                "should not be able to unarchive all the records"
            );
        }
    );

    QUnit.test("kanban grouped by date field", async (assert) => {
        serverData.models.partner.records[0].date = "2007-06-10";
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="date"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["date"],
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_column_title")), [
            "None",
            "June 2007",
        ]);
    });
    QUnit.test("context can be used in kanban template", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates><t t-name="kanban-box">
                        <div>
                            <t t-if="context.some_key">
                                <field name="foo"/>
                            </t>
                        </div>
                    </t></templates>
                </kanban>`,
            context: { some_key: 1 },
            domain: [["id", "=", 1]],
        });

        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.containsOnce(
            target,
            ".o_kanban_record span:contains(yop)",
            "condition in the kanban template should have been correctly evaluated"
        );
    });

    QUnit.test("user context can be used in kanban template", async (assert) => {
        const fakeUserService = {
            start() {
                return { context: { some_key: true } };
            },
        };
        serviceRegistry.add("user", fakeUserService, { force: true });
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field t-if="user_context.some_key" name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            domain: [["id", "=", 1]],
        });

        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.containsOnce(
            target,
            ".o_kanban_record span:contains(yop)",
            "condition in the kanban template should have been correctly evaluated"
        );
    });

    QUnit.test("kanban with sub-template", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <t t-call="another-template"/>
                            </div>
                        </t>
                        <t t-name="another-template">
                            <span><field name="foo"/></span>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")),
            ["yop", "blip", "gnap", "blip"]
        );
    });

    QUnit.test("kanban with t-set outside card", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="int_field"/>
                    <templates>
                        <t t-name="kanban-box">
                            <t t-set="x" t-value="record.int_field.value"/>
                            <div>
                                <t t-esc="x"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")),
            ["10", "9", "17", "-4"]
        );
    });

    QUnit.test("kanban with t-if/t-else on field", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field t-if="record.int_field.value > -1" name="int_field"/>
                                <t t-else="">Negative value</t>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")),
            ["10", "9", "17", "Negative value"]
        );
    });

    QUnit.test("kanban with t-if/t-else on field with widget", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field t-if="record.int_field.value > -1" name="int_field" widget="integer"/>
                                <t t-else="">Negative value</t>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")),
            ["10", "9", "17", "Negative value"]
        );
    });

    QUnit.test("field with widget and attributes in kanban", async (assert) => {
        assert.expect(1);

        class MyField extends Component {
            setup() {
                if (this.props.record.resId === 1) {
                    assert.deepEqual(this.props.attrs, {
                        name: "int_field",
                        widget: "my_field",
                        str: "some string",
                        bool: "true",
                        num: "4.5",
                        options: {},
                        field_id: "int_field",
                    });
                }
            }
        }
        MyField.template = xml`<span/>`;
        MyField.extractProps = ({ attrs }) => ({ attrs });
        registry.category("fields").add("my_field", MyField);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="foo"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field" widget="my_field"
                                    str="some string"
                                    bool="true"
                                    num="4.5"
                                />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });
    });

    QUnit.test("field with widget and dynamic attributes in kanban", async (assert) => {
        class MyField extends Component {}
        MyField.template = xml`<span/>`;
        MyField.extractProps = ({ attrs }) => {
            assert.step(
                `${attrs["dyn-bool"]}/${attrs["interp-str"]}/${attrs["interp-str2"]}/${attrs["interp-str3"]}`
            );
        };
        registry.category("fields").add("my_field", MyField);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="foo"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field" widget="my_field"
                                    t-att-dyn-bool="record.foo.value.length > 3"
                                    t-attf-interp-str="hello {{record.foo.value}}"
                                    t-attf-interp-str2="hello #{record.foo.value} !"
                                    t-attf-interp-str3="hello {{record.foo.value}} }}"
                                />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });
        assert.verifySteps([
            "false/hello yop/hello yop !/hello yop }}",
            "true/hello blip/hello blip !/hello blip }}",
            "true/hello gnap/hello gnap !/hello gnap }}",
            "true/hello blip/hello blip !/hello blip }}",
        ]);
    });

    QUnit.test("view button and string interpolated attribute in kanban", async (assert) => {
        patchWithCleanup(ViewButton.prototype, {
            setup() {
                this._super();
                assert.step(
                    `[${this.props.clickParams["name"]}] className: '${this.props.className}'`
                );
            },
        });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="foo"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <a name="one" type="object" class="hola"/>
                                <a name="two" type="object" class="hola" t-attf-class="hello"/>
                                <a name="sri" type="object" class="hola" t-attf-class="{{record.foo.value}}"/>
                                <a name="foa" type="object" class="hola" t-attf-class="{{record.foo.value}} olleh"/>
                                <a name="fye" type="object" class="hola" t-attf-class="hello {{record.foo.value}}"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });
        assert.verifySteps([
            "[one] className: 'hola oe_kanban_action oe_kanban_action_a'",
            "[two] className: 'hola oe_kanban_action oe_kanban_action_a hello'",
            "[sri] className: 'hola oe_kanban_action oe_kanban_action_a yop'",
            "[foa] className: 'hola oe_kanban_action oe_kanban_action_a yop olleh'",
            "[fye] className: 'hola oe_kanban_action oe_kanban_action_a hello yop'",
            "[one] className: 'hola oe_kanban_action oe_kanban_action_a'",
            "[two] className: 'hola oe_kanban_action oe_kanban_action_a hello'",
            "[sri] className: 'hola oe_kanban_action oe_kanban_action_a blip'",
            "[foa] className: 'hola oe_kanban_action oe_kanban_action_a blip olleh'",
            "[fye] className: 'hola oe_kanban_action oe_kanban_action_a hello blip'",
            "[one] className: 'hola oe_kanban_action oe_kanban_action_a'",
            "[two] className: 'hola oe_kanban_action oe_kanban_action_a hello'",
            "[sri] className: 'hola oe_kanban_action oe_kanban_action_a gnap'",
            "[foa] className: 'hola oe_kanban_action oe_kanban_action_a gnap olleh'",
            "[fye] className: 'hola oe_kanban_action oe_kanban_action_a hello gnap'",
            "[one] className: 'hola oe_kanban_action oe_kanban_action_a'",
            "[two] className: 'hola oe_kanban_action oe_kanban_action_a hello'",
            "[sri] className: 'hola oe_kanban_action oe_kanban_action_a blip'",
            "[foa] className: 'hola oe_kanban_action oe_kanban_action_a blip olleh'",
            "[fye] className: 'hola oe_kanban_action oe_kanban_action_a hello blip'",
        ]);
    });

    QUnit.test("kanban with kanban-tooltip template", async (assert) => {
        serviceRegistry.add("tooltip", tooltipService);
        let simulateTimeout;
        let simulateInterval;
        patchWithCleanup(browser, {
            setTimeout: (fn) => {
                simulateTimeout = fn;
            },
            setInterval: (fn) => {
                simulateInterval = fn;
            },
        });
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-tooltip">
                            <ul class="oe_kanban_tooltip">
                                <li><t t-esc="record.foo.value" /></li>
                            </ul>
                        </t>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")),
            ["yop", "blip", "gnap", "blip"]
        );

        assert.containsNone(target, ".o_popover_container .o_popover");
        target.querySelector(".o_kanban_record").dispatchEvent(new Event("mouseenter"));
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");

        simulateTimeout();
        await nextTick();
        assert.containsOnce(target, ".o_popover_container .o_popover");
        assert.strictEqual(
            target.querySelector(".o_popover_container .o_popover").innerText,
            "yop"
        );

        const recordRect = target.querySelector(".o_kanban_record").getBoundingClientRect();
        const x = recordRect.right + 10;
        const y = recordRect.bottom + 10;
        await triggerEvent(target.querySelector(".o_kanban_record"), null, "mousemove", {
            pageX: x,
            layerX: x,
            screenX: x,
            pageY: y,
            layerY: y,
            screenY: y,
        });
        assert.containsOnce(target, ".o_popover_container .o_popover");
        simulateInterval();
        await nextTick();
        assert.containsNone(target, ".o_popover_container .o_popover");
    });

    QUnit.test("pager should be hidden in grouped mode", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });

        assert.containsNone(target, ".o_pager");
    });

    QUnit.test("pager, ungrouped, with default limit", async (assert) => {
        assert.expect(3);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            async mockRPC(route, { method, kwargs }) {
                if (method === "web_search_read") {
                    assert.strictEqual(kwargs.limit, 40, "default limit should be 40 in Kanban");
                }
            },
        });

        assert.containsOnce(target, ".o_pager");
        assert.deepEqual(getPagerValue(target), [1, 4]);
    });

    QUnit.test("pager, ungrouped, with limit given in options", async (assert) => {
        assert.expect(3);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            async mockRPC(route, { method, kwargs }) {
                if (method === "web_search_read") {
                    assert.strictEqual(kwargs.limit, 2);
                }
            },
            limit: 2,
        });

        assert.deepEqual(getPagerValue(target), [1, 2]);
        assert.strictEqual(getPagerLimit(target), 4);
    });

    QUnit.test("pager, ungrouped, with limit set on arch and given in options", async (assert) => {
        assert.expect(3);

        // the limit given in the arch should take the priority over the one given in options
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban limit="3">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            async mockRPC(route, { method, kwargs }) {
                if (method === "web_search_read") {
                    assert.strictEqual(kwargs.limit, 3);
                }
            },
            limit: 2,
        });

        assert.deepEqual(getPagerValue(target), [1, 3]);
        assert.strictEqual(getPagerLimit(target), 4);
    });

    QUnit.test("pager, ungrouped, with count limit reached", async (assert) => {
        patchWithCleanup(DynamicRecordList, { WEB_SEARCH_READ_COUNT_LIMIT: 3 });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban limit="2">
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            async mockRPC(route, { method }) {
                assert.step(method);
            },
        });

        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "3+");
        assert.verifySteps(["get_views", "web_search_read"]);

        await click(target.querySelector(".o_pager_limit"));
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);
        assert.strictEqual(target.querySelector(".o_pager_value").innerText, "1-2");
        assert.strictEqual(target.querySelector(".o_pager_limit").innerText, "4");
        assert.verifySteps(["search_count"]);
    });

    QUnit.test(
        "pager, ungrouped, deleting all records from last page should move to previous page",
        async (assert) => {
            patchDialog((_cls, props) => {
                assert.step("open-dialog");
                props.confirm();
            });

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `<kanban limit="3">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <div><a role="menuitem" type="delete" class="dropdown-item">Delete</a></div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });

            assert.deepEqual(getPagerValue(target), [1, 3]);
            assert.strictEqual(getPagerLimit(target), 4);

            // move to next page
            await pagerNext(target);

            assert.deepEqual(getPagerValue(target), [4, 4]);

            // delete a record
            await click(target, ".o_kanban_record a");

            assert.verifySteps(["open-dialog"]);
            assert.deepEqual(getPagerValue(target), [1, 3]);
            assert.strictEqual(getPagerLimit(target), 3);
        }
    );

    QUnit.test("kanban with an action id as on_create attrs", async (assert) => {
        const actionService = {
            start() {
                return {
                    doAction: (action, options) => {
                        // simplified flow in this test: simulate a target new action which
                        // creates a record and closes itself
                        assert.step(`doAction ${action}`);
                        serverData.models.partner.records.push({ id: 299, foo: "new" });
                        options.onClose();
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="some.action">
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);
        await createRecord();
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 5);
        assert.verifySteps([
            "get_views",
            "web_search_read",
            "doAction some.action",
            "web_search_read",
        ]);
    });

    QUnit.test("grouped kanban with quick_create attrs set to false", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban quick_create="false" on_create="quick_create">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            createRecord: () => assert.step("create record"),
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsNone(target, ".o_kanban_quick_add");

        await click(target.querySelector(".o-kanban-button-new"));

        assert.containsNone(target, ".o_kanban_quick_create");
        assert.verifySteps(["create record"]);
    });

    QUnit.test("create in grouped on m2o", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        assert.containsN(target, ".o_kanban_group.o_group_draggable", 2);
        assert.containsOnce(target, ".btn-primary.o-kanban-button-new");
        assert.containsOnce(target, ".o_column_quick_create");

        await createRecord();

        assert.containsOnce(target, ".o_kanban_group:first-child > .o_kanban_quick_create");
        assert.strictEqual(target.querySelector(".o_column_title").innerText, "hello");
    });

    QUnit.test("create in grouped on char", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["foo"],
        });

        assert.containsNone(target, ".o_kanban_group.o_group_draggable");
        assert.containsN(target, ".o_kanban_group", 3);
        assert.strictEqual(target.querySelector(".o_column_title").innerText, "blip");
        assert.containsNone(target, ".o_kanban_group:first-child > .o_kanban_quick_create");
    });

    QUnit.test("prevent deletion when grouped by many2many field", async (assert) => {
        serverData.models.partner.records[0].category_ids = [6, 7];
        serverData.models.partner.records[3].category_ids = [7];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="foo"/>
                                <t t-if="widget.deletable"><span class="thisisdeletable">delete</span></t>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["category_ids"],
        });

        assert.containsNone(target, ".thisisdeletable", "records should not be deletable");

        await reload(kanban, { groupBy: ["foo"] });

        assert.containsN(target, ".thisisdeletable", 4, "records should be deletable");
    });

    QUnit.test("quick created records in grouped kanban are on displayed top", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="display_name"/></div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 2);

        await createRecord();
        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 2);
        assert.containsOnce(target.querySelector(".o_kanban_group"), ".o_kanban_quick_create");

        await editInput(target, ".o_field_widget[name=display_name] input", "new record");
        await click(target, ".o_kanban_add");
        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 3);
        assert.containsOnce(target.querySelector(".o_kanban_group"), ".o_kanban_quick_create");
        // the new record must be the first record of the column
        assert.strictEqual(target.querySelector(".o_kanban_record").innerText, "new record");

        await editInput(target, ".o_field_widget[name=display_name] input", "another record");
        await click(target, ".o_kanban_add");
        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 4);
        assert.containsOnce(target.querySelector(".o_kanban_group"), ".o_kanban_quick_create");
        // the new record must be the first record of the column
        assert.strictEqual(target.querySelector(".o_kanban_record").innerText, "another record");
        assert.strictEqual(target.querySelectorAll(".o_kanban_record")[1].innerText, "new record");
    });

    QUnit.test("quick create record without quick_create_view", async (assert) => {
        assert.expect(16);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
            async mockRPC(route, { args, method }) {
                assert.step(method || route);
                if (method === "name_create") {
                    assert.strictEqual(args[0], "new partner");
                }
            },
        });

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");

        // click on 'Create' -> should open the quick create in the first column
        await createRecord();

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_quick_create");

        const quickCreate = target.querySelector(
            ".o_kanban_group:first-child .o_kanban_quick_create"
        );

        assert.containsOnce(quickCreate, ".o_form_view.o_xxs_form_view");
        assert.containsOnce(quickCreate, "input");
        assert.containsOnce(
            quickCreate,
            ".o_field_widget.o_required_modifier input[placeholder=Title]"
        );

        // fill the quick create and validate
        await editQuickCreateInput("display_name", "new partner");
        await validateRecord();

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);

        assert.verifySteps([
            "get_views",
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "onchange", // quick create
            "name_create", // should perform a name_create to create the record
            "read", // read the created record
            "onchange", // reopen the quick create automatically
        ]);
    });

    QUnit.test("quick create record with quick_create_view", async (assert) => {
        assert.expect(19);

        serverData.views["partner,some_view_ref,form"] =
            "<form>" +
            '<field name="foo"/>' +
            '<field name="int_field"/>' +
            '<field name="state" widget="priority"/>' +
            "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
            async mockRPC(route, args) {
                assert.step(args.method || route);
                if (args.method === "create") {
                    assert.deepEqual(
                        args.args[0],
                        {
                            foo: "new partner",
                            int_field: 4,
                            state: "def",
                        },
                        "should send the correct values"
                    );
                }
            },
        });

        assert.containsOnce(target, ".o_control_panel", "should have one control panel");
        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");

        // click on 'Create' -> should open the quick create in the first column
        await createRecord();

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_quick_create");
        const quickCreate = target.querySelector(
            ".o_kanban_group:first-child .o_kanban_quick_create"
        );

        assert.containsOnce(quickCreate, ".o_form_view.o_xxs_form_view");
        assert.containsOnce(
            target,
            ".o_control_panel",
            "should not have instantiated an extra control panel"
        );
        assert.containsN(quickCreate, "input", 2);
        assert.containsN(quickCreate, ".o_field_widget", 3, "should have rendered three widgets");

        // fill the quick create and validate
        await editQuickCreateInput("foo", "new partner");
        await editQuickCreateInput("int_field", 4);
        await click(quickCreate, ".o_field_widget[name=state] .o_priority_star:first-child");
        await validateRecord();
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);

        assert.verifySteps([
            "get_views",
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "get_views", // form view in quick create
            "onchange", // quick create
            "create", // should perform a create to create the record
            "read", // read the created record
            "onchange", // new quick create
        ]);
    });

    QUnit.test(
        "quick create record should focus default field [REQUIRE FOCUS]",
        async function (assert) {
            serverData.views["partner,some_view_ref,form"] =
                "<form>" +
                '<field name="foo"/>' +
                '<field name="int_field" default_focus="1"/>' +
                '<field name="state" widget="priority"/>' +
                "</form>";

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["bar"],
            });

            await click(target, ".o-kanban-button-new");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_field_widget[name=int_field] input")
            );
        }
    );

    QUnit.test(
        "quick create record should focus first field input [REQUIRE FOCUS]",
        async function (assert) {
            serverData.views["partner,some_view_ref,form"] =
                "<form>" +
                '<field name="foo"/>' +
                '<field name="int_field"/>' +
                '<field name="state" widget="priority"/>' +
                "</form>";

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["bar"],
            });

            await click(target, ".o-kanban-button-new");
            assert.strictEqual(
                document.activeElement,
                target.querySelector(".o_field_widget[name=foo] input")
            );
        }
    );

    QUnit.test("quick_create_view without quick_create option", async (assert) => {
        serverData.views["partner,some_view_ref,form"] = `
            <form>
                <field name="display_name"/>
            </form>`;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban quick_create_view="some_view_ref">
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["bar"],
            createRecord() {
                assert.step("create record");
            },
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(target, ".o_kanban_group .o_kanban_quick_add", 2);

        // click on 'Create' in control panel -> should not open the quick create
        await createRecord();
        assert.containsNone(target, ".o_kanban_quick_create");
        assert.verifySteps(["create record"]);

        // click "+" icon in first column -> should open the quick create
        await click(target.querySelector(".o_kanban_quick_add"));
        assert.containsOnce(target.querySelector(".o_kanban_group"), ".o_kanban_quick_create");
        assert.verifySteps([]);
    });

    QUnit.test("quick create record in grouped on m2o (no quick_create_view)", async (assert) => {
        assert.expect(14);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, { method, args, kwargs }) {
                assert.step(method || route);
                if (method === "name_create") {
                    assert.strictEqual(args[0], "new partner");
                    const { default_product_id, default_qux } = kwargs.context;
                    assert.strictEqual(default_product_id, 3);
                    assert.strictEqual(default_qux, 2.5);
                }
            },
            context: { default_qux: 2.5 },
        });

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "first column should contain two records"
        );

        // click on 'Create', fill the quick create and validate
        await createRecord();
        await editQuickCreateInput("display_name", "new partner");
        await validateRecord();

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            3,
            "first column should contain three records"
        );

        assert.verifySteps([
            "get_views",
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "onchange", // quick create
            "name_create", // should perform a name_create to create the record
            "read", // read the created record
            "onchange", // reopen the quick create automatically
        ]);
    });

    QUnit.test("quick create record in grouped on m2o (with quick_create_view)", async (assert) => {
        assert.expect(15);

        serverData.views["partner,some_view_ref,form"] =
            "<form>" +
            '<field name="foo"/>' +
            '<field name="int_field"/>' +
            '<field name="state" widget="priority"/>' +
            "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, { method, args, kwargs }) {
                assert.step(method || route);
                if (method === "create") {
                    assert.deepEqual(
                        args[0],
                        {
                            foo: "new partner",
                            int_field: 4,
                            state: "def",
                        },
                        "should send the correct values"
                    );
                    const { default_product_id, default_qux } = kwargs.context;
                    assert.strictEqual(default_product_id, 3);
                    assert.strictEqual(default_qux, 2.5);
                }
            },
            context: { default_qux: 2.5 },
        });

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);

        // click on 'Create', fill the quick create and validate
        await createRecord();
        const quickCreate = target.querySelector(
            ".o_kanban_group:first-child .o_kanban_quick_create"
        );
        await editQuickCreateInput("foo", "new partner");
        await editQuickCreateInput("int_field", 4);
        await click(quickCreate, ".o_field_widget[name=state] .o_priority_star:first-child");
        await validateRecord();

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 3);

        assert.verifySteps([
            "get_views",
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "get_views", // form view in quick create
            "onchange", // quick create
            "create", // should perform a create to create the record
            "read", // read the created record
            "onchange", // reopen the quick create automatically
        ]);
    });

    QUnit.test("quick create record validation: stays open when invalid", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                    <field name="bar"/>
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>
            `,
            groupBy: ["bar"],
            async mockRPC(route, { method }) {
                assert.step(method || route);
            },
        });
        assert.verifySteps(["get_views", "web_read_group", "web_search_read", "web_search_read"]);

        await createRecord();
        assert.verifySteps(["onchange"]);

        // do not fill anything and validate
        await validateRecord();
        assert.verifySteps([]);
        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_quick_create");
        assert.hasClass(target.querySelector("[name=display_name]"), "o_field_invalid");
        assert.containsOnce(target, ".o_notification_manager .o_notification");
        assert.equal(
            target.querySelector(".o_notification").textContent,
            "Invalid fields: Display Name"
        );
    });

    QUnit.test("quick create record with default values and onchanges", async (assert) => {
        serverData.models.partner.fields.int_field.default = 4;
        serverData.models.partner.onchanges = {
            foo(obj) {
                if (obj.foo) {
                    obj.int_field = 8;
                }
            },
        };
        serverData.views["partner,some_view_ref,form"] =
            "<form>" + '<field name="foo"/>' + '<field name="int_field"/>' + "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
            async mockRPC(route, { method }) {
                assert.step(method || route);
            },
        });

        // click on 'Create' -> should open the quick create in the first column
        await createRecord();
        const quickCreate = target.querySelector(
            ".o_kanban_group:first-child .o_kanban_quick_create"
        );

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_quick_create");
        assert.strictEqual(
            quickCreate.querySelector(".o_field_widget[name=int_field] input").value,
            "4",
            "default value should be set"
        );

        // fill the 'foo' field -> should trigger the onchange
        await editQuickCreateInput("foo", "new partner");

        assert.strictEqual(
            quickCreate.querySelector(".o_field_widget[name=int_field] input").value,
            "8",
            "onchange should have been triggered"
        );

        assert.verifySteps([
            "get_views",
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "get_views", // form view in quick create
            "onchange", // quick create
            "onchange", // onchange due to 'foo' field change
        ]);
    });

    QUnit.test("quick create record with quick_create_view: modifiers", async (assert) => {
        serverData.views["partner,some_view_ref,form"] =
            "<form>" +
            '<field name="foo" required="1"/>' +
            '<field name="int_field" attrs=\'{"invisible": [["foo", "=", false]]}\'/>' +
            "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban quick_create_view="some_view_ref">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });
        // create a new record
        await quickCreateRecord();
        assert.hasClass(
            target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo]"),
            "o_required_modifier",
            "foo field should be required"
        );
        assert.containsNone(
            target,
            ".o_kanban_quick_create .o_field_widget[name=int_field]",
            "int_field should be invisible"
        );

        // fill 'foo' field
        await editQuickCreateInput("foo", "new partner");

        assert.containsOnce(
            target,
            ".o_kanban_quick_create .o_field_widget[name=int_field]",
            "int_field should now be visible"
        );
    });

    QUnit.test("quick create record with onchange of field marked readonly", async (assert) => {
        assert.expect(15);

        serverData.models.partner.onchanges = {
            foo(obj) {
                obj.int_field = 8;
            },
        };
        serverData.views["partner,some_view_ref,form"] = `<form>
            <field name="foo"/>
            <field name="int_field" readonly="true"/>
        </form>`;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `<kanban on_create="quick_create" quick_create_view="some_view_ref">
                <field name="bar"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
            groupBy: ["bar"],
            async mockRPC(route, { method, args }) {
                if (method === "create") {
                    assert.notOk(
                        "int_field" in args[0],
                        "readonly field shouldn't be sent in create"
                    );
                }
                assert.step(method || route);
            },
        });
        assert.verifySteps([
            "get_views",
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
        ]);

        // click on 'Create' -> should open the quick create in the first column
        await quickCreateRecord();
        assert.verifySteps(["get_views", "onchange"]);

        // fill the 'foo' field -> should trigger the onchange
        await editQuickCreateInput("foo", "new partner");
        assert.verifySteps(["onchange"]);
        await validateRecord();
        assert.verifySteps(["create", "read", "onchange"]);
    });

    QUnit.test("quick create record and change state in grouped mode", async (assert) => {
        serverData.models.partner.fields.kanban_state = {
            string: "Kanban State",
            type: "selection",
            selection: [
                ["normal", "Grey"],
                ["done", "Green"],
                ["blocked", "Red"],
            ],
        };

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                            <div class="oe_kanban_bottom_right">
                                <field name="kanban_state" widget="state_selection"/>
                            </div>
                        </div>
                    </templates>
                </kanban>
            `,
            groupBy: ["foo"],
        });

        // Quick create kanban record
        await quickCreateRecord();
        await editQuickCreateInput("display_name", "Test");
        await validateRecord();

        // Select state in kanban
        await click(getCard(0), ".o_status");
        await click(getCard(0), ".o_field_state_selection .dropdown-item:first-child");

        assert.hasClass(
            target.querySelector(".o_status"),
            "o_status_green",
            "Kanban state should be done (Green)"
        );
    });

    QUnit.test("window resize should not change quick create form size", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            groupBy: ["bar"],
            arch: `
                <kanban on_create="quick_create">
                    <field name="bar"/>
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>`,
        });

        await quickCreateRecord();
        assert.hasClass(
            target.querySelector(".o_kanban_quick_create .o_form_view"),
            "o_xxs_form_view"
        );

        await triggerEvent(window, "", "resize");
        assert.hasClass(
            target.querySelector(".o_kanban_quick_create .o_form_view"),
            "o_xxs_form_view"
        );
    });

    QUnit.test(
        "quick create record: cancel and validate without using the buttons",
        async (assert) => {
            serverData.views["partner,some_view_ref,form"] = `<form><field name="foo" /></form>`;

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban quick_create_view="some_view_ref" on_create="quick_create">' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["bar"],
            });

            assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

            // click to add an element and cancel the quick creation by pressing ESC
            await quickCreateRecord();

            assert.containsOnce(target, ".o_kanban_quick_create");

            await triggerEvent(target, ".o_kanban_quick_create input", "keydown", {
                key: "Escape",
            });

            assert.containsNone(
                target,
                ".o_kanban_quick_create",
                "should have destroyed the quick create element"
            );

            // click to add and element and click outside, should cancel the quick creation
            await quickCreateRecord();
            await click(target, ".o_kanban_group:first-child .o_kanban_record:last-of-type");
            assert.containsNone(
                target,
                ".o_kanban_quick_create",
                "the quick create should be destroyed when the user clicks outside"
            );

            // click to input and drag the mouse outside, should not cancel the quick creation
            await quickCreateRecord();
            await triggerEvent(target, ".o_kanban_quick_create input", "mousedown");
            await click(target, ".o_kanban_group:first-child .o_kanban_record:last-of-type");
            assert.containsOnce(
                target,
                ".o_kanban_quick_create",
                "the quick create should not have been destroyed after clicking outside"
            );

            // click to really add an element
            await quickCreateRecord();
            await editQuickCreateInput("foo", "new partner");

            // clicking outside should no longer destroy the quick create as it is dirty
            await click(target, ".o_kanban_group:first-child .o_kanban_record:last-of-type");
            assert.containsOnce(
                target,
                ".o_kanban_quick_create",
                "the quick create should not have been destroyed"
            );

            // confirm by pressing ENTER
            await triggerEvent(target, ".o_kanban_quick_create input", "keydown", {
                key: "Enter",
            });

            assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 5);
            assert.deepEqual(getCardTexts(0), ["new partner", "blip"]);
        }
    );

    QUnit.test("quick create record: validate with ENTER", async (assert) => {
        serverData.views["partner,some_view_ref,form"] =
            "<form>" + '<field name="foo"/>' + '<field name="int_field"/>' + "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });

        assert.containsN(target, ".o_kanban_record", 4, "should have 4 records at the beginning");

        // add an element and confirm by pressing ENTER
        await quickCreateRecord();
        await editQuickCreateInput("foo", "new partner");
        await validateRecord();
        // triggers a navigation event, leading to the 'commitChanges' and record creation

        assert.containsN(target, ".o_kanban_record", 5, "should have created a new record");
        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input").value,
            "",
            "quick create should now be empty"
        );
    });

    QUnit.test("quick create record: prevent multiple adds with ENTER", async (assert) => {
        serverData.views["partner,some_view_ref,form"] =
            "<form>" + '<field name="foo"/>' + '<field name="int_field"/>' + "</form>";

        const prom = makeDeferred();

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
            async mockRPC(route, args) {
                if (args.method === "create") {
                    assert.step("create");
                    await prom;
                }
            },
        });

        assert.containsN(target, ".o_kanban_record", 4, "should have 4 records at the beginning");

        // add an element and press ENTER twice
        await quickCreateRecord();
        await editQuickCreateInput("foo", "new partner");
        await triggerEvent(
            target,
            ".o_kanban_quick_create .o_field_widget[name=foo] input",
            "keydown",
            {
                key: "Enter",
            }
        );

        assert.containsN(target, ".o_kanban_record", 4, "should not have created the record yet");
        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input").value,
            "new partner",
            "quick create should not be empty yet"
        );
        assert.hasClass(
            target.querySelector(".o_kanban_quick_create"),
            "o_disabled",
            "quick create should be disabled"
        );

        prom.resolve();
        await nextTick();

        assert.containsN(target, ".o_kanban_record", 5, "should have created a new record");
        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input").value,
            "",
            "quick create should now be empty"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_quick_create"),
            "o_disabled",
            "quick create should be enabled"
        );

        assert.verifySteps(["create"]);
    });

    QUnit.test("quick create record: prevent multiple adds with Add clicked", async (assert) => {
        serverData.views["partner,some_view_ref,form"] =
            "<form>" + '<field name="foo"/>' + '<field name="int_field"/>' + "</form>";

        const prom = makeDeferred();
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
            async mockRPC(route, { method }) {
                if (method === "create") {
                    assert.step("create");
                    await prom;
                }
            },
        });

        assert.containsN(target, ".o_kanban_record", 4, "should have 4 records at the beginning");

        // add an element and click 'Add' twice
        await quickCreateRecord();
        await editQuickCreateInput("foo", "new partner");
        await validateRecord();
        await validateRecord();

        assert.containsN(target, ".o_kanban_record", 4, "should not have created the record yet");
        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input").value,
            "new partner",
            "quick create should not be empty yet"
        );
        assert.hasClass(
            target.querySelector(".o_kanban_quick_create"),
            "o_disabled",
            "quick create should be disabled"
        );

        prom.resolve();
        await nextTick();

        assert.containsN(target, ".o_kanban_record", 5, "should have created a new record");
        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input").value,
            "",
            "quick create should now be empty"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_quick_create"),
            "o_disabled",
            "quick create should be enabled"
        );

        assert.verifySteps(["create"]);
    });

    QUnit.test(
        "save a quick create record and create a new record at the same time",
        async (assert) => {
            const prom = makeDeferred();
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                    <kanban on_create="quick_create">
                        <field name="bar"/>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="display_name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
                groupBy: ["bar"],
                async mockRPC(route, { method }) {
                    if (method === "name_create") {
                        assert.step("name_create");
                        await prom;
                    }
                },
            });

            assert.containsN(
                target,
                ".o_kanban_record",
                4,
                "should have 4 records at the beginning"
            );

            // Create and save a record
            await quickCreateRecord();
            await editQuickCreateInput("display_name", "new partner");
            await validateRecord();
            assert.containsN(
                target,
                ".o_kanban_record",
                4,
                "should not have created the record yet"
            );
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create [name=display_name] input").value,
                "new partner",
                "quick create should not be empty yet"
            );
            assert.hasClass(
                target.querySelector(".o_kanban_quick_create"),
                "o_disabled",
                "quick create should be disabled"
            );

            // Create a new record during the save of the first one
            await createRecord();
            assert.containsN(
                target,
                ".o_kanban_record",
                4,
                "should not have created the record yet"
            );
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create [name=display_name] input").value,
                "new partner",
                "quick create should not be empty yet"
            );
            assert.hasClass(
                target.querySelector(".o_kanban_quick_create"),
                "o_disabled",
                "quick create should be disabled"
            );

            prom.resolve();
            await nextTick();
            assert.containsN(target, ".o_kanban_record", 5, "should have created a new record");
            assert.strictEqual(
                target.querySelector(
                    ".o_kanban_quick_create .o_field_widget[name=display_name] input"
                ).value,
                "",
                "quick create should now be empty"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o_kanban_quick_create"),
                "o_disabled",
                "quick create should be enabled"
            );

            assert.verifySteps(["name_create"]);
        }
    );

    QUnit.test(
        "quick create record: prevent multiple adds with ENTER, with onchange",
        async (assert) => {
            assert.expect(14);

            serverData.models.partner.onchanges = {
                foo(obj) {
                    obj.int_field += obj.foo ? 3 : 0;
                },
            };
            serverData.views["partner,some_view_ref,form"] =
                "<form>" + '<field name="foo"/>' + '<field name="int_field"/>' + "</form>";

            let shouldDelayOnchange = false;
            const prom = makeDeferred();
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["bar"],
                async mockRPC(route, { method, args }) {
                    switch (method) {
                        case "onchange": {
                            assert.step(method);
                            if (shouldDelayOnchange) {
                                await prom;
                            }
                            break;
                        }
                        case "create": {
                            assert.step(method);
                            assert.strictEqual(args[0].foo, "new partner");
                            assert.strictEqual(args[0].int_field, 3);
                            break;
                        }
                    }
                },
            });

            assert.containsN(
                target,
                ".o_kanban_record",
                4,
                "should have 4 records at the beginning"
            );

            // add an element and press ENTER twice
            await quickCreateRecord();
            shouldDelayOnchange = true;
            await editQuickCreateInput("foo", "new partner");
            await triggerEvent(
                target,
                ".o_kanban_quick_create .o_field_widget[name=foo] input",
                "keydown",
                {
                    key: "Enter",
                }
            );

            assert.containsN(
                target,
                ".o_kanban_record",
                4,
                "should not have created the record yet"
            );
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input")
                    .value,
                "new partner",
                "quick create should not be empty yet"
            );
            assert.hasClass(
                target.querySelector(".o_kanban_quick_create"),
                "o_disabled",
                "quick create should be disabled"
            );

            prom.resolve();
            await nextTick();

            assert.containsN(target, ".o_kanban_record", 5, "should have created a new record");
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input")
                    .value,
                "",
                "quick create should now be empty"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o_kanban_quick_create"),
                "o_disabled",
                "quick create should be enabled"
            );

            assert.verifySteps([
                "onchange", // default_get
                "onchange", // new partner
                "create",
                "onchange", // default_get
            ]);
        }
    );

    QUnit.test(
        "quick create record: click Add to create, with delayed onchange",
        async (assert) => {
            assert.expect(13);

            serverData.models.partner.onchanges = {
                foo(obj) {
                    obj.int_field += obj.foo ? 3 : 0;
                },
            };
            serverData.views["partner,some_view_ref,form"] =
                "<form>" + '<field name="foo"/>' + '<field name="int_field"/>' + "</form>";

            let shouldDelayOnchange = false;
            const prom = makeDeferred();
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/><field name="int_field"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["bar"],
                async mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.step("onchange");
                        if (shouldDelayOnchange) {
                            await prom;
                        }
                    }
                    if (args.method === "create") {
                        assert.step("create");
                        assert.deepEqual(_.pick(args.args[0], "foo", "int_field"), {
                            foo: "new partner",
                            int_field: 3,
                        });
                    }
                },
            });

            assert.containsN(
                target,
                ".o_kanban_record",
                4,
                "should have 4 records at the beginning"
            );

            // add an element and click 'add'
            await quickCreateRecord();
            shouldDelayOnchange = true;
            await editQuickCreateInput("foo", "new partner");
            await validateRecord();

            assert.containsN(
                target,
                ".o_kanban_record",
                4,
                "should not have created the record yet"
            );
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input")
                    .value,
                "new partner",
                "quick create should not be empty yet"
            );
            assert.hasClass(
                target.querySelector(".o_kanban_quick_create"),
                "o_disabled",
                "quick create should be disabled"
            );

            prom.resolve(); // the onchange returns

            await nextTick();
            assert.containsN(target, ".o_kanban_record", 5, "should have created a new record");
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create .o_field_widget[name=foo] input")
                    .value,
                "",
                "quick create should now be empty"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o_kanban_quick_create"),
                "o_disabled",
                "quick create should be enabled"
            );

            assert.verifySteps([
                "onchange", // default_get
                "onchange", // new partner
                "create",
                "onchange", // default_get
            ]);
        }
    );

    QUnit.test("quick create when first column is folded", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });

        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_group:first-child"),
            "o_column_folded",
            "first column should not be folded"
        );

        // fold the first column
        let clickColumnAction = await toggleColumnActions(0);
        await clickColumnAction("Fold");

        assert.hasClass(
            target.querySelector(".o_kanban_group:first-child"),
            "o_column_folded",
            "first column should be folded"
        );

        // click on 'Create' to open the quick create in the first column
        await createRecord();

        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_group:first-child"),
            "o_column_folded",
            "first column should no longer be folded"
        );
        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_quick_create",
            "should have added a quick create element in first column"
        );

        // fold again the first column
        clickColumnAction = await toggleColumnActions(0);
        await clickColumnAction("Fold");

        assert.hasClass(
            target.querySelector(".o_kanban_group:first-child"),
            "o_column_folded",
            "first column should be folded"
        );
        assert.containsNone(
            target,
            ".o_kanban_quick_create",
            "there should be no more quick create"
        );
    });

    QUnit.test("quick create record: cancel when not dirty", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should contain one record"
        );

        // click to add an element
        await quickCreateRecord();
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "should have open the quick create widget"
        );

        // click again to add an element -> should have kept the quick create open
        await quickCreateRecord();
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "should have kept the quick create open"
        );

        // click outside: should remove the quick create
        await click(target, ".o_kanban_group:first-child .o_kanban_record:last-of-type");
        assert.containsNone(
            target,
            ".o_kanban_quick_create",
            "the quick create should not have been destroyed"
        );

        // click to reopen the quick create
        await quickCreateRecord();
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "should have open the quick create widget"
        );

        // press ESC: should remove the quick create
        await triggerEvent(target, ".o_kanban_quick_create input", "keydown", { key: "Escape" });

        assert.containsNone(
            target,
            ".o_kanban_quick_create",
            "quick create widget should have been removed"
        );

        // click to reopen the quick create
        await quickCreateRecord();
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "should have open the quick create widget"
        );

        // click on 'Discard': should remove the quick create
        await quickCreateRecord();
        await discardRecord();
        assert.containsNone(
            target,
            ".o_kanban_quick_create",
            "the quick create should be destroyed when the user clicks outside"
        );

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should still contain one record"
        );

        // click to reopen the quick create
        await quickCreateRecord();
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "should have open the quick create widget"
        );

        // clicking on the quick create itself should keep it open
        await click(target, ".o_kanban_quick_create");
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "the quick create should not have been destroyed when clicked on itself"
        );
    });

    QUnit.test("quick create record: cancel when modal is opened", async (assert) => {
        serverData.views["partner,some_view_ref,form"] = '<form><field name="product_id"/></form>';

        // patch setTimeout s.t. the autocomplete dropdown opens directly
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            groupBy: ["bar"],
            arch: `
                <kanban on_create="quick_create" quick_create_view="some_view_ref">
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>`,
        });

        // click to add an element
        await quickCreateRecord();
        assert.containsOnce(target, ".o_kanban_quick_create");

        await editInput(target, ".o_kanban_quick_create input", "test");
        await triggerEvent(target, ".o_kanban_quick_create input", "input");
        await triggerEvent(target, ".o_kanban_quick_create input", "blur");

        // When focusing out of the many2one, a modal to add a 'product' will appear.
        // The following assertions ensures that a click on the body element that has 'modal-open'
        // will NOT close the quick create.
        // This can happen when the user clicks out of the input because of a race condition between
        // the focusout of the m2o and the global 'click' handler of the quick create.
        // Check odoo/odoo#61981 for more details.
        assert.hasClass(document.body, "modal-open", "modal should be opening after m2o focusout");
        await click(document.body);
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "quick create should stay open while modal is opening"
        );
    });

    QUnit.test("quick create record: cancel when dirty", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should contain one record"
        );

        // click to add an element and edit it
        await quickCreateRecord();

        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "should have open the quick create widget"
        );

        await editQuickCreateInput("display_name", "some value");

        // click outside: should not remove the quick create
        await click(target, ".o_kanban_group:first-child .o_kanban_record");

        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "the quick create should not have been destroyed"
        );

        // press ESC: should remove the quick create
        await triggerEvent(target, ".o_kanban_quick_create input", "keydown", { key: "Escape" });

        assert.containsNone(
            target,
            ".o_kanban_quick_create",
            "quick create widget should have been removed"
        );

        // click to reopen quick create and edit it
        await quickCreateRecord();

        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "should have open the quick create widget"
        );

        await editQuickCreateInput("display_name", "some value");

        // click on 'Discard': should remove the quick create
        await discardRecord();

        assert.containsNone(
            target,
            ".o_kanban_quick_create",
            "the quick create should be destroyed when the user discard quick creation"
        );

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should still contain one record"
        );
    });

    QUnit.test("quick create record and edit in grouped mode", async (assert) => {
        assert.expect(5);

        let newRecordID;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            async mockRPC(route, { args, method }) {
                if (method === "read") {
                    newRecordID = args[0][0];
                }
            },
            groupBy: ["bar"],
            selectRecord: (resId) => {
                assert.strictEqual(resId, newRecordID);
            },
        });

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should contain one record"
        );

        // click to add and edit a record
        await quickCreateRecord();
        await editQuickCreateInput("display_name", "new partner");
        await editRecord();

        assert.strictEqual(
            serverData.models.partner.records.length,
            5,
            "should have created a partner"
        );
        assert.strictEqual(
            _.last(serverData.models.partner.records).name,
            "new partner",
            "should have correct name"
        );
        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "first column should now contain two records"
        );
    });

    QUnit.test("quick create several records in a row", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should contain one record"
        );

        // click to add an element, fill the input and press ENTER
        await quickCreateRecord();

        assert.containsOnce(target, ".o_kanban_quick_create", "the quick create should be open");

        await editQuickCreateInput("display_name", "new partner 1");
        await validateRecord();

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "first column should now contain two records"
        );
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "the quick create should still be open"
        );

        // create a second element in a row
        await createRecord();
        await editQuickCreateInput("display_name", "new partner 2");
        await validateRecord();

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            3,
            "first column should now contain three records"
        );
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "the quick create should still be open"
        );
    });

    QUnit.test("quick create is disabled until record is created and read", async (assert) => {
        const prom = makeDeferred();
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
            async mockRPC(route, { method }) {
                if (method === "read") {
                    await prom;
                }
            },
        });

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should contain one record"
        );

        // click to add a record, and add two in a row (first one will be delayed)
        await quickCreateRecord();

        assert.containsOnce(target, ".o_kanban_quick_create", "the quick create should be open");

        await editQuickCreateInput("display_name", "new partner 1");
        await validateRecord();

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should still contain one record"
        );
        assert.containsOnce(
            target,
            ".o_kanban_quick_create.o_disabled",
            "quick create should be disabled"
        );

        prom.resolve();
        await nextTick();

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "first column should now contain two records"
        );
        assert.containsNone(
            target,
            ".o_kanban_quick_create.o_disabled",
            "quick create should be enabled"
        );
    });

    QUnit.test("quick create record fail in grouped by many2one", async (assert) => {
        serverData.views["partner,false,form"] = `
            <form>
                <field name="product_id"/>
                <field name="foo"/>
            </form>`;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                    <field name="product_id"/>
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (args.method === "name_create") {
                    throw makeErrorFromResponse({
                        code: 200,
                        message: "Odoo Server Error",
                        data: {
                            name: "odoo.exceptions.UserError",
                            debug: "traceback",
                            arguments: ["This is a user error"],
                            context: {},
                        },
                    });
                }
            },
        });

        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 2);

        await createRecord();
        assert.containsOnce(target.querySelector(".o_kanban_group"), ".o_kanban_quick_create");

        await editQuickCreateInput("display_name", "test");
        await validateRecord();
        assert.containsOnce(target, ".modal .o_form_view .o_form_editable");
        assert.strictEqual(target.querySelector(".modal .o_field_many2one input").value, "hello");

        // specify a name and save
        await editInput(target, ".modal .o_field_widget[name=foo] input", "test");
        await click(target, ".modal .o_form_button_save");
        assert.containsNone(target, ".modal");
        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 3);
        const firstRecord = target.querySelector(".o_kanban_group .o_kanban_record");
        assert.strictEqual(firstRecord.innerText, "test");
        assert.containsOnce(target, ".o_kanban_quick_create:not(.o_disabled)");
    });

    QUnit.test("quick create record is re-enabled after discard on failure", async (assert) => {
        serverData.views["partner,false,form"] = `
            <form>
                <field name="product_id"/>
                <field name="foo"/>
            </form>`;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                    <field name="product_id"/>
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (args.method === "name_create") {
                    throw makeErrorFromResponse({
                        code: 200,
                        message: "Odoo Server Error",
                        data: {
                            name: "odoo.exceptions.UserError",
                            debug: "traceback",
                            arguments: ["This is a user error"],
                            context: {},
                        },
                    });
                }
            },
        });

        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 2);

        await createRecord();
        assert.containsOnce(target.querySelector(".o_kanban_group"), ".o_kanban_quick_create");

        await editQuickCreateInput("display_name", "test");
        await validateRecord();
        assert.containsOnce(target, ".modal .o_form_view .o_form_editable");

        await click(target.querySelector(".modal .o_form_button_cancel"));
        assert.containsNone(target, ".modal .o_form_view .o_form_editable");
        assert.containsOnce(target.querySelector(".o_kanban_group"), ".o_kanban_quick_create");
        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 2);
    });

    QUnit.test("quick create record fails in grouped by char", async (assert) => {
        assert.expect(7);

        serverData.views["partner,false,form"] = '<form><field name="foo"/></form>';

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            groupBy: ["foo"],
            arch: `
                <kanban on_create="quick_create">
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (args.method === "name_create") {
                    throw makeErrorFromResponse({
                        code: 200,
                        message: "Odoo Server Error",
                        data: {
                            name: "odoo.exceptions.UserError",
                            debug: "traceback",
                            arguments: ["This is a user error"],
                            context: {},
                        },
                    });
                }
                if (args.method === "create") {
                    assert.deepEqual(args.args[0], { foo: "blip" });
                    assert.deepEqual(args.kwargs.context, {
                        default_foo: "blip",
                        default_name: "test",
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    });
                }
            },
        });

        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 2);

        await quickCreateRecord();
        await editQuickCreateInput("display_name", "test");
        await validateRecord();

        assert.containsOnce(target, ".modal .o_form_view .o_form_editable");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=foo] input").value,
            "blip"
        );
        await click(target, ".modal .o_form_button_save");

        assert.containsNone(target, ".modal .o_form_view .o_form_editable");
        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 3);
    });

    QUnit.test("quick create record fails in grouped by selection", async (assert) => {
        assert.expect(7);

        serverData.views["partner,false,form"] = '<form><field name="state"/></form>';

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            groupBy: ["state"],
            arch: `
                <kanban on_create="quick_create">
                    <templates><t t-name="kanban-box">
                        <div><field name="state"/></div>
                    </t></templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (args.method === "name_create") {
                    throw makeErrorFromResponse({
                        code: 200,
                        message: "Odoo Server Error",
                        data: {
                            name: "odoo.exceptions.UserError",
                            debug: "traceback",
                            arguments: ["This is a user error"],
                            context: {},
                        },
                    });
                }
                if (args.method === "create") {
                    assert.deepEqual(args.args[0], { state: "abc" });
                    assert.deepEqual(args.kwargs.context, {
                        default_state: "abc",
                        default_name: "test",
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    });
                }
            },
        });

        assert.containsOnce(target.querySelector(".o_kanban_group"), ".o_kanban_record");

        await quickCreateRecord();
        await editQuickCreateInput("display_name", "test");
        await validateRecord();

        assert.containsOnce(target, ".modal .o_form_view .o_form_editable");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=state] select").value,
            '"abc"'
        );

        await click(target, ".modal .o_form_button_save");

        assert.containsNone(target, ".modal .o_form_view .o_form_editable");
        assert.containsN(target.querySelector(".o_kanban_group"), ".o_kanban_record", 2);
    });

    QUnit.test("quick create record in empty grouped kanban", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, { method }) {
                if (method === "web_read_group") {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    return {
                        groups: [
                            { __domain: [["product_id", "=", 3]], product_id_count: 0 },
                            { __domain: [["product_id", "=", 5]], product_id_count: 0 },
                        ],
                        length: 2,
                    };
                }
            },
        });

        assert.containsN(target, ".o_kanban_group", 2, "there should be 2 columns");
        assert.containsNone(target, ".o_kanban_record", "both columns should be empty");

        await createRecord();

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_quick_create",
            "should have opened the quick create in the first column"
        );
    });

    QUnit.test("quick create record in grouped on date(time) field", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="display_name"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["date"],
            createRecord: () => {
                assert.step("createRecord");
            },
        });

        assert.containsNone(
            target,
            ".o_kanban_header .o_kanban_quick_add i",
            "quick create should be disabled when grouped on a date field"
        );

        // clicking on CREATE in control panel should not open a quick create
        await createRecord();
        assert.containsNone(
            target,
            ".o_kanban_quick_create",
            "should not have opened the quick create widget"
        );

        await reload(kanban, { groupBy: ["datetime"] });

        assert.containsNone(
            target,
            ".o_kanban_header .o_kanban_quick_add i",
            "quick create should be disabled when grouped on a datetime field"
        );

        // clicking on CREATE in control panel should not open a quick create
        await createRecord();
        assert.containsNone(
            target,
            ".o_kanban_quick_create",
            "should not have opened the quick create widget"
        );

        assert.verifySteps(["createRecord", "createRecord"]);
    });

    QUnit.test(
        "quick create record if grouped on date(time) field with attribute allow_group_range_value: true",
        async (assert) => {
            serverData.models.partner.records[0].date = "2017-01-08";
            serverData.models.partner.records[1].date = "2017-01-09";
            serverData.models.partner.records[2].date = "2017-01-08";
            serverData.models.partner.records[3].date = "2017-01-10";
            serverData.models.partner.records[0].datetime = "2017-01-08 10:55:05";
            serverData.models.partner.records[1].datetime = "2017-01-09 11:31:10";
            serverData.models.partner.records[2].datetime = "2017-01-08 09:20:25";
            serverData.models.partner.records[3].datetime = "2017-01-10 08:05:51";
            serverData.views["partner,quick_form,form"] =
                "<form>" + '<field name="date"/>' + '<field name="datetime"/>' + "</form>";

            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="quick_form">' +
                    '<field name="date" allow_group_range_value="true"/>' +
                    '<field name="datetime" allow_group_range_value="true"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="display_name"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["date"],
            });

            assert.containsOnce(
                target,
                ".o_kanban_header .o_kanban_quick_add i",
                "quick create should be enabled when grouped on a non-readonly date field"
            );

            // clicking on CREATE in control panel should open a quick create
            await createRecord();
            assert.containsOnce(
                target,
                ".o_kanban_group:first-child .o_kanban_quick_create",
                "should have opened the quick create in the first column"
            );
            assert.strictEqual(
                target.querySelector(
                    ".o_kanban_group:first-child .o_kanban_quick_create .o_field_widget[name=date] .o_datepicker input"
                ).value,
                "01/31/2017"
            );

            await reload(kanban, { groupBy: ["datetime"] });

            assert.containsOnce(
                target,
                ".o_kanban_header .o_kanban_quick_add i",
                "quick create should be enabled when grouped on a non-readonly datetime field"
            );

            // clicking on CREATE in control panel should open a quick create
            await createRecord();

            assert.containsOnce(
                target,
                ".o_kanban_group:first-child .o_kanban_quick_create",
                "should have opened the quick create in the first column"
            );
            assert.strictEqual(
                target.querySelector(
                    ".o_kanban_group:first-child .o_kanban_quick_create .o_field_widget[name=datetime] .o_datepicker input"
                ).value,
                "01/31/2017 23:59:59"
            );
        }
    );

    QUnit.test(
        "quick create record feature is properly enabled/disabled at reload",
        async (assert) => {
            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create">' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="display_name"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["foo"],
            });

            assert.containsN(
                target,
                ".o_kanban_header .o_kanban_quick_add i",
                3,
                "quick create should be enabled when grouped on a char field"
            );

            await reload(kanban, { groupBy: ["date"] });

            assert.containsNone(
                target,
                ".o_kanban_header .o_kanban_quick_add i",
                "quick create should now be disabled (grouped on date field)"
            );

            await reload(kanban, { groupBy: ["bar"] });

            assert.containsN(
                target,
                ".o_kanban_header .o_kanban_quick_add i",
                2,
                "quick create should be enabled again (grouped on boolean field)"
            );
        }
    );

    QUnit.test("quick create record in grouped by char field", async (assert) => {
        assert.expect(4);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="display_name"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["foo"],
            async mockRPC(route, { method, kwargs }) {
                if (method === "name_create") {
                    assert.strictEqual(kwargs.context.default_foo, "blip");
                }
            },
        });

        assert.containsN(target, ".o_kanban_header .o_kanban_quick_add i", 3);
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);

        await quickCreateRecord();
        await editQuickCreateInput("display_name", "new record");
        await validateRecord();

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 3);
    });

    QUnit.test("quick create record in grouped by boolean field", async (assert) => {
        assert.expect(4);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="display_name"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
            async mockRPC(route, { method, kwargs }) {
                if (method === "name_create") {
                    assert.strictEqual(kwargs.context.default_bar, true);
                }
            },
        });

        assert.containsN(target, ".o_kanban_header .o_kanban_quick_add i", 2);
        assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 3);

        await quickCreateRecord(1);
        await editQuickCreateInput("display_name", "new record");
        await validateRecord();

        assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 4);
    });

    QUnit.test("quick create record in grouped on selection field", async (assert) => {
        assert.expect(4);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="display_name"/></div>' +
                "</t></templates>" +
                "</kanban>",
            async mockRPC(route, { method, kwargs }) {
                if (method === "name_create") {
                    assert.strictEqual(kwargs.context.default_state, "abc");
                }
            },
            groupBy: ["state"],
        });

        assert.containsN(
            target,
            ".o_kanban_header .o_kanban_quick_add i",
            3,
            "quick create should be enabled when grouped on a selection field"
        );
        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column (abc) should contain 1 record"
        );

        await quickCreateRecord();
        await editQuickCreateInput("display_name", "new record");
        await validateRecord();

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "first column (abc) should contain 2 records"
        );
    });

    QUnit.test(
        "quick create record in grouped by char field (within quick_create_view)",
        async (assert) => {
            assert.expect(6);

            serverData.views["partner,some_view_ref,form"] =
                "<form>" + '<field name="foo"/>' + "</form>";

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["foo"],
                async mockRPC(route, { method, args, kwargs }) {
                    if (method === "create") {
                        assert.deepEqual(args[0], { foo: "blip" });
                        assert.strictEqual(kwargs.context.default_foo, "blip");
                    }
                },
            });

            assert.containsN(target, ".o_kanban_header .o_kanban_quick_add i", 3);
            assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);

            await quickCreateRecord();
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create input").value,
                "blip",
                "should have set the correct foo value by default"
            );
            await validateRecord();

            assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 3);
        }
    );

    QUnit.test(
        "quick create record in grouped by boolean field (within quick_create_view)",
        async (assert) => {
            assert.expect(6);

            serverData.views["partner,some_view_ref,form"] =
                "<form>" + '<field name="bar"/>' + "</form>";

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="bar"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["bar"],
                async mockRPC(route, { method, args, kwargs }) {
                    if (method === "create") {
                        assert.deepEqual(args[0], { bar: true });
                        assert.strictEqual(kwargs.context.default_bar, true);
                    }
                },
            });

            assert.containsN(
                target,
                ".o_kanban_header .o_kanban_quick_add i",
                2,
                "quick create should be enabled when grouped on a boolean field"
            );
            assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 3);

            await quickCreateRecord(1);

            assert.ok(
                target.querySelector(".o_kanban_quick_create .o_field_boolean input").checked
            );

            await validateRecord();

            assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 4);
        }
    );

    QUnit.test(
        "quick create record in grouped by selection field (within quick_create_view)",
        async (assert) => {
            assert.expect(6);

            serverData.views["partner,some_view_ref,form"] = `<form><field name="state"/></form>`;

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="state"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["state"],
                async mockRPC(route, { method, args, kwargs }) {
                    if (method === "create") {
                        assert.deepEqual(args[0], { state: "abc" });
                        assert.strictEqual(kwargs.context.default_state, "abc");
                    }
                },
            });

            assert.containsN(
                target,
                ".o_kanban_header .o_kanban_quick_add i",
                3,
                "quick create should be enabled when grouped on a selection field"
            );
            assert.containsOnce(
                target,
                ".o_kanban_group:first-child .o_kanban_record",
                "first column (abc) should contain 1 record"
            );

            await quickCreateRecord();
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create select").value,
                '"abc"',
                "should have set the correct state value by default"
            );
            await validateRecord();

            assert.containsN(
                target,
                ".o_kanban_group:first-child .o_kanban_record",
                2,
                "first column (abc) should now contain 2 records"
            );
        }
    );

    QUnit.test("quick create record while adding a new column", async (assert) => {
        const prom = makeDeferred();
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, { method, model }) {
                if (method === "name_create" && model === "product") {
                    await prom;
                }
            },
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);

        // add a new column
        assert.containsOnce(target, ".o_column_quick_create");
        assert.isNotVisible(target.querySelector(".o_column_quick_create input"));

        await createColumn();

        assert.isVisible(target.querySelector(".o_column_quick_create input"));

        await editColumnName("new column");
        await validateColumn();

        assert.strictEqual(target.querySelector(".o_column_quick_create input").value, "");
        assert.containsN(target, ".o_kanban_group", 2);

        // click to add a new record
        await createRecord();

        // should wait for the column to be created (and view to be re-rendered
        // before opening the quick create
        assert.containsNone(target, ".o_kanban_quick_create");

        // unlock column creation
        prom.resolve();
        await nextTick();

        assert.containsN(target, ".o_kanban_group", 3);
        assert.containsOnce(target, ".o_kanban_quick_create");

        // quick create record in first column
        await editQuickCreateInput("display_name", "new record");
        await validateRecord();

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 3);
    });

    QUnit.test("close a column while quick creating a record", async (assert) => {
        serverData.views["partner,some_view_ref,form"] = '<form><field name="int_field"/></form>';

        let prom;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create" quick_create_view="some_view_ref">
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(_route, { method }) {
                if (prom && method === "get_views") {
                    assert.step(method);
                    await prom;
                }
            },
        });

        prom = makeDeferred();

        assert.verifySteps([]);
        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsNone(target, ".o_column_folded");

        // click to quick create a new record in the first column (this operation is delayed)
        await quickCreateRecord();

        assert.verifySteps(["get_views"]);
        assert.containsNone(target, ".o_form_view");

        // click to fold the first column
        const clickColumnAction = await toggleColumnActions(0);
        await clickColumnAction("Fold");

        assert.containsOnce(target, ".o_column_folded");

        prom.resolve();
        await nextTick();

        assert.verifySteps([]);
        assert.containsNone(target, ".o_form_view");
        assert.containsOnce(target, ".o_column_folded");

        await createRecord();

        assert.verifySteps([]); // "get_views" should have already be done
        assert.containsOnce(target, ".o_form_view");
        assert.containsNone(target, ".o_column_folded");
    });

    QUnit.test(
        "quick create record: open on a column while another column has already one",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create">' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["product_id"],
            });

            // Click on quick create in first column
            await quickCreateRecord();
            assert.containsOnce(target, ".o_kanban_quick_create");
            assert.containsOnce(
                target.querySelector(".o_kanban_group:first-child"),
                ".o_kanban_quick_create"
            );

            // Click on quick create in second column
            await quickCreateRecord(1);
            assert.containsOnce(target, ".o_kanban_quick_create");
            assert.containsOnce(
                target.querySelector(".o_kanban_group:nth-child(2)"),
                ".o_kanban_quick_create"
            );

            // Click on quick create in first column once again
            await quickCreateRecord();
            assert.containsOnce(target, ".o_kanban_quick_create");
            assert.containsOnce(
                target.querySelector(".o_kanban_group:first-child"),
                ".o_kanban_quick_create"
            );
        }
    );

    QUnit.test("many2many_tags in kanban views", async (assert) => {
        serverData.models.partner.records[0].category_ids = [6, 7];
        serverData.models.partner.records[1].category_ids = [7, 8];
        serverData.models.category.records.push({
            id: 8,
            name: "hello",
            color: 0,
        });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click">' +
                '<field name="category_ids" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                '<field name="foo"/>' +
                '<field name="state" widget="priority"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            async mockRPC(route) {
                assert.step(route);
            },
            selectRecord: (resId) => {
                assert.deepEqual(
                    resId,
                    1,
                    "should trigger an event to open the clicked record in a form view"
                );
            },
        });

        assert.containsN(
            getCard(0),
            ".o_field_many2many_tags .o_tag",
            2,
            "first record should contain 2 tags"
        );
        assert.containsOnce(getCard(0), ".o_tag.o_tag_color_2", "first tag should have color 2");
        assert.verifySteps(
            [
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_search_read",
                "/web/dataset/call_kw/category/read",
            ],
            "two RPC should have been done (one search read and one read for the m2m)"
        );

        // Checks that second records has only one tag as one should be hidden (color 0)
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(2) .o_tag",
            "there should be only one tag in second record"
        );

        // Write on the record using the priority widget to trigger a re-render in readonly
        await click(target, ".o_kanban_record:first-child .o_priority_star:first-child");

        assert.verifySteps(
            [
                "/web/dataset/call_kw/partner/write",
                "/web/dataset/call_kw/partner/read",
                "/web/dataset/call_kw/category/read",
            ],
            "five RPCs should have been done (previous 2, 1 write (triggers a re-render), same 2 at re-render"
        );
        assert.containsN(
            target,
            ".o_kanban_record:first-child .o_field_many2many_tags .o_tag",
            2,
            "first record should still contain only 2 tags"
        );

        // click on a tag (should trigger switch_view)
        await click(target, ".o_kanban_record:first-child .o_tag:first-child");
    });

    QUnit.test("Do not open record when clicking on `a` with `href`", async (assert) => {
        serverData.models.partner.records = [{ id: 1, foo: "yop" }];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                "<templates>" +
                '<t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click">' +
                '<field name="foo"/>' +
                "<div>" +
                '<a class="o_test_link" href="#">test link</a>' +
                "</div>" +
                "</div>" +
                "</t>" +
                "</templates>" +
                "</kanban>",
        });

        patchWithCleanup(kanban.env.services.action, {
            async switchView() {
                // when clicking on a record in kanban view,
                // it switches to form view.
                throw new Error("should not switch view");
            },
        });

        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.containsOnce(target, ".o_kanban_record a");

        const testLink = target.querySelector(".o_kanban_record a");
        assert.ok(testLink.href.length, "link inside kanban record should have non-empty href");

        // Prevent the browser default behaviour when clicking on anything.
        // This includes clicking on a `<a>` with `href`, so that it does not
        // change the URL in the address bar.
        // Note that we should not specify a click listener on 'a', otherwise
        // it may influence the kanban record global click handler to not open
        // the record.
        testLink.addEventListener("click", (ev) => {
            assert.notOk(
                ev.defaultPrevented,
                "should not prevented browser default behaviour beforehand"
            );
            assert.strictEqual(
                ev.target,
                testLink,
                "should have clicked on the test link in the kanban record"
            );
            ev.preventDefault();
        });

        await click(testLink);
    });

    QUnit.test("Open record when clicking on widget field", async function (assert) {
        assert.expect(2);

        serverData.views[
            "product,false,form"
        ] = `<form string="Product"><field name="display_name"/></form>`;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="salary" widget="monetary"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            selectRecord: (resId) => {
                assert.strictEqual(resId, 1, "should trigger an event to open the form view");
            },
        });

        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

        await click(target.querySelector(".oe_kanban_global_click .o_field_monetary[name=salary]"));
    });

    QUnit.test("o2m loaded in only one batch", async (assert) => {
        serverData.models.subtask = {
            fields: {
                name: { string: "Name", type: "char" },
            },
            records: [
                { id: 1, name: "subtask #1" },
                { id: 2, name: "subtask #2" },
            ],
        };
        serverData.models.partner.fields.subtask_ids = {
            string: "Subtasks",
            type: "one2many",
            relation: "subtask",
        };
        serverData.models.partner.records[0].subtask_ids = [1];
        serverData.models.partner.records[1].subtask_ids = [2];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="subtask_ids" widget="many2many_tags"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });

        await reload(kanban, { groupBy: ["product_id"] });
        assert.verifySteps([
            "get_views",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "read",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "read",
        ]);
    });

    QUnit.test("m2m loaded in only one batch", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="category_ids" widget="many2many_tags"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });

        await reload(kanban, { groupBy: ["product_id"] });
        assert.verifySteps([
            "get_views",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "read",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "read",
        ]);
    });

    QUnit.test("fetch reference in only one batch", async (assert) => {
        serverData.models.partner.records[0].ref_product = "product,3";
        serverData.models.partner.records[1].ref_product = "product,5";
        serverData.models.partner.fields.ref_product = {
            string: "Reference Field",
            type: "reference",
        };

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            groupBy: ["product_id"],
            arch: `
                <kanban>
                    <field name="product_id"/>
                    <templates><t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="ref_product"/>
                        </div>
                    </t></templates>
                </kanban>`,
            mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });

        await reload(kanban, { groupBy: ["product_id"] });
        assert.verifySteps([
            "get_views",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "name_get",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "name_get",
        ]);
    });

    QUnit.test("wait x2manys batch fetches to re-render", async (assert) => {
        let prom = Promise.resolve();
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="category_ids" widget="many2many_tags"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, { method }) {
                if (method === "read") {
                    await prom;
                }
            },
        });

        assert.containsN(target, ".o_tag", 2);
        assert.containsN(target, ".o_kanban_group", 2);

        prom = makeDeferred();
        reload(kanban, { groupBy: ["state"] });

        await nextTick();

        assert.containsN(target, ".o_tag", 2);
        assert.containsN(target, ".o_kanban_group", 2);

        prom.resolve();
        await nextTick();

        assert.containsN(target, ".o_kanban_group", 3);
        assert.containsN(target, ".o_tag", 2, "Should display 2 tags after update");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_tag").innerText,
            "gold",
            "First category should be 'gold'"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(3) .o_tag").innerText,
            "silver",
            "Second category should be 'silver'"
        );
    });

    QUnit.test("can drag and drop a record from one column to the next", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click"><field name="foo"/>' +
                '<t t-if="widget.editable"><span class="thisiseditable">edit</span></t>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route) {
                if (route === "/web/dataset/resequence") {
                    assert.step("resequence");
                }
            },
        });
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
        assert.containsN(target, ".thisiseditable", 4);

        assert.verifySteps([]);

        // first record of first column moved to the bottom of second column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);
        assert.containsN(target, ".thisiseditable", 4);

        assert.verifySteps(["resequence"]);
    });

    QUnit.test("drag and drop highlight on hover", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                <field name="product_id"/>
                <templates><t t-name="kanban-box">
                <div class="oe_kanban_global_click"><field name="foo"/>
                </div>
                </t></templates>
                </kanban>`,
            groupBy: ["product_id"],
        });
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);

        // first record of first column moved to the bottom of second column
        const drop = drag(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );
        assert.hasClass(target.querySelector(".o_kanban_group:nth-child(2)"), "o_kanban_hover");
        await drop();
        assert.containsNone(target, ".o_kanban_group:nth-child(2).o_kanban_hover");
    });

    QUnit.test("drag and drop outside of a column", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                <field name="product_id"/>
                <templates><t t-name="kanban-box">
                <div class="oe_kanban_global_click"><field name="foo"/>
                </div>
                </t></templates>
                </kanban>`,
            groupBy: ["product_id"],
        });
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);

        // first record of first column moved to the right of a column
        await dragAndDrop(".o_kanban_group:first-child .o_kanban_record", ".o_column_quick_create");
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
    });

    QUnit.test("drag and drop a record, grouped by selection", async (assert) => {
        assert.expect(7);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                "<templates>" +
                '<t t-name="kanban-box">' +
                '<div><field name="state"/></div>' +
                "</t>" +
                "</templates>" +
                "</kanban>",
            groupBy: ["state"],
            async mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    assert.step("resequence");
                    return true;
                }
                if (args.model === "partner" && args.method === "write") {
                    assert.deepEqual(args.args[1], { state: "abc" });
                }
            },
        });
        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");

        // first record of second column moved to the bottom of first column
        await dragAndDrop(
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            ".o_kanban_group:first-child"
        );

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsNone(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.verifySteps(["resequence"]);
    });

    QUnit.test("prevent drag and drop of record if grouped by readonly", async (assert) => {
        // Whether the kanban is grouped by state, foo or bar
        // the user must not be able to drag and drop from one group to another,
        // as state, foo or bar are made readonly one way or another.
        // However, product_id must be draggable: by default, in the models, it's readonly,
        // but a counter order is given in the view architecture: readonly="0".
        // state must not be draggable:
        // state is not readonly in the model. state is passed in the arch specifying readonly="1".
        // foo must not be draggable:
        // foo is readonly in the model fields. foo is passed in the arch but without specifying readonly.
        // bar must not be draggable:
        // bar is readonly in the model fields. bar is not passed in the arch.
        // product_id must be draggable:
        // product_id is readonly in the model fields. product_id is passed in the arch specifying readonly="0".
        serverData.models.partner.fields.foo.readonly = true;
        serverData.models.partner.fields.bar.readonly = true;
        serverData.models.partner.fields.product_id.readonly = true;
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                "<templates>" +
                '<t t-name="kanban-box"><div>' +
                '<field name="foo"/>' +
                '<field name="product_id" readonly="0" invisible="1"/>' +
                '<field name="state" readonly="1"/>' +
                "</div></t>" +
                "</templates>" +
                "</kanban>",
            groupBy: ["state"],
            async mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    return true;
                }
                if (
                    args.model === "partner" &&
                    args.method === "write" &&
                    !(args.args && args.args[1] && args.args[1].product_id)
                ) {
                    // In the test, nothing should be draggable except the test on product_id
                    throw new Error("should not be draggable");
                }
            },
        });

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 2);

        // first record of first column moved to the bottom of second column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        // should not be draggable
        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 2);

        await reload(kanban, { groupBy: ["foo"] });

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.containsOnce(target, ".o_kanban_group:nth-child(3) .o_kanban_record");

        // first record of first column moved to the bottom of second column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        // should not be draggable
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.containsOnce(target, ".o_kanban_group:nth-child(3) .o_kanban_record");

        assert.deepEqual(getCardTexts(0), ["blipDEF", "blipGHI"]);

        // second record of first column moved at first place
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record:last-of-type",
            ".o_kanban_group:first-child .o_kanban_record"
        );

        // should still be able to resequence
        assert.deepEqual(getCardTexts(0), ["blipGHI", "blipDEF"]);

        await reload(kanban, { groupBy: ["bar"] });

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 1);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 0);

        assert.deepEqual(getCardTexts(0), ["blipGHI"]);

        // first record of first column moved to the bottom of second column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        // should not be draggable
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 1);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 0);

        assert.deepEqual(getCardTexts(0), ["blipGHI"]);

        await reload(kanban, { groupBy: ["product_id"] });

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 0);

        assert.deepEqual(getCardTexts(0), ["yopABC", "gnapGHI"]);

        // first record of first column moved to the bottom of second column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        // should be draggable
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 1);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 0);

        assert.deepEqual(getCardTexts(0), ["gnapGHI"]);
    });

    QUnit.test("prevent drag and drop if grouped by date/datetime field", async (assert) => {
        serverData.models.partner.records[0].date = "2017-01-08";
        serverData.models.partner.records[1].date = "2017-01-09";
        serverData.models.partner.records[2].date = "2017-02-08";
        serverData.models.partner.records[3].date = "2017-02-10";
        serverData.models.partner.records[0].datetime = "2017-01-08 10:55:05";
        serverData.models.partner.records[1].datetime = "2017-01-09 11:31:10";
        serverData.models.partner.records[2].datetime = "2017-02-08 09:20:25";
        serverData.models.partner.records[3].datetime = "2017-02-10 08:05:51";

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="date"/>' +
                '<field name="datetime"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["date:month"],
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(
            target,
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            2,
            "1st column should contain 2 records of January month"
        );
        assert.containsN(
            target,
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            2,
            "2nd column should contain 2 records of February month"
        );

        // drag&drop a record in another column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        // should not drag&drop record
        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "Should remain same records in first column (2 records)"
        );
        assert.containsN(
            target,
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            2,
            "Should remain same records in 2nd column (2 record)"
        );

        await reload(kanban, { groupBy: ["datetime:month"] });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "1st column should contain 2 records of January month"
        );
        assert.containsN(
            target,
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            2,
            "2nd column should contain 2 records of February month"
        );

        // drag&drop a record in another column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        // should not drag&drop record
        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "Should remain same records in first column(2 records)"
        );
        assert.containsN(
            target,
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            2,
            "Should remain same records in 2nd column(2 record)"
        );
    });

    QUnit.test("prevent drag and drop if grouped by many2many field", async (assert) => {
        serverData.models.partner.records[0].category_ids = [6, 7];
        serverData.models.partner.records[3].category_ids = [7];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["category_ids"],
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.strictEqual(
            target.querySelector(".o_kanban_group:first-child .o_column_title").innerText,
            "gold",
            "first column should have correct title"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:last-child .o_column_title").innerText,
            "silver",
            "second column should have correct title"
        );
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 3);

        // drag&drop a record in another column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 3);

        // Sanity check: groupby a non m2m field and check dragdrop is working
        await reload(kanban, { groupBy: ["state"] });

        assert.containsN(target, ".o_kanban_group", 3);
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_group .o_column_title")].map(
                (el) => el.innerText
            ),
            ["ABC", "DEF", "GHI"],
            "columns should have correct title"
        );
        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should have 1 record"
        );
        assert.containsN(
            target,
            ".o_kanban_group:last-child .o_kanban_record",
            2,
            "last column should have 2 records"
        );

        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:last-child"
        );

        assert.containsNone(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "first column should not contain records"
        );
        assert.containsN(
            target,
            ".o_kanban_group:last-child .o_kanban_record",
            3,
            "last column should contain 3 records"
        );
    });

    QUnit.test(
        "drag and drop record if grouped by date/time field with attribute allow_group_range_value: true",
        async (assert) => {
            assert.expect(16);

            serverData.models.partner.records[0].date = "2017-01-08";
            serverData.models.partner.records[1].date = "2017-01-09";
            serverData.models.partner.records[2].date = "2017-02-08";
            serverData.models.partner.records[3].date = "2017-02-10";
            serverData.models.partner.records[0].datetime = "2017-01-08 10:55:05";
            serverData.models.partner.records[1].datetime = "2017-01-09 11:31:10";
            serverData.models.partner.records[2].datetime = "2017-02-08 09:20:25";
            serverData.models.partner.records[3].datetime = "2017-02-10 08:05:51";

            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<field name="date" allow_group_range_value="true"/>' +
                    '<field name="datetime" allow_group_range_value="true"/>' +
                    "<templates>" +
                    '<t t-name="kanban-box">' +
                    '<div><field name="display_name"/></div>' +
                    "</t>" +
                    "</templates>" +
                    "</kanban>",
                groupBy: ["date:month"],
                async mockRPC(route, { model, method, args }) {
                    if (route === "/web/dataset/resequence") {
                        assert.step("resequence");
                        return true;
                    }
                    if (model === "partner" && method === "write") {
                        if ("date" in args[1]) {
                            assert.deepEqual(args[1], { date: "2017-02-28" });
                        } else if ("datetime" in args[1]) {
                            assert.deepEqual(args[1], { datetime: "2017-02-28 22:59:59" });
                        }
                    }
                },
            });

            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsN(
                target,
                ".o_kanban_group:first-child .o_kanban_record",
                2,
                "1st column should contain 2 records of January month"
            );
            assert.containsN(
                target,
                ".o_kanban_group:nth-child(2) .o_kanban_record",
                2,
                "2nd column should contain 2 records of February month"
            );

            await dragAndDrop(
                ".o_kanban_group:first-child .o_kanban_record",
                ".o_kanban_group:nth-child(2)"
            );

            assert.containsOnce(
                target,
                ".o_kanban_group:first-child .o_kanban_record",
                "Should only have one record remaining"
            );
            assert.containsN(
                target,
                ".o_kanban_group:nth-child(2) .o_kanban_record",
                3,
                "Should now have 3 records"
            );
            assert.verifySteps(["resequence"]);

            await reload(kanban, { groupBy: ["datetime:month"] });

            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsN(
                target,
                ".o_kanban_group:first-child .o_kanban_record",
                2,
                "1st column should contain 2 records of January month"
            );
            assert.containsN(
                target,
                ".o_kanban_group:nth-child(2) .o_kanban_record",
                2,
                "2nd column should contain 2 records of February month"
            );

            await dragAndDrop(
                ".o_kanban_group:first-child .o_kanban_record",
                ".o_kanban_group:nth-child(2)"
            );

            assert.containsOnce(
                target,
                ".o_kanban_group:first-child .o_kanban_record",
                "Should only have one record remaining"
            );
            assert.containsN(
                target,
                ".o_kanban_group:nth-child(2) .o_kanban_record",
                3,
                "Should now have 3 records"
            );
            assert.verifySteps(["resequence"]);
        }
    );

    QUnit.test("Move record in grouped by date, progress bars and sum field", async (assert) => {
        serverData.models.partner.records[0].date = "2017-01-08";
        serverData.models.partner.records[1].date = "2017-01-09";
        serverData.models.partner.records[2].date = "2017-02-08";
        serverData.models.partner.records[3].date = "2017-02-10";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <field name="date" allow_group_range_value="true" />
                    <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field" />
                    <templates>
                        <div t-name="kanban-box">
                            <field name="id" />
                        </div>
                    </templates>
                </kanban>
            `,
            groupBy: ["date:month"],
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "1st column should contain 2 records of January month"
        );
        assert.containsN(
            target,
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            2,
            "2nd column should contain 2 records of February month"
        );

        assert.deepEqual(
            getProgressBars(0).map((pb) => pb.style.width),
            ["50%", "50%"]
        );
        assert.deepEqual(
            getProgressBars(1).map((pb) => pb.style.width),
            ["50%", "50%"]
        );
        assert.deepEqual(getCounters(), ["19", "13"]);

        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "Should only have one record remaining"
        );
        assert.containsN(
            target,
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            3,
            "Should now have 3 records"
        );

        assert.deepEqual(
            getProgressBars(0).map((pb) => pb.style.width),
            ["100%"]
        );
        assert.deepEqual(
            getProgressBars(1).map((pb) => pb.style.width),
            ["33.3333%", "33.3333%", "33.3333%"] // abridged to e-4
        );
        assert.deepEqual(getCounters(), ["9", "23"]);
    });

    QUnit.test(
        "completely prevent drag and drop if records_draggable set to false",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban records_draggable="false">' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["product_id"],
            });

            // testing initial state
            assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
            assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
            assert.deepEqual(getCardTexts(), ["yop", "gnap", "blip", "blip"]);
            assert.containsNone(target, ".o_record_draggable");

            // attempt to drag&drop a record in another column
            await dragAndDrop(
                ".o_kanban_group:first-child .o_kanban_record",
                ".o_kanban_group:nth-child(2)"
            );

            // should not drag&drop record
            assert.containsN(
                target,
                ".o_kanban_group:nth-child(2) .o_kanban_record",
                2,
                "First column should still contain 2 records"
            );
            assert.containsN(
                target,
                ".o_kanban_group:nth-child(2) .o_kanban_record",
                2,
                "Second column should still contain 2 records"
            );
            assert.deepEqual(
                getCardTexts(),
                ["yop", "gnap", "blip", "blip"],
                "Records should not have moved"
            );

            // attempt to drag&drop a record in the same column
            await dragAndDrop(
                ".o_kanban_group:first-child .o_kanban_record",
                ".o_kanban_group:first-child .o_kanban_record:last-of-type"
            );

            assert.deepEqual(
                getCardTexts(),
                ["yop", "gnap", "blip", "blip"],
                "Records should not have moved"
            );
        }
    );

    QUnit.test("prevent drag and drop of record if onchange fails", async (assert) => {
        serverData.models.partner.onchanges = {
            product_id() {},
        };

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                "<templates>" +
                '<t t-name="kanban-box"><div>' +
                '<field name="foo"/>' +
                '<field name="product_id"/>' +
                "</div></t>" +
                "</templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, { model, method }) {
                if (model === "partner" && method === "onchange") {
                    throw {};
                }
            },
        });

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);

        // drag&drop a record in another column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        // should not be dropped, card should reset back to first column
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
    });

    QUnit.test("kanban view with default_group_by", async (assert) => {
        assert.expect(7);

        serverData.models.partner.records[0].product_id = 1;
        serverData.models.product.records.push({ id: 1, display_name: "third product" });

        let readGroupCount = 0;
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban default_group_by="bar">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            async mockRPC(route, { kwargs }) {
                if (route === "/web/dataset/call_kw/partner/web_read_group") {
                    readGroupCount++;
                    switch (readGroupCount) {
                        case 1:
                            return assert.deepEqual(kwargs.groupby, ["bar"]);
                        case 2:
                            return assert.deepEqual(kwargs.groupby, ["product_id"]);
                        case 3:
                            return assert.deepEqual(kwargs.groupby, ["bar"]);
                    }
                }
            },
        });

        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
        assert.containsN(target, ".o_kanban_group", 2);

        // simulate an update coming from the searchview, with another groupby given
        await reload(kanban, { groupBy: ["product_id"] });
        assert.containsN(target, ".o_kanban_group", 3);

        // simulate an update coming from the searchview, removing the previously set groupby
        await reload(kanban, { groupBy: [] });
        assert.containsN(target, ".o_kanban_group", 2);
    });

    QUnit.test("kanban view not groupable", async (assert) => {
        patchWithCleanup(kanbanView, { searchMenuTypes: ["filter", "favorite"] });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban default_group_by="bar">
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>
            `,
            searchViewArch: `
                <search>
                    <filter string="Filter" name="filter" domain="[]"/>
                    <filter string="candle" name="itsName" context="{'group_by': 'foo'}"/>
                </search>
            `,
            async mockRPC(route, { method }) {
                if (method === "web_read_group") {
                    throw new Error("Should not do a read_group RPC");
                }
            },
            context: { search_default_itsName: 1 },
        });

        assert.doesNotHaveClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
        assert.containsNone(target, ".o_control_panel div.o_search_options div.o_group_by_menu");
        assert.deepEqual(getFacetTexts(target), []);

        // validate presence of the search arch info
        await toggleFilterMenu(target);
        assert.containsOnce(target, ".o_filter_menu .o_menu_item");
    });

    QUnit.test("kanban view with create=False", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban create="0">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
        });

        assert.containsNone(target, ".o-kanban-button-new");
    });

    QUnit.test("kanban view with create=False and groupby", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban create="0">
                    <templates>
                        <t t-name="kanban-box">>
                            <div><field name="foo"/></div>>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
        });

        assert.containsNone(target, ".o-kanban-button-new");
    });

    QUnit.test("clicking on a link triggers correct event", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban><templates><t t-name="kanban-box">' +
                '<div><a type="edit">Edit</a></div>' +
                "</t></templates></kanban>",
            selectRecord: (resId, { mode }) => {
                assert.equal(resId, 1);
                assert.equal(mode, "edit");
            },
        });
        await click(getCard(0), "a");
    });

    QUnit.test("environment is updated when (un)folding groups", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="id"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        assert.deepEqual(getCardTexts(), ["1", "3", "2", "4"]);

        // fold the second group and check that the res_ids it contains are no
        // longer in the environment
        const clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Fold");

        assert.deepEqual(getCardTexts(), ["1", "3"]);

        // re-open the second group and check that the res_ids it contains are
        // back in the environment
        await click(getColumn(1));

        assert.deepEqual(getCardTexts(), ["1", "3", "2", "4"]);
    });

    QUnit.test("create a column in grouped on m2o", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, { method }) {
                if (method === "name_create" || route === "/web/dataset/resequence") {
                    assert.step(method || route);
                }
            },
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsOnce(target, ".o_column_quick_create", "should have a quick create column");
        assert.containsNone(
            target,
            ".o_column_quick_create input",
            "the input should not be visible"
        );

        await createColumn();

        assert.containsOnce(target, ".o_column_quick_create input", "the input should be visible");

        // discard the column creation and click it again
        await triggerEvent(target, ".o_column_quick_create input", "keydown", {
            key: "Escape",
        });

        assert.containsNone(
            target,
            ".o_column_quick_create input",
            "the input should not be visible"
        );

        await createColumn();

        assert.containsOnce(target, ".o_column_quick_create input", "the input should be visible");

        await editColumnName("new value");
        await validateColumn();

        assert.containsN(target, ".o_kanban_group", 3);
        assert.containsOnce(
            getColumn(2),
            "span:contains(new value)",
            "the last column should be the newly created one"
        );
        assert.ok(getColumn(2).dataset.id, "the created column should have an associated id");
        assert.doesNotHaveClass(
            getColumn(2),
            "o_column_folded",
            "the created column should not be folded"
        );
        assert.verifySteps(["name_create", "/web/dataset/resequence"]);

        // fold and unfold the created column, and check that no RPCs are done (as there are no records)
        const clickColumnAction = await toggleColumnActions(2);
        await clickColumnAction("Fold");

        assert.hasClass(getColumn(2), "o_column_folded", "the created column should now be folded");

        await click(getColumn(2));

        assert.doesNotHaveClass(getColumn(1), "o_column_folded");
        assert.verifySteps([], "no rpc should have been done when folding/unfolding");

        // quick create a record
        await createRecord();

        assert.hasClass(
            getColumn(0).querySelector(":scope > div:nth-child(2)"),
            "o_kanban_quick_create",
            "clicking on create should open the quick_create in the first column"
        );
    });

    QUnit.test("auto fold group when reach the limit", async (assert) => {
        for (let i = 0; i < 12; i++) {
            serverData.models.product.records.push({
                id: 8 + i,
                name: "column",
            });
            serverData.models.partner.records.push({
                id: 20 + i,
                foo: "dumb entry",
                product_id: 8 + i,
            });
        }

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args, performRPC) {
                if (args.method === "web_read_group") {
                    const result = await performRPC(route, args);
                    result.groups[2].__fold = true;
                    result.groups[8].__fold = true;
                    return result;
                }
            },
        });

        // we look if column are folded/unfolded according to what is expected
        assert.doesNotHaveClass(getColumn(1), "o_column_folded");
        assert.doesNotHaveClass(getColumn(3), "o_column_folded");
        assert.doesNotHaveClass(getColumn(9), "o_column_folded");
        assert.hasClass(getColumn(2), "o_column_folded");
        assert.hasClass(getColumn(8), "o_column_folded");

        // we look if columns are actually folded after we reached the limit
        assert.hasClass(getColumn(12), "o_column_folded");
        assert.hasClass(getColumn(13), "o_column_folded");

        // we look if we have the right count of folded/unfolded column
        assert.containsN(target, ".o_kanban_group:not(.o_column_folded)", 10);
        assert.containsN(target, ".o_kanban_group.o_column_folded", 4);
    });

    QUnit.test(
        "hide and display help message (ESC) in kanban quick create [REQUIRE FOCUS]",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<field name="product_id"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["product_id"],
            });

            await createColumn();
            await nextTick(); // Wait for the autofocus to trigger after the update

            assert.containsOnce(target, ".o_discard_msg", "the ESC to discard message is visible");

            // click outside the column (to lose focus)
            await click(getColumn(0), ".o_kanban_header");

            assert.containsNone(
                target,
                ".o_discard_msg",
                "the ESC to discard message is no longer visible"
            );
        }
    );

    QUnit.test("delete a column in grouped on m2o", async (assert) => {
        assert.expect(38);

        let resequencedIDs = [];
        let dialogProps;

        patchDialog((_cls, props) => {
            assert.ok(true, "a confirm modal should be displayed");
            dialogProps = props;
        });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban class="o_kanban_test" on_create="quick_create">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            groupBy: ["product_id"],
            async mockRPC(route, { ids, method }) {
                if (route === "/web/dataset/resequence") {
                    resequencedIDs = ids;
                    assert.strictEqual(
                        ids.filter(isNaN).length,
                        0,
                        "column resequenced should be existing records with IDs"
                    );
                }
                if (method) {
                    assert.step(method);
                }
            },
        });

        // check the initial rendering
        assert.containsN(target, ".o_kanban_group", 2, "should have two columns");
        assert.strictEqual(
            getColumn(0).querySelector(".o_column_title").innerText,
            "hello",
            'first column should be [3, "hello"]'
        );
        assert.strictEqual(
            getColumn(1).querySelector(".o_column_title").innerText,
            "xmo",
            'second column should be [5, "xmo"]'
        );
        assert.containsN(
            getColumn(1),
            ".o_kanban_record",
            2,
            "second column should have two records"
        );

        // check available actions in kanban header's config dropdown
        await toggleColumnActions(0);
        assert.containsOnce(
            getColumn(0),
            ".o_kanban_toggle_fold",
            "should be able to fold the column"
        );
        assert.containsOnce(getColumn(0), ".o_column_edit", "should be able to edit the column");
        assert.containsOnce(
            getColumn(0),
            ".o_column_delete",
            "should be able to delete the column"
        );
        assert.containsNone(
            getColumn(0),
            ".o_column_archive_records",
            "should not be able to archive all the records"
        );
        assert.containsNone(
            getColumn(0),
            ".o_column_unarchive_records",
            "should not be able to restore all the records"
        );

        // delete second column (first cancel the confirm request, then confirm)
        let clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Delete");

        dialogProps.cancel();
        await nextTick();

        assert.strictEqual(
            getColumn(1).querySelector(".o_column_title").innerText,
            "xmo",
            'column [5, "xmo"] should still be there'
        );

        dialogProps.confirm();
        await nextTick();

        clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Delete");

        assert.strictEqual(
            getColumn(1).querySelector(".o_column_title").innerText,
            "hello",
            'last column should now be [3, "hello"]'
        );
        assert.containsN(target, ".o_kanban_group", 2, "should still have two columns");
        assert.strictEqual(
            getColumn(0).querySelector(".o_column_title").innerText,
            "None (2)",
            "first column should have no id (Undefined column)"
        );

        // check available actions on 'Undefined' column
        await click(getColumn(0));
        await toggleColumnActions(0);
        assert.containsOnce(
            getColumn(0),
            ".o_kanban_toggle_fold",
            "should be able to fold the column"
        );
        assert.containsNone(getColumn(0), ".o_column_edit", "should be able to edit the column");
        assert.containsNone(
            getColumn(0),
            ".o_column_delete",
            "should be able to delete the column"
        );
        assert.containsNone(
            getColumn(0),
            ".o_column_archive_records",
            "should not be able to archive all the records"
        );
        assert.containsNone(
            getColumn(0),
            ".o_column_unarchive_records",
            "should not be able to restore all the records"
        );
        assert.verifySteps([
            "get_views",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "unlink",
            "web_read_group",
            "web_search_read",
            "web_search_read",
        ]);
        assert.containsN(
            target,
            ".o_kanban_group",
            2,
            "the old groups should have been correctly deleted"
        );

        // test column drag and drop having an 'Undefined' column
        await dragAndDrop(
            ".o_kanban_group:first-child .o_column_title",
            ".o_kanban_group:nth-child(2)"
        );
        assert.deepEqual(
            resequencedIDs,
            [],
            "resequencing require at least 2 not Undefined columns"
        );
        await createColumn();
        await editColumnName("once third column");
        await validateColumn();

        assert.deepEqual(resequencedIDs, [3, 4], "creating a column should trigger a resequence");

        await dragAndDrop(
            ".o_kanban_group:first-child .o_column_title",
            ".o_kanban_group:nth-child(3)"
        );

        assert.deepEqual(
            resequencedIDs,
            [3, 4],
            "moving the Undefined column should not affect order of other columns"
        );

        await dragAndDrop(
            ".o_kanban_group:nth-child(2) .o_column_title",
            ".o_kanban_group:nth-child(3)"
        );

        assert.deepEqual(resequencedIDs, [4, 3], "moved column should be resequenced accordingly");
        assert.verifySteps(["name_create"]);
    });

    QUnit.test("create a column, delete it and create another one", async (assert) => {
        patchDialog((_cls, props) => props.confirm());

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        assert.containsN(target, ".o_kanban_group", 2);

        await createColumn();
        await editColumnName("new column 1");
        await validateColumn();

        assert.containsN(target, ".o_kanban_group", 3);

        const clickColumnAction = await toggleColumnActions(2);
        await clickColumnAction("Delete");

        assert.containsN(target, ".o_kanban_group", 2);

        await createColumn();
        await editColumnName("new column 2");
        await validateColumn();

        assert.containsN(target, ".o_kanban_group", 3);
        assert.strictEqual(
            getColumn(2).querySelector("span").innerText,
            "new column 2",
            "the last column should be the newly created one"
        );
    });

    QUnit.test("edit a column in grouped on m2o", async (assert) => {
        serverData.views["product,false,form"] =
            '<form string="Product"><field name="display_name"/></form>';

        let nbRPCs = 0;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC() {
                nbRPCs++;
            },
        });

        assert.strictEqual(
            getColumn(1).querySelector(".o_column_title").innerText,
            "xmo",
            'title of the column should be "xmo"'
        );

        // edit the title of column [5, 'xmo'] and close without saving
        let clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Edit");

        assert.containsOnce(
            target,
            ".modal .o_form_editable",
            "a form view should be open in a modal"
        );
        assert.strictEqual(
            target.querySelector(".modal .o_form_editable input").value,
            "xmo",
            'the name should be "xmo"'
        );

        await editInput(target, ".modal .o_form_editable input", "ged"); // change the value
        nbRPCs = 0;
        await click(target, ".modal-header .btn-close");

        assert.containsNone(target, ".modal");
        assert.strictEqual(
            getColumn(1).querySelector(".o_column_title").innerText,
            "xmo",
            'title of the column should still be "xmo"'
        );
        assert.strictEqual(nbRPCs, 0, "no RPC should have been done");

        // edit the title of column [5, 'xmo'] and discard
        clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Edit");
        await editInput(target, ".modal .o_form_editable input", "ged"); // change the value
        nbRPCs = 0;
        await click(target, ".modal button.o_form_button_cancel");

        assert.containsNone(target, ".modal");
        assert.strictEqual(
            getColumn(1).querySelector(".o_column_title").innerText,
            "xmo",
            'title of the column should still be "xmo"'
        );
        assert.strictEqual(nbRPCs, 0, "no RPC should have been done");

        // edit the title of column [5, 'xmo'] and save
        clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Edit");
        await editInput(target, ".modal .o_form_editable input", "ged"); // change the value
        nbRPCs = 0;
        await click(target, ".modal .o_form_button_save"); // click on save

        assert.containsNone(target, ".modal", "the modal should be closed");
        assert.strictEqual(
            getColumn(1).querySelector(".o_column_title").innerText,
            "ged",
            'title of the column should be "ged"'
        );
        assert.strictEqual(nbRPCs, 4, "should have done 1 write, 1 read_group and 2 search_read");
    });

    QUnit.test("edit a column propagates right context", async (assert) => {
        assert.expect(4);

        serverData.views["product,false,form"] =
            '<form string="Product"><field name="display_name"/></form>';

        patchWithCleanup(session.user_context, { lang: "brol" });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(_route, { method, model, kwargs }) {
                if (model === "partner" && method === "web_search_read") {
                    assert.strictEqual(
                        kwargs.context.lang,
                        "brol",
                        "lang is present in context for partner operations"
                    );
                } else if (model === "product") {
                    assert.strictEqual(
                        kwargs.context.lang,
                        "brol",
                        "lang is present in context for product operations"
                    );
                }
            },
        });

        const clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Edit");
    });

    QUnit.test("quick create column should be opened if there is no column", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            domain: [["foo", "=", "norecord"]],
        });

        assert.containsNone(target, ".o_kanban_group");
        assert.containsOnce(target, ".o_column_quick_create");
        assert.containsOnce(
            target,
            ".o_column_quick_create input",
            "the quick create should be opened"
        );
    });

    QUnit.test(
        "quick create column should not be closed on window click if there is no column",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                <kanban>
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
                groupBy: ["product_id"],
                domain: [["foo", "=", "norecord"]],
            });

            assert.containsNone(target, ".o_kanban_group");
            assert.containsOnce(target, ".o_column_quick_create");
            assert.containsOnce(
                target,
                ".o_column_quick_create input",
                "the quick create should be opened"
            );
            // click outside should not discard quick create column
            await click(target, ".o_kanban_example_background_container");
            assert.containsOnce(
                target,
                ".o_column_quick_create input",
                "the quick create should still be opened"
            );
        }
    );

    QUnit.test("quick create several columns in a row", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        assert.containsN(target, ".o_kanban_group", 2, "should have two columns");
        assert.containsOnce(
            target,
            ".o_column_quick_create",
            "should have a ColumnQuickCreate widget"
        );
        assert.containsOnce(
            target,
            ".o_column_quick_create .o_quick_create_folded:visible",
            "the ColumnQuickCreate should be folded"
        );
        assert.containsNone(
            target,
            ".o_column_quick_create .o_quick_create_unfolded:visible",
            "the ColumnQuickCreate should be folded"
        );

        // add a new column
        await createColumn();
        assert.containsNone(
            target,
            ".o_column_quick_create .o_quick_create_folded:visible",
            "the ColumnQuickCreate should be unfolded"
        );
        assert.containsOnce(
            target,
            ".o_column_quick_create .o_quick_create_unfolded:visible",
            "the ColumnQuickCreate should be unfolded"
        );
        await editColumnName("New Column 1");
        await validateColumn();
        assert.containsN(target, ".o_kanban_group", 3, "should now have three columns");

        // add another column
        assert.containsNone(
            target,
            ".o_column_quick_create .o_quick_create_folded:visible",
            "the ColumnQuickCreate should still be unfolded"
        );
        assert.containsOnce(
            target,
            ".o_column_quick_create .o_quick_create_unfolded:visible",
            "the ColumnQuickCreate should still be unfolded"
        );
        await editColumnName("New Column 2");
        await validateColumn();
        assert.containsN(target, ".o_kanban_group", 4);
    });

    QUnit.test("quick create column with enter", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        // add a new column
        await createColumn();
        await editColumnName("New Column 1");
        await triggerEvent(target, ".o_column_quick_create input", "keydown", {
            key: "Enter",
        });
        assert.containsN(target, ".o_kanban_group", 3, "should now have three columns");
    });

    QUnit.test("quick create column and examples", async (assert) => {
        serviceRegistry.add("dialog", dialogService, { force: true });
        registry.category("kanban_examples").add("test", {
            examples: [
                {
                    name: "A first example",
                    columns: ["Column 1", "Column 2", "Column 3"],
                    description: "A weak description.",
                },
                {
                    name: "A second example",
                    columns: ["Col 1", "Col 2"],
                    description: `A fantastic description.`,
                },
            ],
        });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban examples="test">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        assert.containsOnce(target, ".o_column_quick_create", "should have quick create available");

        // open the quick create
        await createColumn();

        assert.containsOnce(
            target,
            ".o_column_quick_create .o_kanban_examples:visible",
            "should have a link to see examples"
        );

        // click to see the examples
        await click(target, ".o_column_quick_create .o_kanban_examples");

        assert.containsOnce(
            target,
            ".modal .o_kanban_examples_dialog",
            "should have open the examples dialog"
        );
        assert.containsN(
            target,
            ".modal .o_notebook_headers li",
            2,
            "should have two examples (in the menu)"
        );
        assert.strictEqual(
            target.querySelector(".modal .o_notebook_headers").innerText,
            "A first example\nA second example",
            "example names should be correct"
        );
        assert.containsOnce(
            target,
            ".modal .o_notebook_content .tab-pane",
            "should have only rendered one page"
        );

        const firstPane = target.querySelector(".modal .o_notebook_content .tab-pane");
        assert.containsN(
            firstPane,
            ".o_kanban_examples_group",
            3,
            "there should be 3 stages in the first example"
        );
        assert.strictEqual(
            [...firstPane.querySelectorAll("h6")].map((e) => e.textContent).join(""),
            "Column 1Column 2Column 3",
            "column titles should be correct"
        );
        assert.strictEqual(
            firstPane.querySelector(".o_kanban_examples_description").innerHTML,
            "A weak description.",
            "An escaped description should be displayed"
        );

        await click(target.querySelector(".nav-item:nth-child(2) .nav-link"));
        const secondPane = target.querySelector(".o_notebook_content");
        assert.containsN(
            secondPane,
            ".o_kanban_examples_group",
            2,
            "there should be 2 stages in the second example"
        );
        assert.strictEqual(
            [...secondPane.querySelectorAll("h6")].map((e) => e.textContent).join(""),
            "Col 1Col 2",
            "column titles should be correct"
        );
        assert.strictEqual(
            secondPane.querySelector(".o_kanban_examples_description").innerHTML,
            "A fantastic description.",
            "A formatted description should be displayed."
        );
    });

    QUnit.test("quick create column's apply button's display text", async (assert) => {
        serviceRegistry.add("dialog", dialogService, { force: true });
        const applyExamplesText = "Use This For My Test";
        registry.category("kanban_examples").add("test", {
            applyExamplesText: applyExamplesText,
            examples: [
                {
                    name: "A first example",
                    columns: ["Column 1", "Column 2", "Column 3"],
                },
                {
                    name: "A second example",
                    columns: ["Col 1", "Col 2"],
                },
            ],
        });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban examples="test">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        // open the quick create
        await createColumn();

        // click to see the examples
        await click(target, ".o_column_quick_create .o_kanban_examples");

        const $primaryActionButton = $(".modal footer.modal-footer button.btn-primary");
        assert.strictEqual(
            $primaryActionButton.text(),
            applyExamplesText,
            "the primary button should display the value of applyExamplesText"
        );
    });

    QUnit.test(
        "quick create column and examples background with ghostColumns titles",
        async (assert) => {
            serverData.models.partner.records = [];
            registry.category("kanban_examples").add("test", {
                ghostColumns: ["Ghost 1", "Ghost 2", "Ghost 3", "Ghost 4"],
                examples: [
                    {
                        name: "A first example",
                        columns: ["Column 1", "Column 2", "Column 3"],
                    },
                    {
                        name: "A second example",
                        columns: ["Col 1", "Col 2"],
                    },
                ],
            });

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban examples="test">' +
                    '<field name="product_id"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["product_id"],
            });

            assert.containsOnce(
                target,
                ".o_kanban_example_background",
                "should have ExamplesBackground when no data"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".o_kanban_examples_group h6")].map(
                    (el) => el.innerText
                ),
                ["Ghost 1", "Ghost 2", "Ghost 3", "Ghost 4"],
                "ghost title should be correct"
            );
            assert.containsOnce(
                target,
                ".o_column_quick_create",
                "should have a ColumnQuickCreate widget"
            );
            assert.containsOnce(
                target,
                ".o_column_quick_create .o_kanban_examples:visible",
                "should not have a link to see examples as there is no examples registered"
            );
        }
    );

    QUnit.test(
        "quick create column and examples background without ghostColumns titles",
        async (assert) => {
            serverData.models.partner.records = [];

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<field name="product_id"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["product_id"],
            });

            assert.containsOnce(
                target,
                ".o_kanban_example_background",
                "should have ExamplesBackground when no data"
            );
            assert.deepEqual(
                [...target.querySelectorAll(".o_kanban_examples_group h6")].map(
                    (el) => el.innerText
                ),
                ["Column 1", "Column 2", "Column 3", "Column 4"],
                "ghost title should be correct"
            );
            assert.containsOnce(
                target,
                ".o_column_quick_create",
                "should have a ColumnQuickCreate widget"
            );
            assert.containsNone(
                target,
                ".o_column_quick_create .o_kanban_examples:visible",
                "should not have a link to see examples as there is no examples registered"
            );
        }
    );

    QUnit.test(
        "nocontent helper after adding a record (kanban with progressbar)",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `<kanban >
                    <field name="product_id"/>
                    <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                    <templates>
                      <t t-name="kanban-box">
                        <div><field name="foo"/></div>
                      </t>
                    </templates>
                </kanban>`,
                groupBy: ["product_id"],
                domain: [["foo", "=", "abcd"]],
                async mockRPC(route, args) {
                    if (args.method === "web_read_group") {
                        return {
                            groups: [
                                {
                                    __domain: [["product_id", "=", 3]],
                                    product_id_count: 0,
                                    product_id: [3, "hello"],
                                },
                            ],
                        };
                    }
                },
                noContentHelp: "No content helper",
            });

            assert.containsOnce(target, ".o_view_nocontent", "the nocontent helper is displayed");

            // add a record
            await quickCreateRecord();
            await editQuickCreateInput("display_name", "twilight sparkle");
            await validateRecord();

            assert.containsNone(
                target,
                ".o_view_nocontent",
                "the nocontent helper is not displayed after quick create"
            );

            // cancel quick create
            await discardRecord();
            assert.containsNone(
                target,
                ".o_view_nocontent",
                "the nocontent helper is not displayed after cancelling the quick create"
            );
        }
    );

    QUnit.test(
        "if view was not grouped at start, it can be grouped and ungrouped",
        async (assert) => {
            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create">' +
                    '<field name="product_id"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
            });

            assert.doesNotHaveClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
            await reload(kanban, { groupBy: ["product_id"] });

            assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");

            await reload(kanban, { groupBy: [] });

            assert.doesNotHaveClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
        }
    );

    QUnit.test("no content helper when archive all records in kanban group", async (assert) => {
        // add active field on partner model to have archive option
        serverData.models.partner.fields.active = {
            string: "Active",
            type: "boolean",
            default: true,
        };
        // remove last records to have only one column
        serverData.models.partner.records = serverData.models.partner.records.slice(0, 3);

        patchDialog((_cls, props) => {
            assert.step("open-dialog");
            props.confirm();
        });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `<kanban>
                        <field name="active"/>
                        <field name="bar"/>
                        <templates>
                            <t t-name="kanban-box">
                               <div><field name="foo"/></div>
                            </t>
                        </templates>
                    </kanban>`,
            noContentHelp: '<p class="hello">click to add a partner</p>',
            groupBy: ["bar"],
        });

        // check that the (unique) column contains 3 records
        assert.containsN(target, ".o_kanban_group:last-child .o_kanban_record", 3);

        // archive the records of the last column
        const clickColumnAction = await toggleColumnActions(0);
        await clickColumnAction("Archive All");

        // check no content helper is exist
        assert.containsOnce(target, ".o_view_nocontent");
        assert.verifySteps(["open-dialog"]);
    });

    QUnit.test("no content helper when no data", async (assert) => {
        const records = serverData.models.partner.records;

        serverData.models.partner.records = [];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban><templates><t t-name="kanban-box">' +
                "<div>" +
                '<t t-esc="record.foo.value"/>' +
                '<field name="foo"/>' +
                "</div>" +
                "</t></templates></kanban>",
            noContentHelp: '<p class="hello">click to add a partner</p>',
        });

        assert.containsOnce(target, ".o_view_nocontent", "should display the no content helper");

        assert.strictEqual(
            target.querySelector(".o_view_nocontent").innerText,
            '<p class="hello">click to add a partner</p>',
            "should have rendered no content helper from action"
        );

        serverData.models.partner.records = records;
        await reload(kanban);

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "should not display the no content helper"
        );
    });

    QUnit.test("no nocontent helper for grouped kanban with empty groups", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args, performRpc) {
                if (args.method === "web_read_group") {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    const result = await performRpc(...arguments);
                    for (const group of result.groups) {
                        group[args.kwargs.groupby[0] + "_count"] = 0;
                    }
                    return result;
                }
            },
            noContentHelp: "No content helper",
        });

        assert.containsN(target, ".o_kanban_group", 2, "there should be two columns");
        assert.containsNone(target, ".o_kanban_record", "there should be no records");
    });

    QUnit.test("no nocontent helper for grouped kanban with no records", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            noContentHelp: "No content helper",
        });

        assert.containsNone(target, ".o_kanban_group", "there should be no columns");
        assert.containsNone(target, ".o_kanban_record", "there should be no records");
        assert.containsNone(
            target,
            ".o_view_nocontent",
            "there should be no nocontent helper (we are in 'column creation mode')"
        );
        assert.containsOnce(
            target,
            ".o_column_quick_create",
            "there should be a column quick create"
        );
    });

    QUnit.test("no nocontent helper is shown when no longer creating column", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            noContentHelp: "No content helper",
        });

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "there should be no nocontent helper (we are in 'column creation mode')"
        );

        // creating a new column
        await editColumnName("applejack");
        await validateColumn();

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "there should be no nocontent helper (still in 'column creation mode')"
        );

        // leaving column creation mode
        await triggerEvent(target, ".o_column_quick_create .o_input", "keydown", {
            key: "Escape",
        });

        assert.containsOnce(target, ".o_view_nocontent", "there should be a nocontent helper");
    });

    QUnit.test("no nocontent helper is hidden when quick creating a column", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    return {
                        groups: [
                            {
                                __domain: [["product_id", "=", 3]],
                                product_id_count: 0,
                                product_id: [3, "hello"],
                            },
                        ],
                        length: 1,
                    };
                }
            },
            noContentHelp: "No content helper",
        });

        assert.containsOnce(target, ".o_view_nocontent", "there should be a nocontent helper");

        await createColumn();

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "there should be no nocontent helper (we are in 'column creation mode')"
        );
    });

    QUnit.test("remove nocontent helper after adding a record", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="name"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    return {
                        groups: [
                            {
                                __domain: [["product_id", "=", 3]],
                                product_id_count: 0,
                                product_id: [3, "hello"],
                            },
                        ],
                        length: 1,
                    };
                }
            },
            noContentHelp: "No content helper",
        });

        assert.containsOnce(target, ".o_view_nocontent", "there should be a nocontent helper");

        // add a record
        await quickCreateRecord();
        await editQuickCreateInput("display_name", "twilight sparkle");
        await validateRecord();

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "there should be no nocontent helper (there is now one record)"
        );
    });

    QUnit.test("remove nocontent helper when adding a record", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="name"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    return {
                        groups: [
                            {
                                __domain: [["product_id", "=", 3]],
                                product_id_count: 0,
                                product_id: [3, "hello"],
                            },
                        ],
                        length: 1,
                    };
                }
            },
            noContentHelp: "No content helper",
        });

        assert.containsOnce(target, ".o_view_nocontent", "there should be a nocontent helper");

        // add a record
        await quickCreateRecord();
        await editQuickCreateInput("display_name", "twilight sparkle");

        assert.containsNone(
            target,
            ".o_view_nocontent",
            "there should be no nocontent helper (there is now one record)"
        );
    });

    QUnit.test(
        "nocontent helper is displayed again after canceling quick create",
        async (assert) => {
            serverData.models.partner.records = [];

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="name"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["product_id"],
                async mockRPC(route, args) {
                    if (args.method === "web_read_group") {
                        return {
                            groups: [
                                {
                                    __domain: [["product_id", "=", 3]],
                                    product_id_count: 0,
                                    product_id: [3, "hello"],
                                },
                            ],
                            length: 1,
                        };
                    }
                },
                noContentHelp: "No content helper",
            });

            // add a record
            await quickCreateRecord();

            await click(target);

            assert.containsOnce(
                target,
                ".o_view_nocontent",
                "there should be again a nocontent helper"
            );
        }
    );

    QUnit.test(
        "nocontent helper for grouped kanban (on m2o field) with no records with no group_create",
        async (assert) => {
            serverData.models.partner.records = [];

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban group_create="false">' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["product_id"],
                noContentHelp: "No content helper",
            });

            assert.containsNone(target, ".o_kanban_group", "there should be no columns");
            assert.containsNone(target, ".o_kanban_record", "there should be no records");
            assert.containsNone(
                target,
                ".o_view_nocontent",
                "there should not be a nocontent helper"
            );
            assert.containsNone(
                target,
                ".o_column_quick_create",
                "there should not be a column quick create"
            );
        }
    );

    QUnit.test(
        "nocontent helper for grouped kanban (on date field) with no records with no group_create",
        async (assert) => {
            serverData.models.partner.records = [];

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                    <kanban group_create="false">
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="foo"/></div>
                            </t>
                        </templates>
                    </kanban>`,
                groupBy: ["date"],
                noContentHelp: "No content helper",
            });

            assert.containsNone(target, ".o_kanban_group");
            assert.containsNone(target, ".o_kanban_record");
            assert.containsOnce(target, ".o_view_nocontent");
            assert.containsNone(target, ".o_column_quick_create");
            assert.containsNone(target, ".o_kanban_example_background");
        }
    );

    QUnit.test("empty grouped kanban with sample data and no columns", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            serverData,
            groupBy: ["product_id"],
            resModel: "partner",
            type: "kanban",
            noContentHelp: "No content helper",
        });

        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(target, ".o_quick_create_unfolded");
        assert.containsOnce(target, ".o_kanban_example_background_container");
    });

    QUnit.test("empty grouped kanban with sample data and click quick create", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(route, { kwargs, method }, performRpc) {
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    result.groups.forEach((group) => {
                        group[`${kwargs.groupby[0]}_count`] = 0;
                    });
                }
                return result;
            },
            noContentHelp: "No content helper",
        });

        assert.containsN(target, ".o_kanban_group", 2, "there should be two columns");
        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent");
        assert.containsN(
            target,
            ".o_kanban_record",
            16,
            "there should be 8 sample records by column"
        );

        await quickCreateRecord();
        assert.doesNotHaveClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsNone(target, ".o_kanban_record");
        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(
            target.querySelector(".o_kanban_group:first-child"),
            ".o_kanban_quick_create"
        );

        await editQuickCreateInput("display_name", "twilight sparkle");
        await validateRecord();

        assert.doesNotHaveClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsOnce(
            target.querySelector(".o_kanban_group:first-child"),
            ".o_kanban_record"
        );
        assert.containsNone(target, ".o_view_nocontent");
    });

    QUnit.test("empty grouped kanban with sample data and cancel quick create", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(route, { kwargs, method }, performRpc) {
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    result.groups.forEach((group) => {
                        group[`${kwargs.groupby[0]}_count`] = 0;
                    });
                }
                return result;
            },
            noContentHelp: "No content helper",
        });
        assert.containsN(target, ".o_kanban_group", 2, "there should be two columns");
        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent");
        assert.containsN(
            target,
            ".o_kanban_record",
            16,
            "there should be 8 sample records by column"
        );

        await quickCreateRecord();
        assert.doesNotHaveClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsNone(target, ".o_kanban_record");
        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(
            target.querySelector(".o_kanban_group:first-child"),
            ".o_kanban_quick_create"
        );

        await click(target.querySelector(".o_kanban_view"));
        assert.doesNotHaveClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsNone(target, ".o_kanban_quick_create");
        assert.containsNone(target, ".o_kanban_record");
        assert.containsOnce(target, ".o_view_nocontent");
    });

    QUnit.test("empty grouped kanban with sample data: keyboard navigation", async (assert) => {
        await makeView({
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                            <field name="state" widget="priority"/>
                        </div>
                    </templates>
                </kanban>`,
            serverData,
            groupBy: ["product_id"],
            resModel: "partner",
            type: "kanban",
            async mockRPC(route, { kwargs, method }, performRpc) {
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    result.groups.forEach((g) => (g.product_id_count = 0));
                }
                return result;
            },
        });

        // Check keynav is disabled
        assert.hasClass(getCard(0), "o_sample_data_disabled");

        await toggleColumnActions(0);

        assert.hasClass(target.querySelector(".o_kanban_toggle_fold"), "o_sample_data_disabled");
        assert.containsNone(target, '[tabindex]:not([tabindex="-1"])');

        assert.hasClass(document.activeElement, "o_searchview_input");

        await triggerEvent(document.activeElement, null, "keydown", { key: "ArrowDown" });

        assert.hasClass(document.activeElement, "o_searchview_input");
    });

    QUnit.test("empty kanban with sample data", async (assert) => {
        serverData.models.partner.records = [];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            noContentHelp: "No content helper",
        });

        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsN(
            target,
            ".o_kanban_record:not(.o_kanban_ghost)",
            10,
            "there should be 10 sample records"
        );
        assert.containsOnce(target, ".o_view_nocontent");

        await reload(kanban, { domain: [["id", "<", 0]] });

        assert.doesNotHaveClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsNone(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.containsOnce(target, ".o_view_nocontent");
    });

    QUnit.test("empty grouped kanban with sample data and many2many_tags", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field"/>
                                <field name="category_ids" widget="many2many_tags"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(route, { kwargs, method }, performRpc) {
                assert.step(method || route);
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    result.groups.forEach((group) => {
                        group[`${kwargs.groupby[0]}_count`] = 0;
                    });
                }
                return result;
            },
        });

        assert.containsN(target, ".o_kanban_group", 2, "there should be 2 'real' columns");
        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.ok(
            target.querySelectorAll(".o_kanban_record").length >= 1,
            "there should be sample records"
        );
        assert.ok(
            target.querySelectorAll(".o_field_many2many_tags .o_tag").length >= 1,
            "there should be tags"
        );

        assert.verifySteps(["get_views", "web_read_group"], "should not read the tags");
    });

    QUnit.test("sample data does not change after reload with sample data", async (assert) => {
        Object.assign(serverData, {
            views: {
                "partner,false,kanban": `
                    <kanban sample="1">
                        <field name="product_id"/>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="int_field"/></div>
                            </t>
                        </templates>
                    </kanban>`,
                "partner,false,search": "<search/>",
                // list-view so that there is a view switcher, unused
                "partner,false,list": '<tree><field name="foo"/></tree>',
            },
        });
        const webClient = await createWebClient({
            serverData,
            async mockRPC(route, { kwargs, method }, performRpc) {
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    result.groups.forEach((group) => {
                        group[`${kwargs.groupby[0]}_count`] = 0;
                    });
                }
                return result;
            },
        });
        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "kanban"],
                [false, "list"],
            ],
            context: {
                group_by: ["product_id"],
            },
        });

        const columns = target.querySelectorAll(".o_kanban_group");

        assert.ok(columns.length >= 1, "there should be at least 1 sample column");
        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsN(target, ".o_kanban_record", 16);

        const kanbanText = target.querySelector(".o_kanban_view").innerText;
        await click(target.querySelector(".o_control_panel .o_switch_view.o_kanban"));

        assert.strictEqual(
            kanbanText,
            target.querySelector(".o_kanban_view").innerText,
            "the content should be the same after reloading the view"
        );
    });

    QUnit.test("non empty kanban with sample data", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            noContentHelp: "No content helper",
        });

        assert.doesNotHaveClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);
        assert.containsNone(target, ".o_view_nocontent");

        await reload(kanban, { domain: [["id", "<", 0]] });
        assert.doesNotHaveClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsNone(target, ".o_kanban_record:not(.o_kanban_ghost)");
    });

    QUnit.test("empty grouped kanban with sample data: add a column", async (assert) => {
        await makeView({
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            serverData,
            groupBy: ["product_id"],
            resModel: "partner",
            type: "kanban",
            async mockRPC(route, { method }, performRpc) {
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    result.groups = serverData.models.product.records.map((r) => {
                        return {
                            product_id: [r.id, r.display_name],
                            product_id_count: 0,
                            __domain: [["product_id", "=", r.id]],
                        };
                    });
                    result.length = result.groups.length;
                }
                return result;
            },
        });

        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsN(target, ".o_kanban_group", 2);
        assert.ok(
            target.querySelectorAll(".o_kanban_record").length > 0,
            "should contain sample records"
        );

        await createColumn();
        await editColumnName("Yoohoo");
        await validateColumn();

        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsN(target, ".o_kanban_group", 3);
        assert.ok(
            target.querySelectorAll(".o_kanban_record").length > 0,
            "should contain sample records"
        );
    });

    QUnit.test("empty grouped kanban with sample data: cannot fold a column", async (assert) => {
        // folding a column in grouped kanban with sample data is disabled, for the sake of simplicity
        await makeView({
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            serverData,
            groupBy: ["product_id"],
            resModel: "partner",
            type: "kanban",
            async mockRPC(route, { kwargs, method }, performRpc) {
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    // override read_group to return a single, empty group
                    result.groups = result.groups.slice(0, 1);
                    result.groups[0][`${kwargs.groupby[0]}_count`] = 0;
                    result.length = 1;
                }
                return result;
            },
        });

        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_kanban_group");
        assert.ok(
            target.querySelectorAll(".o_kanban_record").length > 0,
            "should contain sample records"
        );

        await toggleColumnActions(0);

        assert.hasClass(
            target.querySelector(".o_kanban_config .o_kanban_toggle_fold"),
            "o_sample_data_disabled"
        );
        assert.hasClass(target.querySelector(".o_kanban_config .o_kanban_toggle_fold"), "disabled");
    });

    QUnit.skip("empty grouped kanban with sample data: fold/unfold a column", async (assert) => {
        // folding/unfolding of grouped kanban with sample data is currently disabled
        await makeView({
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            serverData,
            groupBy: ["product_id"],
            resModel: "partner",
            type: "kanban",
            async mockRPC(route, { kwargs, method }, performRpc) {
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    // override read_group to return a single, empty group
                    result.groups = result.groups.slice(0, 1);
                    result.groups[0][`${kwargs.groupby[0]}_count`] = 0;
                    result.length = 1;
                }
                return result;
            },
        });

        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_kanban_group");
        assert.ok(
            target.querySelectorAll(".o_kanban_record").length > 0,
            "should contain sample records"
        );

        // Fold the column
        const clickColumnAction = await toggleColumnActions(0);
        await clickColumnAction("Fold");

        assert.containsOnce(target, ".o_kanban_group");
        assert.hasClass(target.querySelector(".o_kanban_group"), "o_column_folded");

        // Unfold the column
        await click(target, ".o_kanban_group.o_column_folded");

        assert.containsOnce(target, ".o_kanban_group");
        assert.doesNotHaveClass(target.querySelector(".o_kanban_group"), "o_column_folded");
        assert.ok(
            target.querySelectorAll(".o_kanban_record").length > 0,
            "should contain sample records"
        );
    });

    QUnit.test("empty grouped kanban with sample data: delete a column", async (assert) => {
        serverData.models.partner.records = [];

        patchDialog((_cls, props) => props.confirm());

        let groups = [
            {
                product_id: [1, "New"],
                product_id_count: 0,
                __domain: [],
            },
        ];
        await makeView({
            arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            serverData,
            groupBy: ["product_id"],
            resModel: "partner",
            type: "kanban",
            async mockRPC(route, { method }, performRpc) {
                const result = await performRpc(...arguments);
                if (method === "web_read_group") {
                    // override read_group to return a single, empty group
                    return {
                        groups,
                        length: groups.length,
                    };
                }
                return result;
            },
        });

        assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_kanban_group");
        assert.ok(
            target.querySelectorAll(".o_kanban_record").length > 0,
            "should contain sample records"
        );

        // Delete the first column
        groups = [];
        const clickColumnAction = await toggleColumnActions(0);
        await clickColumnAction("Delete");

        assert.containsNone(target, ".o_kanban_group");
        assert.containsOnce(target, ".o_column_quick_create .o_quick_create_unfolded");
    });

    QUnit.test(
        "empty grouped kanban with sample data: add a column and delete it right away",
        async (assert) => {
            patchDialog((_cls, props) => props.confirm());

            await makeView({
                arch: `
                <kanban sample="1">
                    <field name="product_id"/>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
                serverData,
                groupBy: ["product_id"],
                resModel: "partner",
                type: "kanban",
                async mockRPC(route, { method }, performRpc) {
                    const result = await performRpc(...arguments);
                    if (method === "web_read_group") {
                        result.groups = serverData.models.product.records.map((r) => {
                            return {
                                product_id: [r.id, r.display_name],
                                product_id_count: 0,
                                __domain: [["product_id", "=", r.id]],
                            };
                        });
                        result.length = result.groups.length;
                    }
                    return result;
                },
            });

            assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
            assert.containsN(target, ".o_kanban_group", 2);
            assert.ok(
                target.querySelectorAll(".o_kanban_record").length > 0,
                "should contain sample records"
            );

            // add a new column
            await createColumn();
            await editColumnName("Yoohoo");
            await validateColumn();

            assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
            assert.containsN(target, ".o_kanban_group", 3);
            assert.ok(
                target.querySelectorAll(".o_kanban_record").length,
                "should contain sample records"
            );

            // delete the column we just created
            const clickColumnAction = await toggleColumnActions(2);
            await clickColumnAction("Delete");

            assert.hasClass(target.querySelector(".o_content"), "o_view_sample_data");
            assert.containsN(target, ".o_kanban_group", 2);
            assert.ok(
                target.querySelectorAll(".o_kanban_record").length,
                "should contain sample records"
            );
        }
    );

    QUnit.test("bounce create button when no data and click on empty area", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `<kanban><templates><t t-name="kanban-box">
                    <div>
                        <t t-esc="record.foo.value"/>
                        <field name="foo"/>
                    </div>
                </t></templates></kanban>`,
            noContentHelp: "click to add a partner",
        });

        await click(target, ".o_kanban_view");
        assert.doesNotHaveClass(target.querySelector(".o-kanban-button-new"), "o_catch_attention");

        await reload(kanban, { domain: [["id", "<", 0]] });

        await click(target, ".o_kanban_renderer");
        assert.hasClass(target.querySelector(".o-kanban-button-new"), "o_catch_attention");
    });

    QUnit.test("buttons with modifiers", async (assert) => {
        serverData.models.partner.records[1].bar = false; // so that test is more complete

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="foo"/>' +
                '<field name="bar"/>' +
                '<field name="state"/>' +
                '<templates><div t-name="kanban-box">' +
                '<button class="o_btn_test_1" type="object" name="a1" ' +
                "attrs=\"{'invisible': [['foo', '!=', 'yop']]}\"/>" +
                '<button class="o_btn_test_2" type="object" name="a2" ' +
                "attrs=\"{'invisible': [['bar', '=', True]]}\" " +
                'states="abc,def"/>' +
                "</div></templates>" +
                "</kanban>",
        });

        assert.containsOnce(target, ".o_btn_test_1", "kanban should have one buttons of type 1");
        assert.containsN(target, ".o_btn_test_2", 3, "kanban should have three buttons of type 2");
    });

    QUnit.test("support styling of anchor tags with action type", async function (assert) {
        assert.expect(3);

        const actionService = {
            start() {
                return {
                    doActionButton: (action) => assert.strictEqual(action.name, "42"),
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                            <a type="action" name="42" class="btn-primary" style="margin-left: 10px"><i class="fa fa-arrow-right"/> Click me !</a>
                        </div>
                    </templates>
                </kanban>`,
            resId: 1,
        });

        await click(target.querySelector("a[type='action']"));
        assert.hasClass(target.querySelector("a[type='action']"), "btn-primary");
        assert.strictEqual(target.querySelector("a[type='action']").style.marginLeft, "10px");
    });

    QUnit.test("button executes action and reloads", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                            <button type="object" name="a1" class="a1"/>
                        </div>
                    </templates>
                </kanban>
            `,
            async mockRPC(route) {
                assert.step(route);
            },
        });
        assert.verifySteps([
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/web_search_read",
        ]);

        assert.ok(
            target.querySelectorAll("button.a1").length,
            "kanban should have at least one button a1"
        );

        let count = 0;
        patchWithCleanup(kanban.env.services.action, {
            doActionButton({ onClose }) {
                count++;
                onClose();
            },
        });
        click(target.querySelector("button.a1"));
        await click(target.querySelector("button.a1"));

        assert.strictEqual(count, 1, "should have triggered an execute action only once");
        assert.verifySteps(
            ["/web/dataset/call_kw/partner/web_search_read"],
            "the records should be reloaded after executing a button action"
        );
    });

    QUnit.test("button executes action and check domain", async (assert) => {
        serverData.models.partner.fields.active = {
            string: "Active",
            type: "boolean",
            default: true,
        };
        for (const k in serverData.models.partner.records) {
            serverData.models.partner.records[k].active = true;
        }

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><div t-name="kanban-box">' +
                '<field name="foo"/>' +
                '<field name="active"/>' +
                '<button type="object" name="a1" />' +
                '<button type="object" name="toggle_active" class="toggle-active" />' +
                "</div></templates>" +
                "</kanban>",
        });
        patchWithCleanup(kanban.env.services.action, {
            doActionButton({ onClose }) {
                serverData.models.partner.records[0].active = false;
                onClose();
            },
        });

        assert.strictEqual(
            getCard(0).querySelector("span").textContent,
            "yop",
            "should display 'yop' record"
        );
        await click(getCard(0), "button.toggle-active");
        assert.notEqual(
            getCard(0).querySelector("span").textContent,
            "yop",
            "should remove 'yop' record from the view"
        );
    });

    QUnit.test("button executes action with domain field not in view", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            domain: [["bar", "=", true]],
            arch:
                "<kanban>" +
                '<templates><div t-name="kanban-box">' +
                '<field name="foo"/>' +
                '<button type="object" name="a1" />' +
                '<button type="object" name="toggle_action" />' +
                "</div></templates>" +
                "</kanban>",
        });
        patchWithCleanup(kanban.env.services.action, {
            doActionButton({ onClose }) {
                onClose();
            },
        });

        try {
            await click(target.querySelector('.o_kanban_record button[name="toggle_action"]'));
            assert.strictEqual(true, true, "Everything went fine");
        } catch {
            assert.strictEqual(true, false, "Error triggered at action execution");
        }
    });

    QUnit.test("field tag with modifiers but no widget", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo" attrs="{'invisible': [['id', '=', 1]]}"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.strictEqual(target.querySelector(".o_kanban_record").innerText, "");
        assert.strictEqual(target.querySelectorAll(".o_kanban_record")[1].innerText, "blip");
    });

    QUnit.test("field tag with widget and class attributes", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo" widget="char" class="hi"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.containsN(target, ".o_field_widget.hi", 4);
    });

    QUnit.test("rendering date and datetime (value)", async (assert) => {
        serverData.models.partner.records[0].date = "2017-01-25";
        serverData.models.partner.records[1].datetime = "2016-12-12 10:55:05";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="date"/>' +
                '<field name="datetime"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<span class="date" t-esc="record.date.value"/>' +
                '<span class="datetime" t-esc="record.datetime.value"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
        });

        assert.strictEqual(getCard(0).querySelector(".date").innerText, "01/25/2017");
        assert.strictEqual(getCard(1).querySelector(".datetime").innerText, "12/12/2016 11:55:05");
    });

    QUnit.test("rendering date and datetime (raw value)", async (assert) => {
        serverData.models.partner.records[0].date = "2017-01-25";
        serverData.models.partner.records[1].datetime = "2016-12-12 10:55:05";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="date"/>' +
                '<field name="datetime"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<span class="date" t-esc="record.date.raw_value"/>' +
                '<span class="datetime" t-esc="record.datetime.raw_value"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
        });

        assert.equal(getCard(0).querySelector(".date").innerText, "2017-01-25T00:00:00.000+01:00");
        assert.equal(
            getCard(1).querySelector(".datetime").innerText,
            "2016-12-12T11:55:05.000+01:00"
        );
    });

    QUnit.test("rendering many2one (value)", async (assert) => {
        serverData.models.partner.records[1].product_id = false;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<span class="product_id" t-esc="record.product_id.value"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
        });

        assert.deepEqual(getCardTexts(), ["hello", "hello", "xmo"]);
    });

    QUnit.test("rendering many2one (raw value)", async (assert) => {
        serverData.models.partner.records[1].product_id = false;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<span class="product_id" t-esc="record.product_id.raw_value"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
        });

        assert.deepEqual(getCardTexts(), ["3", "false", "3", "5"]);
    });

    QUnit.test("evaluate conditions on relational fields", async (assert) => {
        serverData.models.partner.records[0].product_id = false;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<field name="category_ids"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<button t-if="!record.product_id.raw_value" class="btn_a">A</button>' +
                '<button t-if="!record.category_ids.raw_value.length" class="btn_b">B</button>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
        });

        assert.containsN(
            target,
            ".o_kanban_record:not(.o_kanban_ghost)",
            4,
            "there should be 4 records"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:not(.o_kanban_ghost) .btn_a",
            "only 1 of them should have the 'Action' button"
        );
        assert.containsN(
            target,
            ".o_kanban_record:not(.o_kanban_ghost) .btn_b",
            2,
            "only 2 of them should have the 'Action' button"
        );
    });

    QUnit.test("resequence columns in grouped by m2o", async (assert) => {
        serverData.models.product.fields.sequence = { type: "integer" };

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="id"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.strictEqual(getColumn(0).querySelector(".o_column_title").innerText, "hello");
        assert.deepEqual(getCardTexts(), ["1", "3", "2", "4"]);

        await dragAndDrop(".o_kanban_group:first-child", ".o_kanban_group:nth-child(2)");

        // Drag & drop on column (not title) should not work
        assert.strictEqual(getColumn(0).querySelector(".o_column_title").innerText, "hello");
        assert.deepEqual(getCardTexts(), ["1", "3", "2", "4"]);

        await dragAndDrop(
            ".o_kanban_group:first-child .o_column_title",
            ".o_kanban_group:nth-child(2)"
        );

        assert.strictEqual(getColumn(0).querySelector(".o_column_title").innerText, "xmo");
        assert.deepEqual(getCardTexts(), ["2", "4", "1", "3"]);
    });

    QUnit.test("prevent resequence columns if groups_draggable=false", async (assert) => {
        serverData.models.product.fields.sequence = { type: "integer" };

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban groups_draggable='0'>
                    <field name="product_id"/>
                    <templates><t t-name="kanban-box">
                        <div><field name="id"/></div>
                    </t></templates>
                </kanban>`,
            groupBy: ["product_id"],
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.strictEqual(getColumn(0).querySelector(".o_column_title").innerText, "hello");
        assert.deepEqual(getCardTexts(), ["1", "3", "2", "4"]);

        await dragAndDrop(".o_kanban_group:first-child", ".o_kanban_group:nth-child(2)");

        // Drag & drop on column (not title) should not work
        assert.strictEqual(getColumn(0).querySelector(".o_column_title").innerText, "hello");
        assert.deepEqual(getCardTexts(), ["1", "3", "2", "4"]);

        await dragAndDrop(
            ".o_kanban_group:first-child .o_column_title",
            ".o_kanban_group:nth-child(2)"
        );

        assert.strictEqual(getColumn(0).querySelector(".o_column_title").innerText, "hello");
        assert.deepEqual(getCardTexts(), ["1", "3", "2", "4"]);
    });

    QUnit.test("properly evaluate more complex domains", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="foo"/>' +
                '<field name="bar"/>' +
                '<field name="category_ids"/>' +
                "<templates>" +
                '<t t-name="kanban-box">' +
                "<div>" +
                '<field name="foo"/>' +
                "<button type=\"object\" attrs=\"{'invisible':['|', ('bar','=',True), ('category_ids', '!=', [])]}\" class=\"btn btn-primary float-end\" name=\"arbitrary\">Join</button>" +
                "</div>" +
                "</t>" +
                "</templates>" +
                "</kanban>",
        });

        assert.containsOnce(
            target,
            "button.float-end.oe_kanban_action_button",
            "only one button should be visible"
        );
    });

    QUnit.test("edit the kanban color with the colorpicker", async (assert) => {
        serverData.models.category.records[0].color = 12;

        await makeView({
            type: "kanban",
            resModel: "category",
            serverData,
            arch:
                "<kanban>" +
                '<field name="color"/>' +
                "<templates>" +
                '<t t-name="kanban-box">' +
                '<div color="color">' +
                '<div class="o_dropdown_kanban dropdown">' +
                '<a class="dropdown-toggle o-no-caret btn" data-bs-toggle="dropdown" href="#">' +
                '<span class="fa fa-bars fa-lg"/>' +
                "</a>" +
                '<ul class="dropdown-menu" role="menu">' +
                "<li>" +
                '<ul class="oe_kanban_colorpicker"/>' +
                "</li>" +
                "</ul>" +
                "</div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t>" +
                "</templates>" +
                "</kanban>",
            async mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.step(`write-color-${args[1].color}`);
                }
            },
        });

        await toggleRecordDropdown(0);

        assert.containsNone(
            target,
            ".o_kanban_record.oe_kanban_color_12",
            "no record should have the color 12"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:first-child .oe_kanban_colorpicker",
            "there should be a color picker"
        );
        assert.containsN(
            target,
            ".o_kanban_record:first-child .oe_kanban_colorpicker > *",
            12,
            "the color picker should have 12 children (the colors)"
        );

        await click(target, ".oe_kanban_colorpicker a.oe_kanban_color_9");

        assert.verifySteps(["write-color-9"], "should write on the color field");
        assert.hasClass(getCard(0), "oe_kanban_color_9");
    });

    QUnit.test("load more records in column", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="id"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
            limit: 2,
            async mockRPC(_route, { method, kwargs }) {
                if (method === "web_search_read") {
                    assert.step(`${kwargs.limit} - ${kwargs.offset}`);
                }
            },
        });

        assert.containsN(
            getColumn(1),
            ".o_kanban_record",
            2,
            "there should be 2 records in the column"
        );
        assert.deepEqual(getCardTexts(1), ["1", "2"]);

        // load more
        await loadMore(1);

        assert.containsN(
            getColumn(1),
            ".o_kanban_record",
            3,
            "there should now be 3 records in the column"
        );
        assert.verifySteps(["2 - 0", "2 - 0", "2 - 2"], "the records should be correctly fetched");
        assert.deepEqual(getCardTexts(1), ["1", "2", "3"]);

        // reload
        await validateSearch(target);

        assert.containsN(
            getColumn(1),
            ".o_kanban_record",
            3,
            "there should still be 3 records in the column after reload"
        );
        assert.deepEqual(getCardTexts(1), ["1", "2", "3"]);
        assert.verifySteps(["2 - 0", "3 - 0"]);
    });

    QUnit.test("load more records in column with x2many", async (assert) => {
        assert.expect(10);

        serverData.models.partner.records[0].category_ids = [7];
        serverData.models.partner.records[1].category_ids = [];
        serverData.models.partner.records[2].category_ids = [6];
        serverData.models.partner.records[3].category_ids = [];
        // record [2] will be loaded after

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates><t t-name="kanban-box">
                        <div>
                            <field name="category_ids"/>
                            <field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>`,
            groupBy: ["bar"],
            limit: 2,
            async mockRPC(_route, { args, kwargs, model, method }) {
                if (model === "category" && method === "read") {
                    assert.step(String(args[0]));
                } else if (method === "web_search_read") {
                    const { limit, offset } = kwargs;
                    if (limit) {
                        assert.strictEqual(limit, 2);
                    }
                    if (offset) {
                        assert.strictEqual(offset, 2);
                    }
                }
            },
        });

        assert.containsN(getColumn(1), ".o_kanban_record", 2);

        assert.verifySteps(["7"], "only the appearing category should be fetched");

        // load more
        await loadMore(1);

        assert.containsN(getColumn(1), ".o_kanban_record", 3);
        assert.verifySteps(["6"], "the other categories should not be fetched");
    });

    QUnit.test("update buttons after column creation", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["product_id"],
        });

        assert.containsNone(target, ".o-kanban-button-new");

        await editColumnName("new column");
        await validateColumn();

        assert.containsOnce(target, ".o-kanban-button-new");
    });

    QUnit.test("group_by_tooltip option when grouping on a many2one", async (assert) => {
        assert.expect(14);
        delete serverData.models.partner.records[3].product_id;
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban default_group_by="bar">
                    <field name="bar"/>
                    <field name="product_id" options='{"group_by_tooltip": {"name": "Kikou"}}'/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/product/read") {
                    assert.strictEqual(args.args[0].length, 2, "read on two groups");
                    assert.deepEqual(
                        args.args[1],
                        ["display_name", "name"],
                        "should read on specified fields on the group by relation"
                    );
                }
            },
        });

        assert.hasClass(
            target.querySelector(".o_kanban_renderer"),
            "o_kanban_grouped",
            "should have classname 'o_kanban_grouped'"
        );
        assert.containsN(target, ".o_kanban_group", 2, "should have 2 columns");

        // simulate an update coming from the searchview, with another groupby given
        await reload(kanban, { groupBy: ["product_id"] });

        assert.containsN(target, ".o_kanban_group", 3, "should have 3 columns");
        assert.strictEqual(
            target.querySelectorAll(".o_kanban_group:nth-child(1) .o_kanban_record").length,
            1,
            "column should contain 1 record(s)"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_kanban_group:nth-child(2) .o_kanban_record").length,
            2,
            "column should contain 2 record(s)"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_kanban_group:nth-child(3) .o_kanban_record").length,
            1,
            "column should contain 1 record(s)"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:first-child span.o_column_title").textContent,
            "None",
            "first column should have a default title for when no value is provided"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_kanban_header_title").dataset
                .tooltipInfo,
            "tooltip of first column should not defined, since group_by_tooltip title and the many2one field has no value"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_kanban_header_title").dataset
                .tooltipTemplate,
            "tooltip of first column should not defined, since group_by_tooltip title and the many2one field has no value"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) span.o_column_title").textContent,
            "hello",
            "second column should have a title with a value from the many2one"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_header_title").dataset
                .tooltipInfo,
            `{"entries":[{"title":"Kikou","value":"hello"}]}`,
            "second column should have a tooltip with the group_by_tooltip title and many2one field value"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_header_title").dataset
                .tooltipTemplate,
            "web.KanbanGroupTooltip",
            "second column should have a tooltip with the group_by_tooltip title and many2one field value"
        );
    });

    QUnit.test("asynchronous tooltips when grouped", async (assert) => {
        assert.expect(10);
        serviceRegistry.add("tooltip", tooltipService);
        const prom = makeDeferred();
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban default_group_by="product_id">
                    <field name="bar"/>
                    <field name="product_id"  options='{"group_by_tooltip": {"name": "Name"}}'/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/product/read") {
                    await prom;
                }
            },
        });

        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
        assert.containsN(target, ".o_column_title", 2);
        assert.strictEqual(
            target
                .querySelectorAll(".o_kanban_header_title")[0]
                .getAttribute("data-tooltip-template"),
            null
        );
        assert.strictEqual(
            target.querySelectorAll(".o_kanban_header_title")[0].getAttribute("data-tooltip-info"),
            null
        );
        assert.strictEqual(
            target
                .querySelectorAll(".o_kanban_header_title")[1]
                .getAttribute("data-tooltip-template"),
            null
        );
        assert.strictEqual(
            target.querySelectorAll(".o_kanban_header_title")[1].getAttribute("data-tooltip-info"),
            null
        );
        prom.resolve();
        await nextTick();

        assert.strictEqual(
            target
                .querySelectorAll(".o_kanban_header_title")[0]
                .getAttribute("data-tooltip-template"),
            "web.KanbanGroupTooltip"
        );
        assert.strictEqual(
            target
                .querySelectorAll(".o_kanban_header_title")[1]
                .getAttribute("data-tooltip-template"),
            "web.KanbanGroupTooltip"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_kanban_header_title")[0].getAttribute("data-tooltip-info"),
            '{"entries":[{"title":"Name","value":"hello"}]}'
        );
        assert.strictEqual(
            target.querySelectorAll(".o_kanban_header_title")[1].getAttribute("data-tooltip-info"),
            '{"entries":[{"title":"Name","value":"xmo"}]}'
        );
    });

    QUnit.test("concurrency asynchronous tooltips when grouped", async (assert) => {
        assert.expect(2);
        serviceRegistry.add("tooltip", tooltipService);
        const prom = makeDeferred();
        let rpcCount = 0;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban default_group_by="product_id">
                    <field name="bar"/>
                    <field name="product_id"  options='{"group_by_tooltip": {"name": "Name"}}'/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            searchViewArch: `
            <search>
                <filter name="product_id" string="product" context="{'group_by': 'product_id', 'group_by_tooltip': {'name': 'Name'}}}"/>
            </search>
            `,
            async mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/product/read") {
                    if (rpcCount++ == 0) {
                        await prom;
                    } else {
                        return [
                            {
                                id: 3,
                                display_name: "hello",
                                name: "hello",
                            },
                            {
                                id: 5,
                                display_name: "xmo",
                                name: "xm",
                            },
                        ];
                    }
                }
            },
        });

        // The first tooltip rpc request is blocked and user changes the group by
        await click(target, ".o_group_by_menu > .dropdown-toggle");
        await click(target, ".o_group_by_menu > div > span");
        // The first tooltip request arrives after the second request
        prom.resolve();
        await nextTick();

        assert.strictEqual(
            target.querySelectorAll(".o_kanban_header_title")[0].getAttribute("data-tooltip-info"),
            '{"entries":[{"title":"Name","value":"hello"}]}'
        );
        assert.strictEqual(
            target.querySelectorAll(".o_kanban_header_title")[1].getAttribute("data-tooltip-info"),
            '{"entries":[{"title":"Name","value":"xm"}]}'
        );
    });

    QUnit.test("move a record then put it again in the same column", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="display_name"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["product_id"],
        });

        await editColumnName("column1");
        await validateColumn();

        await editColumnName("column2");
        await validateColumn();

        await quickCreateRecord(1);
        await editQuickCreateInput("display_name", "new partner");
        await validateRecord();

        assert.containsNone(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");

        await dragAndDrop(
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            ".o_kanban_group:first-child"
        );

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsNone(target, ".o_kanban_group:nth-child(2) .o_kanban_record");

        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        assert.containsNone(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
    });

    QUnit.test("resequence a record twice", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="display_name"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["product_id"],
            async mockRPC(route) {
                if (route === "/web/dataset/resequence") {
                    assert.step("resequence");
                }
            },
        });

        await editColumnName("column1");
        await validateColumn();

        await quickCreateRecord();
        await editQuickCreateInput("display_name", "record1");
        await validateRecord();

        await quickCreateRecord();
        await editQuickCreateInput("display_name", "record2");
        await validateRecord();
        await discardRecord(); // close quick create

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.deepEqual(
            getCardTexts(),
            ["record2", "record1"],
            "records should be correctly ordered"
        );

        await dragAndDrop(".o_kanban_record:nth-child(2)", ".o_kanban_record:nth-child(3)");

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.deepEqual(
            getCardTexts(),
            ["record1", "record2"],
            "records should be correctly ordered"
        );

        await dragAndDrop(".o_kanban_record:nth-child(3)", ".o_kanban_record:nth-child(2)");

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.deepEqual(
            getCardTexts(),
            ["record2", "record1"],
            "records should be correctly ordered"
        );
        assert.verifySteps(["resequence", "resequence"], "should have resequenced twice");
    });

    QUnit.test("basic support for widgets (being Owl Components)", async (assert) => {
        class MyComponent extends Component {
            get value() {
                return JSON.stringify(this.props.record.data);
            }
        }
        MyComponent.template = owl.xml`<div t-att-class="props.class" t-esc="value"/>`;
        viewWidgetRegistry.add("test", MyComponent);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
            <kanban>
                <field name="foo"/>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <t t-esc="record.foo.value"/>
                            <widget name="test"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        });

        assert.strictEqual(getCard(2).querySelector(".o_widget").innerText, '{"foo":"gnap"}');
    });

    QUnit.test("subwidgets with on_attach_callback when changing record color", async (assert) => {
        // Note: since the OWL refactor the 'on_attach_callback' is only called
        // once since the card is not entirely re-rendered. Instead we check that
        // the data displayed in the widget field is correctly updated.
        let counter = 0;
        legacyFieldRegistry.add(
            "test_widget",
            AbstractField.extend({
                on_attach_callback: () => counter++,
                _renderReadonly() {
                    this.el.innerText = this.record.data.color;
                },
            })
        );

        await makeView({
            type: "kanban",
            resModel: "category",
            serverData,
            arch:
                "<kanban>" +
                '<field name="color"/>' +
                "<templates>" +
                '<t t-name="kanban-box">' +
                '<div color="color">' +
                '<div class="o_dropdown_kanban dropdown">' +
                '<a class="dropdown-toggle o-no-caret btn" data-bs-toggle="dropdown" href="#">' +
                '<span class="fa fa-bars fa-lg"/>' +
                "</a>" +
                '<ul class="dropdown-menu" role="menu">' +
                "<li>" +
                '<ul class="oe_kanban_colorpicker"/>' +
                "</li>" +
                "</ul>" +
                "</div>" +
                '<field name="name" widget="test_widget"/>' +
                "</div>" +
                "</t>" +
                "</templates>" +
                "</kanban>",
        });

        // counter should be 2 as there are 2 records
        assert.strictEqual(counter, 2, "on_attach_callback should have been called twice");
        assert.deepEqual(getCardTexts(), ["2", "5"]);

        // set a color to kanban record
        await toggleRecordDropdown(0);
        await click(getCard(0), ".oe_kanban_colorpicker a.oe_kanban_color_9");

        // first record has replaced its $el with a new one
        assert.hasClass(getCard(0), "oe_kanban_color_9");
        assert.deepEqual(getCardTexts(), ["9", "5"]);
        assert.strictEqual(counter, 2, "on_attach_callback should have been called twice");
    });

    QUnit.test("column progressbars properly work", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<field name="int_field"/>' +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
        });

        assert.containsN(
            target,
            ".o_kanban_counter",
            serverData.models.product.records.length,
            "kanban counters should have been created"
        );

        assert.deepEqual(
            getCounters(),
            ["-4", "36"],
            "counter should display the sum of int_field values"
        );
    });

    QUnit.test('column progressbars: "false" bar is clickable', async (assert) => {
        serverData.models.partner.records.push({
            id: 5,
            bar: true,
            foo: false,
            product_id: 5,
            state: "ghi",
        });
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<field name="int_field"/>' +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.deepEqual(getCounters(), ["1", "4"]);
        assert.containsN(
            target,
            ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar",
            4
        );
        assert.containsOnce(
            target,
            ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-200",
            "should have false kanban color"
        );
        assert.hasClass(
            target.querySelector(
                ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-200"
            ),
            "bg-200"
        );

        await click(
            target,
            ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-200"
        );

        assert.hasClass(
            target.querySelector(
                ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-200"
            ),
            "progress-bar-animated"
        );
        assert.hasClass(
            target.querySelector(".o_kanban_group:last-child"),
            "o_kanban_group_show_200"
        );
        assert.deepEqual(getCounters(), ["1", "1"]);
    });

    QUnit.test('column progressbars: "false" bar with sum_field', async (assert) => {
        serverData.models.partner.records.push({
            id: 5,
            bar: true,
            foo: false,
            int_field: 15,
            product_id: 5,
            state: "ghi",
        });
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<field name="int_field"/>' +
                '<field name="foo"/>' +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.deepEqual(getCounters(), ["-4", "51"]);

        await click(
            target,
            ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-200"
        );

        assert.hasClass(
            target.querySelector(
                ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-200"
            ),
            "progress-bar-animated"
        );
        assert.deepEqual(getCounters(), ["-4", "15"]);
    });

    QUnit.test("column progressbars should not crash in non grouped views", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<field name="int_field"/>' +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            async mockRPC(route, { method }) {
                assert.step(method);
            },
        });

        assert.deepEqual(getCardTexts(), ["name", "name", "name", "name"]);
        assert.verifySteps(
            ["get_views", "web_search_read"],
            "no read on progress bar data is done"
        );
    });

    QUnit.test(
        "column progressbars: creating a new column should create a new progressbar",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<field name="product_id"/>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                    '<templates><t t-name="kanban-box">' +
                    "<div>" +
                    '<field name="name"/>' +
                    "</div>" +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["product_id"],
            });

            assert.containsN(target, ".o_kanban_counter", 2);

            // Create a new column: this should create an empty progressbar
            await createColumn();
            await editColumnName("test");
            await validateColumn();

            assert.containsN(
                target,
                ".o_kanban_counter",
                3,
                "a new column with a new column progressbar should have been created"
            );
        }
    );

    QUnit.test("column progressbars on quick create properly update counter", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
        });

        assert.deepEqual(getCounters(), ["1", "3"]);

        await quickCreateRecord();
        await editQuickCreateInput("display_name", "Test");

        assert.deepEqual(getCounters(), ["1", "3"]);

        await validateRecord();

        assert.deepEqual(
            getCounters(),
            ["2", "3"],
            "kanban counters should have updated on quick create"
        );
    });

    QUnit.test("column progressbars are working with load more", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            domain: [["bar", "=", true]],
            arch:
                '<kanban limit="1">' +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="id"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
        });

        assert.deepEqual(getCardTexts(0), ["1"]);

        await loadMore(0);
        await loadMore(0);

        assert.deepEqual(getCardTexts(0), ["1", "2", "3"], "intended records are loaded");
    });

    QUnit.test(
        "column progressbars with an active filter are working with load more",
        async (assert) => {
            serverData.models.partner.records.push(
                { id: 5, bar: true, foo: "blork" },
                { id: 6, bar: true, foo: "blork" },
                { id: 7, bar: true, foo: "blork" }
            );

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                domain: [["bar", "=", true]],
                arch: `<kanban limit="1">
                    <progressbar field="foo" colors='{"blork": "success"}'/>
                    <field name="foo"/>
                    <templates><t t-name="kanban-box">
                        <div><field name="id"/></div>
                    </t></templates>
                </kanban>`,
                groupBy: ["bar"],
            });

            await click(target, ".o_kanban_counter_progress .progress-bar.bg-success");

            assert.deepEqual(getCardTexts(), ["5"], "we should have 1 record shown");

            await loadMore(0);
            await loadMore(0);

            assert.deepEqual(getCardTexts(), ["5", "6", "7"]);
        }
    );

    QUnit.test("column progressbars on archiving records update counter", async (assert) => {
        // add active field on partner model and make all records active
        serverData.models.partner.fields.active = { string: "Active", type: "char", default: true };

        patchDialog((_cls, props) => props.confirm());

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="active"/>' +
                '<field name="bar"/>' +
                '<field name="int_field"/>' +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
        });

        assert.deepEqual(getCounters(), ["-4", "36"], "counter should contain the correct value");
        assert.deepEqual(
            getTooltips(1),
            ["1 yop", "1 gnap", "1 blip"],
            "the counter progressbars should be correctly displayed"
        );

        // archive all records of the second columns
        const clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Archive All");

        assert.deepEqual(getCounters(), ["-4", "0"], "counter should contain the correct value");
        assert.containsNone(
            getColumn(1),
            ".progress-bar",
            "the counter progressbars should have been correctly updated"
        );
    });

    QUnit.test(
        "kanban with progressbars: correctly update env when archiving records",
        async (assert) => {
            // add active field on partner model and make all records active
            serverData.models.partner.fields.active = {
                string: "Active",
                type: "char",
                default: true,
            };

            patchDialog((_cls, props) => props.confirm());

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<field name="active"/>' +
                    '<field name="bar"/>' +
                    '<field name="int_field"/>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                    '<templates><t t-name="kanban-box">' +
                    "<div>" +
                    '<field name="id"/>' +
                    "</div>" +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["bar"],
            });

            assert.deepEqual(getCardTexts(), ["4", "1", "2", "3"]);

            // archive all records of the first column
            const clickColumnAction = await toggleColumnActions(0);
            await clickColumnAction("Archive All");

            assert.deepEqual(getCardTexts(), ["1", "2", "3"]);
        }
    );

    QUnit.test("RPCs when (re)loading kanban view progressbars", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<field name="int_field"/>' +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
            async mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });

        await reload(kanban, { groupBy: ["bar"] });

        assert.verifySteps([
            // initial load
            "get_views",
            "web_read_group",
            "read_progress_bar",
            "web_search_read",
            "web_search_read",
            // reload
            "web_read_group",
            "read_progress_bar",
            "web_search_read",
            "web_search_read",
        ]);
    });

    QUnit.test("RPCs when (de)activating kanban view progressbar filters", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="bar"/>
                    <field name="int_field"/>
                    <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                    <templates><t t-name="kanban-box">
                        <div><field name="name"/></div>
                    </t></templates>
                </kanban>
            `,
            groupBy: ["bar"],
            async mockRPC(route, { method }) {
                assert.step(method || route);
            },
        });

        // Activate "yop" on second column
        await click(getColumn(1), ".progress-bar.bg-success");
        // Activate "gnap" on second column
        await click(getColumn(1), ".progress-bar.bg-warning");
        // Deactivate "gnap" on second column
        await click(getColumn(1), ".progress-bar.bg-warning");

        assert.verifySteps([
            // initial load
            "get_views",
            "web_read_group",
            "read_progress_bar",
            "web_search_read",
            "web_search_read",
            // activate filter
            "web_read_group", // recomputes aggregates
            "web_search_read",
            // activate another filter (switching)
            "web_read_group", // recomputes aggregates
            "web_search_read",
            // deactivate active filter
            "web_read_group", // recomputes aggregates
            "web_search_read",
        ]);
    });

    QUnit.test("drag & drop records grouped by m2o with progressbar", async (assert) => {
        serverData.models.partner.records[0].product_id = false;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="int_field"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
        });

        // Unfold first column
        await click(getColumn(0));

        assert.deepEqual(getCounters(), ["1", "1", "2"]);

        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        assert.deepEqual(getCounters(), ["0", "2", "2"]);

        await dragAndDrop(
            ".o_kanban_group:nth-child(2) .o_kanban_record",
            ".o_kanban_group:first-child"
        );

        assert.deepEqual(getCounters(), ["1", "1", "2"]);

        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:nth-child(3)"
        );

        assert.deepEqual(getCounters(), ["0", "1", "3"]);
    });

    QUnit.test("progress bar subgroup count recompute", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `<kanban>
                    <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                    <templates><t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>`,
            groupBy: ["bar"],
        });

        assert.deepEqual(getCounters(), ["1", "3"]);

        await click(target, ".o_kanban_group:nth-child(2) .bg-success");

        assert.deepEqual(getCounters(), ["1", "1"]);
    });

    QUnit.test(
        "progress bar recompute after drag&drop to and from other column",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `<kanban>
                    <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}'/>
                    <templates><t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>`,
                groupBy: ["bar"],
            });

            assert.deepEqual(getTooltips(), ["1 blip", "1 yop", "1 gnap", "1 blip"]);
            assert.deepEqual(getCounters(), ["1", "3"]);

            // Drag the last kanban record to the first column
            await dragAndDrop(
                ".o_kanban_group:last-child .o_kanban_record:nth-child(4)",
                ".o_kanban_group:first-child"
            );

            assert.deepEqual(getTooltips(), ["1 gnap", "1 blip", "1 yop", "1 blip"]);
            assert.deepEqual(getCounters(), ["2", "2"]);
        }
    );

    QUnit.test("load more should load correct records after drag&drop event", async (assert) => {
        // Add a sequence number and initialize
        serverData.models.partner.records.forEach((el, i) => (el.sequence = i));
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `<kanban limit="1">
                <field name="id"/>
                <field name="foo"/>
                <field name="sequence"/>
                <templates><t t-name="kanban-box">
                    <div>
                        <field name="id"/>
                    </div>
                </t></templates>
            </kanban>`,
            groupBy: ["bar"],
        });

        assert.deepEqual(getCardTexts(0), ["4"], "first column's first record must be id 4");
        assert.deepEqual(getCardTexts(1), ["1"], "second column's records should be only the id 1");

        // Drag the first kanban record on top of the last
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record",
            ".o_kanban_group:last-child .o_kanban_record"
        );

        // load more twice to load all records of second column
        await loadMore(1);
        await loadMore(1);

        // Check records of the second column
        assert.deepEqual(
            getCardTexts(1),
            ["4", "1", "2", "3"],
            "first column's first record must be id 4"
        );
    });

    QUnit.test(
        "column progressbars on quick create with quick_create_view are updated",
        async (assert) => {
            serverData.views[
                "partner,some_view_ref,form"
            ] = `<form><field name="int_field"/></form>`;

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<field name="int_field"/>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                    '<templates><t t-name="kanban-box">' +
                    "<div>" +
                    '<field name="name"/>' +
                    "</div>" +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["bar"],
            });

            assert.deepEqual(getCounters(), ["-4", "36"]);

            await createRecord();
            await editQuickCreateInput("int_field", 44);
            await validateRecord();

            assert.deepEqual(
                getCounters(),
                ["40", "36"],
                "kanban counters should have been updated on quick create"
            );
        }
    );

    QUnit.test(
        "column progressbars and active filter on quick create with quick_create_view are updated",
        async (assert) => {
            serverData.views["partner,some_view_ref,form"] = `
                <form>
                    <field name="int_field"/>
                    <field name="foo"/>
                </form>`;

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                    <kanban on_create="quick_create" quick_create_view="some_view_ref">
                        <field name="int_field"/>
                        <field name="foo"/>
                        <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                        <templates><t t-name="kanban-box">
                            <div><field name="name"/></div>
                        </t></templates>
                    </kanban>
                `,
                groupBy: ["bar"],
            });

            await click(getColumn(0), ".progress-bar.bg-danger");

            assert.containsOnce(getColumn(0), ".o_kanban_record");
            assert.containsOnce(getColumn(0), ".oe_kanban_card_danger");
            assert.deepEqual(getCounters(), ["-4", "36"]);

            // open the quick create
            await createRecord();

            // fill it with a record that satisfies the active filter
            await editQuickCreateInput("int_field", 44);
            await editQuickCreateInput("foo", "blip");
            await validateRecord();

            // fill it again with another record that DOES NOT satisfy the active filter
            await editQuickCreateInput("int_field", 1000);
            await editQuickCreateInput("foo", "yop");
            await validateRecord();

            assert.containsN(getColumn(0), ".o_kanban_record", 3);
            assert.containsN(getColumn(0), ".oe_kanban_card_danger", 2);
            assert.containsOnce(getColumn(0), ".oe_kanban_card_success");
            assert.deepEqual(
                getCounters(),
                ["40", "36"],
                "kanban counters should have been updated on quick create, respecting the active filter"
            );
        }
    );

    QUnit.test(
        "keep adding quickcreate in first column after a record from this column was moved",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban on_create="quick_create">' +
                    '<field name="int_field"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates>" +
                    "</kanban>",
                groupBy: ["foo"],
                async mockRPC(route, args) {
                    if (route === "/web/dataset/resequence") {
                        return true;
                    }
                },
            });
            await createRecord();
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create").closest(".o_kanban_group"),
                target.querySelector(".o_kanban_group"),
                "quick create should have been added in the first column"
            );
            await dragAndDrop(".o_kanban_record", ".o_kanban_group:nth-child(2)");
            await createRecord();
            assert.strictEqual(
                target.querySelector(".o_kanban_quick_create").closest(".o_kanban_group"),
                target.querySelector(".o_kanban_group"),
                "quick create should have been added in the first column"
            );
        }
    );

    QUnit.test("test displaying image (URL, image field not set)", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="id"/>' +
                '<templates><t t-name="kanban-box"><div>' +
                "<img t-att-src=\"kanban_image('partner', 'image', record.id.raw_value)\"/>" +
                "</div></t></templates>" +
                "</kanban>",
        });

        // since the field image is not set, kanban_image will generate an URL
        const imageOnRecord = target.querySelectorAll(
            'img[data-src*="/web/image"][data-src*="&id=1"]'
        );
        assert.strictEqual(imageOnRecord.length, 1, "partner with image display image by url");
    });

    QUnit.test("test displaying image (__last_update field)", async (assert) => {
        // the presence of __last_update field ensures that the image is reloaded when necessary
        assert.expect(2);

        const rec = serverData.models.partner.records.find((r) => r.id === 1);
        rec.__last_update = "2022-08-05 08:37:00";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="id"/>
                    <templates><t t-name="kanban-box"><div>
                        <img t-att-src="kanban_image('partner', 'image', record.id.raw_value)"/>
                    </div></t></templates>
                </kanban>`,
            mockRPC(route, { method, kwargs }) {
                if (method === "web_search_read") {
                    assert.deepEqual(kwargs.fields, ["id", "__last_update"]);
                }
            },
            domain: [["id", "in", [1]]],
        });

        assert.ok(
            target
                .querySelector(".o_kanban_record:not(.o_kanban_ghost) img")
                .dataset.src.endsWith(
                    "/web/image?model=partner&field=image&id=1&unique=1659688620000"
                ),
            "image src is the preview image given in option"
        );
    });

    QUnit.test("test displaying image (binary & placeholder)", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="id"/>' +
                '<field name="image"/>' +
                '<templates><t t-name="kanban-box"><div>' +
                "<img t-att-src=\"kanban_image('partner', 'image', record.id.raw_value)\"/>" +
                "</div></t></templates>" +
                "</kanban>",
        });
        const images = target.querySelectorAll("img");
        const placeholders = [];
        for (const [index, img] of images.entries()) {
            if (img.dataset.src.indexOf(serverData.models.partner.records[index].image) === -1) {
                // Then we display a placeholder
                placeholders.push(img);
            }
        }

        assert.strictEqual(
            placeholders.length,
            serverData.models.partner.records.length - 1,
            "partner with no image should display the placeholder"
        );
        assert.strictEqual(
            images[0].dataset.src,
            "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==",
            "The first partners non-placeholder image should be set"
        );
    });

    QUnit.test("test displaying image (for another record)", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="id"/>' +
                '<field name="image"/>' +
                '<templates><t t-name="kanban-box"><div>' +
                "<img t-att-src=\"kanban_image('partner', 'image', 1)\"/>" +
                "</div></t></templates>" +
                "</kanban>",
        });

        // the field image is set, but we request the image for a specific id
        // -> for the record matching the ID, the base64 should be returned
        // -> for all the other records, the image should be displayed by url
        const imageOnRecord = target.querySelectorAll(
            'img[data-src*="/web/image"][data-src*="&id=1"]'
        );
        assert.strictEqual(
            imageOnRecord.length,
            serverData.models.partner.records.length - 1,
            "display image by url when requested for another record"
        );
        assert.strictEqual(
            target.querySelector("img").dataset.src,
            "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==",
            "display image as value when requested for the record itself"
        );
    });

    QUnit.test("test displaying image from m2o field (m2o field not set)", async (assert) => {
        serverData.models.foo_partner = {
            fields: {
                name: { string: "Foo Name", type: "char" },
                partner_id: { string: "Partner", type: "many2one", relation: "partner" },
            },
            records: [
                { id: 1, name: "foo_with_partner_image", partner_id: 1 },
                { id: 2, name: "foo_no_partner" },
            ],
        };

        await makeView({
            type: "kanban",
            resModel: "foo_partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="name"/>
                            <field name="partner_id"/>
                            <img t-att-src="kanban_image('partner', 'image', record.partner_id.raw_value)"/>
                        </div>
                    </templates>
                </kanban>`,
        });
        assert.containsOnce(
            target,
            'img[data-src*="/web/image"][data-src$="&id=1&unique="]',
            "image url should contain id of set partner_id"
        );
        assert.containsOnce(
            target,
            'img[data-src*="/web/image"][data-src$="&id=&unique="]',
            "image url should contain an empty id if partner_id is not set"
        );
    });

    QUnit.test(
        "grouped kanban becomes ungrouped when clearing domain then clearing groupby",
        async (assert) => {
            // in this test, we simulate that clearing the domain is slow, so that
            // clearing the groupby does not corrupt the data handled while
            // reloading the kanban view.
            const prom = makeDeferred();

            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                domain: [["foo", "=", "norecord"]],
                groupBy: ["bar"],
                async mockRPC(route, args, performRpc) {
                    if (args.method === "web_read_group") {
                        const result = performRpc(route, args);
                        const isFirstUpdate =
                            args.kwargs.domain.length === 0 &&
                            args.kwargs.groupby &&
                            args.kwargs.groupby[0] === "bar";
                        if (isFirstUpdate) {
                            await prom;
                        }
                        return result;
                    }
                },
            });

            assert.hasClass(
                target.querySelector(".o_kanban_renderer"),
                "o_kanban_grouped",
                "the kanban view should be grouped"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o_kanban_renderer"),
                "o_kanban_ungrouped",
                "the kanban view should not be ungrouped"
            );

            reload(kanban, { domain: [] }); // 1st update on kanban view
            reload(kanban, { groupBy: [] }); // 2nd update on kanban view
            prom.resolve(); // simulate slow 1st update of kanban view

            await nextTick();
            assert.doesNotHaveClass(
                target.querySelector(".o_kanban_renderer"),
                "o_kanban_grouped",
                "the kanban view should not longer be grouped"
            );
            assert.hasClass(
                target.querySelector(".o_kanban_renderer"),
                "o_kanban_ungrouped",
                "the kanban view should have become ungrouped"
            );
        }
    );

    QUnit.test("quick_create on grouped kanban without column", async (assert) => {
        serverData.models.partner.records = [];

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            // force group_create to false, otherwise the CREATE button in control panel is hidden
            arch:
                '<kanban group_create="0" on_create="quick_create"><templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates></kanban>",
            groupBy: ["product_id"],
            createRecord: () => {
                assert.step("createRecord");
            },
        });

        await createRecord();
        assert.verifySteps(["createRecord"]);
    });

    QUnit.test("keyboard navigation on kanban basic rendering", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban><templates><t t-name="kanban-box">' +
                "<div>" +
                '<t t-esc="record.foo.value"/>' +
                '<field name="foo"/>' +
                "</div>" +
                "</t></templates></kanban>",
        });

        getCard(0).focus();
        assert.strictEqual(document.activeElement, getCard(0), "the kanban cards are focussable");

        triggerHotkey("ArrowRight");

        assert.strictEqual(
            document.activeElement,
            getCard(1),
            "the second card should be focussed"
        );

        triggerHotkey("ArrowLeft");

        assert.strictEqual(document.activeElement, getCard(0), "the first card should be focussed");
    });

    QUnit.test("keyboard navigation on kanban grouped rendering", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });
        const cardsByColumn = [...target.querySelectorAll(".o_kanban_group")].map((c) => [
            ...c.querySelectorAll(".o_kanban_record"),
        ]);
        const firstColumnFirstCard = cardsByColumn[0][0];
        const secondColumnFirstCard = cardsByColumn[1][0];
        const secondColumnSecondCard = cardsByColumn[1][1];

        firstColumnFirstCard.focus();

        // RIGHT should select the next column
        triggerHotkey("ArrowRight");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            secondColumnFirstCard,
            "RIGHT should select the first card of the next column"
        );

        // DOWN should move up one card
        triggerHotkey("ArrowDown");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            secondColumnSecondCard,
            "DOWN should select the second card of the current column"
        );

        // LEFT should go back to the first column
        triggerHotkey("ArrowLeft");
        await nextTick();
        assert.strictEqual(
            document.activeElement,
            firstColumnFirstCard,
            "LEFT should select the first card of the first column"
        );
    });

    QUnit.test(
        "keyboard navigation on kanban grouped rendering with empty columns",
        async (assert) => {
            serverData.models.partner.records[1].state = "abc";

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    "<kanban>" +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["state"],
                async mockRPC(route, args, performRpc) {
                    if (args.method === "web_read_group") {
                        // override read_group to return empty groups, as this is
                        // the case for several models (e.g. project.task grouped
                        // by stage_id)
                        const result = await performRpc(route, args);
                        // add 2 empty columns in the middle
                        result.groups.splice(1, 0, {
                            state_count: 0,
                            state: "md1",
                            __domain: [["state", "=", "md1"]],
                        });
                        result.groups.splice(1, 0, {
                            state_count: 0,
                            state: "md2",
                            __domain: [["state", "=", "md2"]],
                        });
                        // add 1 empty column in the beginning and the end
                        result.groups.unshift({
                            state_count: 0,
                            state: "beg",
                            __domain: [["state", "=", "beg"]],
                        });
                        result.groups.push({
                            state_count: 0,
                            state: "end",
                            __domain: [["state", "=", "end"]],
                        });
                        return result;
                    }
                },
            });

            /**
             * Added columns in mockRPC are empty
             *
             *    | BEG | ABC  | MD1 | MD2 | GHI  | END
             *    |-----|------|-----|-----|------|-----
             *    |     | yop  |     |     | gnap |
             *    |     | blip |     |     | blip |
             */
            const cardsByColumn = [...target.querySelectorAll(".o_kanban_group")].map((c) => [
                ...c.querySelectorAll(".o_kanban_record"),
            ]);
            const yop = cardsByColumn[1][0];
            const gnap = cardsByColumn[4][0];

            yop.focus();

            // RIGHT should select the next column that has a card
            triggerHotkey("ArrowRight");
            await nextTick();
            assert.strictEqual(
                document.activeElement,
                gnap,
                "RIGHT should select the first card of the next column that has a card"
            );

            // LEFT should go back to the first column that has a card
            triggerHotkey("ArrowLeft");
            await nextTick();
            assert.strictEqual(
                document.activeElement,
                yop,
                "LEFT should select the first card of the first column that has a card"
            );
        }
    );

    QUnit.test(
        "keyboard navigation on kanban when the focus is on a link that " +
            "has an action and the kanban has no oe_kanban_global_... class",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban><templates><t t-name="kanban-box">' +
                    '<div><a type="edit">Edit</a></div>' +
                    "</t></templates></kanban>",
                selectRecord: (resId) => {
                    assert.equal(
                        resId,
                        1,
                        "When selecting focusing a card and hitting ENTER, the first link or button is clicked"
                    );
                },
            });
            const firstCard = getCard(0);
            firstCard.focus();
            await triggerEvent(firstCard, null, "keydown", { key: "Enter" });
        }
    );

    QUnit.test("asynchronous rendering of a field widget (ungrouped)", async (assert) => {
        let fooFieldDef = makeDeferred();
        legacyFieldRegistry.add(
            "asyncwidget",
            AbstractField.extend({
                async willStart() {
                    await Promise.all([this._super(...arguments), fooFieldDef]);
                },
                async start() {
                    this.el.innerText = "LOADED";
                    return this._super(...arguments);
                },
            })
        );

        const makeViewProm = makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban><templates><t t-name="kanban-box">' +
                '<div><field name="foo" widget="asyncwidget"/></div>' +
                "</t></templates></kanban>",
        });
        await nextTick();

        assert.containsNone(target, ".o_kanban_record", "kanban view is not ready yet");

        fooFieldDef.resolve();
        const kanban = await makeViewProm;

        assert.deepEqual(getCardTexts(), ["LOADED", "LOADED", "LOADED", "LOADED"]);

        // reload with a domain
        fooFieldDef = makeDeferred();
        await reload(kanban, { domain: [["id", "=", 1]] });

        assert.deepEqual(getCardTexts(), ["LOADED", "LOADED", "LOADED", "LOADED"]);

        fooFieldDef.resolve();
        await nextTick();

        assert.deepEqual(getCardTexts(), ["LOADED"]);
    });

    QUnit.test("asynchronous rendering of a field widget (grouped)", async (assert) => {
        let fooFieldDef = makeDeferred();
        legacyFieldRegistry.add(
            "asyncwidget",
            AbstractField.extend({
                async willStart() {
                    await Promise.all([this._super(...arguments), fooFieldDef]);
                },
                async start() {
                    this.el.innerText = "LOADED";
                    return this._super(...arguments);
                },
            })
        );

        const makeViewProm = makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban><templates><t t-name="kanban-box">' +
                '<div><field name="foo" widget="asyncwidget"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["foo"],
        });
        await nextTick();

        assert.containsNone(target, ".o_kanban_record", "kanban view is not ready yet");

        fooFieldDef.resolve();
        const kanban = await makeViewProm;

        assert.deepEqual(getCardTexts(), ["LOADED", "LOADED", "LOADED", "LOADED"]);

        // reload with a domain
        fooFieldDef = makeDeferred();
        await reload(kanban, { domain: [["id", "=", 1]] });

        assert.deepEqual(getCardTexts(), ["LOADED", "LOADED", "LOADED", "LOADED"]);

        fooFieldDef.resolve();
        await nextTick();

        assert.deepEqual(getCardTexts(), ["LOADED"]);
    });

    QUnit.test("asynchronous rendering of a field widget with display attr", async (assert) => {
        const fooFieldDef = makeDeferred();
        const CharField = legacyFieldRegistry.get("char");
        legacyFieldRegistry.add(
            "asyncwidget",
            CharField.extend({
                async willStart() {
                    await Promise.all([this._super(...arguments), fooFieldDef]);
                },
                async start() {
                    this.el.innerText = "LOADED";
                },
            })
        );

        const makeViewProm = makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban><templates><t t-name="kanban-box">' +
                '<div><field name="foo" display="right" widget="asyncwidget"/></div>' +
                "</t></templates></kanban>",
        });
        await nextTick();

        assert.containsNone(target, ".o_kanban_record", "kanban view is not ready yet");

        fooFieldDef.resolve();
        await makeViewProm;

        assert.deepEqual(getCardTexts(), ["LOADED", "LOADED", "LOADED", "LOADED"]);
        assert.hasClass(getCard(0).querySelector(".o_field_asyncwidget"), "float-end");
    });

    QUnit.test("asynchronous rendering of a widget", async (assert) => {
        const widgetDef = makeDeferred();
        class AsyncWidget extends Component {
            setup() {
                onWillStart(async () => {
                    await widgetDef;
                });
            }
        }
        AsyncWidget.template = xml`<div>LOADED</div>`;
        viewWidgetRegistry.add("asyncwidget", AsyncWidget);

        const makeViewProm = makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban><templates><t t-name="kanban-box">' +
                '<div><widget name="asyncwidget"/></div>' +
                "</t></templates></kanban>",
        });
        await nextTick();

        assert.containsNone(target, ".o_kanban_record", "kanban view is not ready yet");

        widgetDef.resolve();
        await makeViewProm;

        assert.deepEqual(getCardTexts(), ["LOADED", "LOADED", "LOADED", "LOADED"]);
    });

    QUnit.test("update kanban with asynchronous field widget", async (assert) => {
        const fooFieldDef = makeDeferred();
        legacyFieldRegistry.add(
            "asyncwidget",
            AbstractField.extend({
                async willStart() {
                    await Promise.all([this._super(...arguments), fooFieldDef]);
                },
                async start() {
                    this.el.innerText = "LOADED";
                    return this._super(...arguments);
                },
            })
        );

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban><templates><t t-name="kanban-box">' +
                '<div><field name="foo" widget="asyncwidget"/></div>' +
                "</t></templates></kanban>",
            domain: [["id", "=", "0"]], // no record matches this domain
        });

        assert.containsNone(target, ".o_kanban_record:not(.o_kanban_ghost)");

        reload(kanban, { domain: [] }); // this rendering will be async

        assert.containsNone(target, ".o_kanban_record:not(.o_kanban_ghost)");

        fooFieldDef.resolve();
        await nextTick();

        assert.deepEqual(getCardTexts(), ["LOADED", "LOADED", "LOADED", "LOADED"]);
    });

    QUnit.test("set cover image", async (assert) => {
        assert.expect(10);

        serviceRegistry.add("dialog", dialogService, { force: true });
        serviceRegistry.add("http", {
            start: () => ({}),
        });
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                "<templates>" +
                '<t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click">' +
                '<field name="name"/>' +
                '<div class="o_dropdown_kanban dropdown">' +
                '<a class="dropdown-toggle o-no-caret btn" data-bs-toggle="dropdown" href="#">' +
                '<span class="fa fa-bars fa-lg"/>' +
                "</a>" +
                '<div class="dropdown-menu" role="menu">' +
                '<a type="set_cover" data-field="displayed_image_id" class="dropdown-item">Set Cover Image</a>' +
                "</div>" +
                "</div>" +
                "<div>" +
                '<field name="displayed_image_id" widget="attachment_image"/>' +
                "</div>" +
                "</div>" +
                "</t>" +
                "</templates>" +
                "</kanban>",
            async mockRPC(_route, { model, method, args }) {
                if (model === "partner" && method === "write") {
                    assert.step(String(args[0][0]));
                }
            },
        });

        patchWithCleanup(kanban.env.services.action, {
            switchView(_viewType, { mode, resModel, res_id, view_type }) {
                assert.deepEqual(
                    { mode, resModel, res_id, view_type },
                    {
                        mode: "readonly",
                        resModel: "partner",
                        res_id: 1,
                        view_type: "form",
                    },
                    "should trigger an event to open the clicked record in a form view"
                );
            },
        });

        await toggleRecordDropdown(0);
        await click(getCard(0), ".oe_kanban_action");

        assert.containsNone(getCard(0), "img", "Initially there is no image.");

        await click(document.body, ".modal .o_kanban_cover_image img", true);
        await click(document.body, ".modal .btn-primary:first-child");

        assert.containsOnce(target, 'img[data-src*="/web/image/1"]');

        await toggleRecordDropdown(1);
        const coverButton = getCard(1).querySelector("a");
        assert.strictEqual(coverButton.innerText.trim(), "Set Cover Image");
        await click(coverButton);

        assert.containsOnce(document.body, ".modal .o_kanban_cover_image");
        assert.containsOnce(document.body, ".modal .btn:contains(Select)");
        assert.containsOnce(document.body, ".modal .btn:contains(Discard)");

        await triggerEvent(
            document.body,
            ".modal .o_kanban_cover_image img",
            "dblclick",
            { bubbles: true },
            { skipVisibilityCheck: true }
        );

        assert.containsOnce(target, 'img[data-src*="/web/image/2"]');

        await click(target, ".o_kanban_record:first-child .o_attachment_image");

        assert.verifySteps(["1", "2"], "should writes on both kanban records");
    });

    QUnit.test("ungrouped kanban with handle field", async (assert) => {
        assert.expect(3);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<field name="int_field" widget="handle" />' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="foo"/>' +
                "</div>" +
                "</t></templates></kanban>",
            async mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    assert.deepEqual(
                        args.ids,
                        [2, 3, 4, 1],
                        "should write the sequence in correct order"
                    );
                }
            },
        });

        assert.deepEqual(getCardTexts(), ["yop", "blip", "gnap", "blip"]);

        await dragAndDrop(".o_kanban_record", ".o_kanban_record:nth-child(4)");

        assert.deepEqual(getCardTexts(), ["blip", "gnap", "blip", "yop"]);
    });

    QUnit.test("ungrouped kanban without handle field", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="foo"/>' +
                "</div>" +
                "</t></templates></kanban>",
            async mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    throw new Error("should not trigger a resequencing");
                }
            },
        });

        assert.deepEqual(getCardTexts(), ["yop", "blip", "gnap", "blip"]);

        await dragAndDrop(".o_kanban_record", ".o_kanban_record:nth-child(4)");

        assert.deepEqual(getCardTexts(), ["yop", "blip", "gnap", "blip"]);
    });

    QUnit.test("click on image field in kanban with oe_kanban_global_click", async (assert) => {
        assert.expect(2);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click">' +
                '<field name="image" widget="image"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            selectRecord(recordId) {
                assert.equal(
                    recordId,
                    1,
                    "should call its selectRecord prop with the clicked record"
                );
            },
        });

        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

        await click(target.querySelector(".o_field_image"), null, { skipVisibilityCheck: true });
    });

    QUnit.test("kanban view with boolean field", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="bar"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.containsN(target, ".o_kanban_record input:disabled", 4);
        assert.containsN(target, ".o_kanban_record input:checked", 3);
        assert.containsOnce(target, ".o_kanban_record input:not(:checked)");
    });

    QUnit.test("kanban view with boolean widget", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="bar" widget="boolean"/></div>
                        </t>
                    </templates>
                </kanban>
            `,
        });

        assert.containsOnce(getCard(0), "div.o_field_boolean .o-checkbox");
    });

    QUnit.test("kanban view with boolean toggle widget", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="bar" widget="boolean_toggle"/></div>
                        </t>
                    </templates>
                </kanban>
            `,
        });
        assert.ok(getCard(0).querySelector("[name='bar'] input").checked);
        assert.ok(getCard(1).querySelector("[name='bar'] input").checked);

        await click(getCard(1), "[name='bar'] input");
        assert.ok(getCard(0).querySelector("[name='bar'] input").checked);
        assert.notOk(getCard(1).querySelector("[name='bar'] input").checked);
    });

    QUnit.test("kanban view with monetary and currency fields without widget", async (assert) => {
        const currencies = {};
        for (const record of serverData.models.currency.records) {
            currencies[record.id] = record;
        }
        patchWithCleanup(session, { currencies });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="currency_id"/>
                    <templates><t t-name="kanban-box">
                        <div><field name="salary"/></div>
                    </t></templates>
                </kanban>`,
        });

        assert.deepEqual(getCardTexts(), [
            `$${nbsp}1750.00`,
            `$${nbsp}1500.00`,
            `2000.00${nbsp}€`,
            `$${nbsp}2222.00`,
        ]);
    });

    QUnit.test("quick create: keyboard navigation to buttons", async (assert) => {
        await makeView({
            arch: `
                <kanban on_create="quick_create">
                    <field name="bar"/>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="display_name"/>
                        </div>
                    </templates>
                </kanban>`,
            serverData,
            groupBy: ["bar"],
            resModel: "partner",
            type: "kanban",
        });

        // Open quick create
        await createRecord();

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_quick_create");

        // Fill in mandatory field
        await editQuickCreateInput("display_name", "aaa");

        // Tab -> goes to first primary button
        const nameInput = target.querySelector(".o_field_widget[name=display_name] input");
        nameInput.focus();

        const addButton = target.querySelector(".o_kanban_add");
        const event = triggerEvent(nameInput, null, "keydown", { key: "Tab" }, { fast: true });
        assert.strictEqual(getNextTabableElement(target), addButton);
        assert.ok(!event.defaultPrevented);
        addButton.focus();
        await nextTick();
        assert.hasClass(document.activeElement, "btn btn-primary o_kanban_add");
    });

    QUnit.test("kanban with isHtmlEmpty method", async (assert) => {
        serverData.models.product.fields.description = { string: "Description", type: "html" };
        serverData.models.product.records.push(
            {
                id: 11,
                display_name: "product 11",
                description: "<span class='text-info'>hello</hello>",
            },
            {
                id: 12,
                display_name: "product 12",
                description: "<p class='a'><span style='color:red;'/><br/></p>",
            }
        );

        await makeView({
            type: "kanban",
            resModel: "product",
            serverData,
            arch: `<kanban>
                        <field name="description"/>
                        <templates><t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="display_name"/>
                                <div class="test" t-if="!widget.isHtmlEmpty(record.description.raw_value)">
                                    <t t-out="record.description.value"/>
                                </div>
                            </div>
                        </t></templates>
                    </kanban>`,
            domain: [["id", "in", [11, 12]]],
        });
        assert.containsOnce(
            target,
            ".o_kanban_record:first-child div.test",
            "the container is displayed if description have actual content"
        );
        assert.strictEqual(
            target
                .querySelector(".o_kanban_record:first-child div.test span.text-info")
                .innerText.trim(),
            "hello",
            "the inner html content is rendered properly"
        );
        assert.containsNone(
            target,
            ".o_kanban_record:last-child div.test",
            "the container is not displayed if description just have formatting tags and no actual content"
        );
    });

    QUnit.test(
        "progressbar filter state is kept unchanged when domain is updated (records still in group)",
        async (assert) => {
            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                <kanban default_group_by="bar">
                    <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                    <field name="foo"/>
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="id"/>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            });

            // Check that we have 2 columns and check their progressbar's state
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsNone(target, ".o_kanban_group.o_kanban_group_show");
            assert.deepEqual(
                [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
                ["No", "Yes"]
            );
            assert.deepEqual(getTooltips(0), ["1 blip"]);
            assert.deepEqual(getTooltips(1), ["1 yop", "1 blip", "1 Other"]);

            // Apply an active filter
            await click(target, ".o_kanban_group:nth-child(2) .progress-bar.bg-success");

            assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show");
            assert.strictEqual(
                target.querySelector(".o_kanban_group.o_kanban_group_show .o_column_title")
                    .innerText,
                "Yes"
            );

            // Add searchdomain to something restricting progressbars' values (records still in filtered group)
            await reload(kanban, { domain: [["foo", "=", "yop"]] });

            // Check that we have now 1 column only and check its progressbar's state
            assert.containsOnce(target, ".o_kanban_group");
            assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show");
            assert.strictEqual(target.querySelector(".o_column_title").innerText, "Yes");
            assert.deepEqual(getTooltips(), ["1 yop"]);

            // Undo searchdomain
            await reload(kanban, { domain: [] });

            // Check that we have 2 columns back and check their progressbar's state
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show");
            assert.deepEqual(
                [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
                ["No", "Yes"]
            );
            assert.deepEqual(getTooltips(0), ["1 blip"]);
            assert.deepEqual(getTooltips(1), ["1 yop", "1 blip", "1 Other"]);
        }
    );

    QUnit.test(
        "progressbar filter state is kept unchanged when domain is updated (emptying group)",
        async (assert) => {
            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                    <kanban default_group_by="bar">
                        <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                        <field name="foo"/>
                        <field name="bar"/>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="id"/>
                                    <field name="foo"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
            });

            // Check that we have 2 columns, check their progressbar's state and check records
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsNone(target, ".o_kanban_group.o_kanban_group_show");
            assert.deepEqual(
                [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
                ["No", "Yes"]
            );
            assert.deepEqual(getTooltips(0), ["1 blip"]);
            assert.deepEqual(getCardTexts(0), ["4blip"]);
            assert.deepEqual(getTooltips(1), ["1 yop", "1 blip", "1 Other"]);
            assert.deepEqual(getCardTexts(1), ["1yop", "2blip", "3gnap"]);

            // Apply an active filter
            await click(target, ".o_kanban_group:nth-child(2) .progress-bar.bg-success");
            assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show");
            assert.strictEqual(
                target.querySelector(".o_kanban_group.o_kanban_group_show .o_column_title")
                    .innerText,
                "Yes"
            );
            assert.deepEqual(getTooltips(1), ["1 yop", "1 blip", "1 Other"]);
            assert.deepEqual(getCardTexts(1), ["1yop"]);

            // Add searchdomain to something restricting progressbars' values + emptying the filtered group
            await reload(kanban, { domain: [["foo", "=", "blip"]] });

            // Check that we still have 2 columns, check their progressbar's state and check records
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsNone(target, ".o_kanban_group.o_kanban_group_show");
            assert.deepEqual(
                [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
                ["No", "Yes"]
            );
            assert.deepEqual(getTooltips(0), ["1 blip"]);
            assert.deepEqual(getCardTexts(0), ["4blip"]);
            assert.deepEqual(getTooltips(1), ["1 blip"]);
            assert.deepEqual(getCardTexts(1), ["2blip"]);

            // Undo searchdomain
            await reload(kanban, { domain: [] });

            // Check that we still have 2 columns and check their progressbar's state
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsNone(target, ".o_kanban_group.o_kanban_group_show");
            assert.deepEqual(
                [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
                ["No", "Yes"]
            );
            assert.deepEqual(getTooltips(0), ["1 blip"]);
            assert.deepEqual(getCardTexts(0), ["4blip"]);
            assert.deepEqual(getTooltips(1), ["1 yop", "1 blip", "1 Other"]);
            assert.deepEqual(getCardTexts(1), ["1yop", "2blip", "3gnap"]);
        }
    );

    QUnit.test(
        "filtered column keeps consistent counters when dropping in a non-matching record",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                <kanban default_group_by="bar">
                    <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                    <field name="foo"/>
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="id"/>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            });

            // Check that we have 2 columns, check their progressbar's state, and check records
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsNone(target, ".o_kanban_group.o_kanban_group_show");
            assert.deepEqual(
                [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
                ["No", "Yes"]
            );
            assert.deepEqual(getTooltips(0), ["1 blip"]);
            assert.deepEqual(getCardTexts(0), ["4blip"]);
            assert.deepEqual(getTooltips(1), ["1 yop", "1 blip", "1 Other"]);
            assert.deepEqual(getCardTexts(1), ["1yop", "2blip", "3gnap"]);

            // Apply an active filter
            await click(target, ".o_kanban_group:nth-child(2) .progress-bar.bg-success");

            assert.hasClass(
                target.querySelector(".o_kanban_group:nth-child(2)"),
                "o_kanban_group_show"
            );
            assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show");
            assert.strictEqual(
                target.querySelector(".o_kanban_group.o_kanban_group_show .o_column_title")
                    .innerText,
                "Yes"
            );
            assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show .o_kanban_record");
            assert.deepEqual(getCardTexts(1), ["1yop"]);

            // Drop in the non-matching record from first column
            await dragAndDrop(
                ".o_kanban_group:first-child .o_kanban_record",
                ".o_kanban_group.o_kanban_group_show"
            );

            // Check that we have 2 columns, check their progressbar's state, and check records
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show");
            assert.deepEqual(
                [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
                ["No", "Yes"]
            );
            assert.deepEqual(getTooltips(0), []);
            assert.deepEqual(getCardTexts(0), []);
            assert.deepEqual(getTooltips(1), ["1 yop", "2 blip", "1 Other"]);
            assert.deepEqual(getCardTexts(1), ["1yop", "4blip"]);
        }
    );

    QUnit.test("filtered column is reloaded when dragging out its last record", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                    <kanban default_group_by="bar">
                        <progressbar field="foo" colors='{"yop": "success", "blip": "danger"}'/>
                        <field name="foo"/>
                        <field name="bar"/>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="id"/>
                                    <field name="foo"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
            async mockRPC(route, args) {
                assert.step(args.method || route);
            },
        });

        // Check that we have 2 columns, check their progressbar's state, and check records
        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsNone(target, ".o_kanban_group.o_kanban_group_show");
        assert.deepEqual(
            [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
            ["No", "Yes"]
        );
        assert.deepEqual(getTooltips(0), ["1 blip"]);
        assert.deepEqual(getCardTexts(0), ["4blip"]);
        assert.deepEqual(getTooltips(1), ["1 yop", "1 blip", "1 Other"]);
        assert.deepEqual(getCardTexts(1), ["1yop", "2blip", "3gnap"]);
        assert.verifySteps([
            "get_views",
            "web_read_group",
            "read_progress_bar",
            "web_search_read",
            "web_search_read",
        ]);

        // Apply an active filter
        await click(target, ".o_kanban_group:nth-child(2) .progress-bar.bg-success");

        assert.hasClass(
            target.querySelector(".o_kanban_group:nth-child(2)"),
            "o_kanban_group_show"
        );
        assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show");
        assert.strictEqual(
            target.querySelector(".o_kanban_group.o_kanban_group_show .o_column_title").innerText,
            "Yes"
        );
        assert.containsOnce(target, ".o_kanban_group.o_kanban_group_show .o_kanban_record");
        assert.deepEqual(getCardTexts(1), ["1yop"]);
        assert.verifySteps(["web_search_read"]);

        // Drag out its only record onto the first column
        await dragAndDrop(
            ".o_kanban_group.o_kanban_group_show .o_kanban_record",
            ".o_kanban_group:first-child"
        );

        // Check that we have 2 columns, check their progressbar's state, and check records
        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsNone(target, ".o_kanban_group.o_kanban_group_show");
        assert.deepEqual(
            [...target.querySelectorAll(".o_column_title")].map((el) => el.innerText),
            ["No", "Yes"]
        );
        assert.deepEqual(getTooltips(0), ["1 yop", "1 blip"]);
        assert.deepEqual(getCardTexts(0), ["4blip", "1yop"]);
        assert.deepEqual(getTooltips(1), ["1 blip", "1 Other"]);
        assert.deepEqual(getCardTexts(1), ["2blip", "3gnap"]);
        assert.verifySteps([
            "write",
            "read_progress_bar",
            "read", // read happens is delayed by the ORM batcher
            "web_search_read",
            "/web/dataset/resequence",
            "read",
        ]);
    });

    QUnit.test("kanban widget can extract props from attrs", async (assert) => {
        class TestWidget extends Component {}
        TestWidget.template = xml`<div class="o-test-widget-option" t-esc="props.title"/>`;
        TestWidget.extractProps = ({ attrs }) => {
            return {
                title: attrs.title,
            };
        };
        viewWidgetRegistry.add("widget_test_option", TestWidget);

        await makeView({
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <widget name="widget_test_option" title="Widget with Option"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            serverData,
            resModel: "partner",
            type: "kanban",
        });

        assert.containsN(target, ".o-test-widget-option", 4);
        assert.strictEqual(
            target.querySelector(".o-test-widget-option").textContent,
            "Widget with Option"
        );
    });

    QUnit.test("action/type attributes on kanban arch, type='object'", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban action="a1" type="object">
                    <templates><t t-name="kanban-box">
                        <div>
                            <p>some value</p><field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        patchWithCleanup(kanban.env.services.action, {
            doActionButton(params) {
                assert.step(`doActionButton type ${params.type} name ${params.name}`);
                params.onClose();
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);
        await click(target.querySelector(".o_kanban_record p"));
        assert.verifySteps(["doActionButton type object name a1", "web_search_read"]);
    });

    QUnit.test("action/type attributes on kanban arch, type='action'", async (assert) => {
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban action="a1" type="action">
                    <templates><t t-name="kanban-box">
                        <div>
                            <p>some value</p><field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        patchWithCleanup(kanban.env.services.action, {
            doActionButton(params) {
                assert.step(`doActionButton type ${params.type} name ${params.name}`);
                params.onClose();
            },
        });

        assert.verifySteps(["get_views", "web_search_read"]);
        await click(target.querySelector(".o_kanban_record p"));
        assert.verifySteps(["doActionButton type action name a1", "web_search_read"]);
    });

    QUnit.test("Missing t-key is automatically filled with a warning", async (assert) => {
        patchWithCleanup(console, { warn: () => assert.step("warning") });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <span t-foreach="[1, 2, 3]" t-as="i" t-esc="i" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.verifySteps(["warning"]);
        assert.strictEqual(getCard(0).innerText, "123");
    });

    QUnit.test("Quick created record is rendered after load", async (assert) => {
        let def;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban on_create="quick_create">
                    <field name="category_ids" />
                    <progressbar field="foo" colors='{"yop": "success", "gnap": "warning", "blip": "danger"}' sum_field="int_field"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <span t-esc="record.category_ids.raw_value.length" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(_route, { method }) {
                if (method === "read") {
                    await def;
                }
                if (["name_create", "read"].includes(method)) {
                    assert.step(method);
                }
            },
        });

        assert.deepEqual(getCardTexts(0), ["0", "1"]);
        assert.verifySteps(["read"]);

        def = makeDeferred();

        await quickCreateRecord(0);
        await editQuickCreateInput("display_name", "Test");
        await validateRecord();

        def.resolve();
        await nextTick();

        assert.deepEqual(getCardTexts(0), ["0", "0", "1"]);
        assert.verifySteps(["name_create", "read"]);
    });

    QUnit.test("Allow use of 'editable'/'deletable' in ungrouped kanban", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban on_create="quick_create">
                    <templates>
                        <div t-name="kanban-box">
                            <button t-if="widget.editable">EDIT</button>
                            <button t-if="widget.deletable">DELETE</button>
                        </div>
                    </templates>
                </kanban>`,
        });

        assert.deepEqual(getCardTexts(), ["EDITDELETE", "EDITDELETE", "EDITDELETE", "EDITDELETE"]);
    });

    QUnit.test("folded groups are kept when leaving and coming back", async (assert) => {
        serverData.views = {
            "partner,false,kanban": `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="int_field"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            "partner,false,search": "<search/>",
            "partner,false,form": "<form/>",
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "kanban"],
                [false, "form"],
            ],
            context: {
                group_by: ["product_id"],
            },
        });

        assert.containsOnce(target, ".o_kanban_view");
        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsNone(target, ".o_column_folded");
        assert.containsN(target, ".o_kanban_record", 4);

        // fold the first group
        const clickColumnAction = await toggleColumnActions(0);
        await clickColumnAction("Fold");
        assert.containsOnce(target, ".o_column_folded");
        assert.containsN(target, ".o_kanban_record", 2);

        // open a record and go back
        await click(target.querySelector(".o_kanban_record"));
        assert.containsOnce(target, ".o_form_view");
        await click(target.querySelector(".breadcrumb-item a"));

        assert.containsOnce(target, ".o_column_folded");
        assert.containsN(target, ".o_kanban_record", 2);
    });

    QUnit.test("loaded records are kept when leaving and coming back", async (assert) => {
        serverData.views = {
            "partner,false,kanban": `
                <kanban limit="1">
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="int_field"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            "partner,false,search": "<search/>",
            "partner,false,form": "<form/>",
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "kanban"],
                [false, "form"],
            ],
            context: {
                group_by: ["product_id"],
            },
        });

        assert.containsOnce(target, ".o_kanban_view");
        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(target, ".o_kanban_record", 2);

        // load more records in second group
        await loadMore(1);
        assert.containsN(target, ".o_kanban_record", 3);

        // open a record and go back
        await click(target.querySelector(".o_kanban_record"));
        assert.containsOnce(target, ".o_form_view");
        await click(target.querySelector(".breadcrumb-item a"));

        assert.containsN(target, ".o_kanban_record", 3);
    });

    QUnit.test("basic rendering with 2 groupbys", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["bar", "product_id"],
            async mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);
        assert.verifySteps(["get_views", "web_read_group", "web_search_read", "web_search_read"]);
    });

    QUnit.test("basic rendering with a date groupby with a granularity", async (assert) => {
        serverData.models.partner.records[0].date = "2022-06-23";
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["date:day"],
            async mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    assert.deepEqual(args.kwargs.fields, ["foo", "date"]);
                    assert.deepEqual(args.kwargs.groupby, ["date:day"]);
                }
                assert.step(args.method);
            },
        });

        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 3);
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.verifySteps(["get_views", "web_read_group", "web_search_read", "web_search_read"]);
    });

    QUnit.test("quick create record and click outside (no dirty input)", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban limit="2">
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["bar"],
            createRecord: () => {
                assert.step("create record");
            },
        });

        assert.containsNone(target, ".o_kanban_quick_create");

        await quickCreateRecord();

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_quick_create");

        await click(target, ".o_control_panel");

        assert.containsNone(target, ".o_kanban_quick_create");

        await quickCreateRecord();

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_quick_create");

        await quickCreateRecord(1);

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_quick_create");

        await click(target, ".o_kanban_load_more button");

        assert.containsNone(target, ".o_kanban_quick_create");

        await quickCreateRecord();

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_quick_create");

        assert.verifySteps([]);

        await click(target, ".o-kanban-button-new");

        assert.verifySteps(["create record"]);
        assert.containsNone(target, ".o_kanban_quick_create");
    });

    QUnit.test("quick create record and click outside (with dirty input)", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban limit="2">
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["bar"],
            createRecord: () => {
                assert.step("create record");
            },
        });

        assert.containsNone(target, ".o_kanban_quick_create");

        await quickCreateRecord();

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_quick_create");

        await editInput(target, ".o_kanban_quick_create [name=display_name] input", "ABC");

        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create [name=display_name] input").value,
            "ABC"
        );

        await click(target, ".o_control_panel");

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_quick_create");
        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create [name=display_name] input").value,
            "ABC"
        );

        await quickCreateRecord(1);

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_quick_create");
        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create [name=display_name] input").value,
            ""
        );

        await editInput(target, ".o_kanban_quick_create [name=display_name] input", "ABC");

        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create [name=display_name] input").value,
            "ABC"
        );

        await click(target, ".o_kanban_load_more button");

        assert.containsNone(target, ".o_kanban_quick_create");

        await quickCreateRecord();

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_quick_create");

        await editInput(target, ".o_kanban_quick_create [name=display_name] input", "ABC");

        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create [name=display_name] input").value,
            "ABC"
        );
        assert.verifySteps([]);

        await click(target, ".o-kanban-button-new");

        assert.verifySteps(["create record"]);
        assert.containsNone(target, ".o_kanban_quick_create");
    });

    QUnit.test("quick create record and click on 'Load more'", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban limit="2">
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["bar"],
        });

        assert.containsNone(target, ".o_kanban_quick_create");

        await quickCreateRecord(1);

        assert.containsOnce(target, ".o_kanban_quick_create");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_quick_create");
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);

        await click(target, ".o_kanban_load_more button");
        await nextTick();

        assert.containsNone(target, ".o_kanban_quick_create");
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);
    });

    QUnit.test("classes on dropdown menu do not end on dropdown main div", async (assert) => {
        serverData.models.partner.records.splice(1, 3); // keep one record only
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                                <div class="dropdown" />
                                <ul class="o_kanban_card_manage_pane dropdown-menu" role="menu">
                                    <li>Hello</li>
                                </ul>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
        });

        const dropdown = target.querySelector(".o_kanban_record .o-dropdown");
        assert.isVisible(dropdown);
        assert.hasClass(dropdown, "o_dropdown_kanban");
        assert.doesNotHaveClass(dropdown, "dropdown-menu");
        assert.doesNotHaveClass(dropdown, "o_kanban_card_manage_pane");
        await click(dropdown, "button.dropdown-toggle");
        assert.containsOnce(dropdown, ".o_kanban_card_manage_pane.dropdown-menu");
    });

    QUnit.test("classes on toggler do not end on dropdown main div", async (assert) => {
        serverData.models.partner.records.splice(1, 3); // keep one record only
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                                <a class="o_kanban_manage_toggle_button o_left" href="#">
                                    <i class="fa fa-ellipsis-v" role="img" aria-label="Manage" title="Manage"/>
                                </a>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
        });

        const dropdown = target.querySelector(".o_kanban_record .o-dropdown");
        assert.isVisible(dropdown);
        assert.hasClass(dropdown, "o_dropdown_kanban");
        assert.doesNotHaveClass(dropdown, "o_kanban_manage_toggle_button");
        assert.doesNotHaveClass(dropdown, "o_left");
        assert.containsOnce(dropdown, ".o_kanban_manage_toggle_button.o_left");
    });

    QUnit.test("dropdown is closed on item click", async (assert) => {
        serverData.models.partner.records.splice(1, 3); // keep one record only
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                            <div class="o_dropdown_kanban dropdown">
                                <a role="button" class="dropdown-toggle o-no-caret btn" data-bs-toggle="dropdown" data-bs-display="static" href="#" aria-label="Dropdown menu" title="Dropdown menu">
                                    <span class="fa fa-ellipsis-v"/>
                                </a>
                                <div class="dropdown-menu" role="menu">
                                    <a role="menuitem" class="dropdown-item">Item</a>
                                </div>
                            </div>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
        });

        assert.containsNone(target, ".dropdown-menu");
        await click(target, ".o_kanban_renderer .dropdown-toggle");
        assert.containsOnce(target, ".dropdown-menu");
        await click(target, ".o_kanban_renderer .dropdown-menu .dropdown-item");
        assert.containsNone(target, ".dropdown-menu");
    });

    QUnit.test(
        "classes on dropdown are on dropdown main div but not the other attributes",
        async (assert) => {
            serverData.models.partner.records.splice(1, 3); // keep one record only
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: /* xml */ `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="foo"/>
                                    <div class="o_kanban_manage_button_section my_class" placeholder="Bouh"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                `,
            });

            const dropdown = target.querySelector(".o_kanban_record .o-dropdown");
            assert.isVisible(dropdown);
            assert.strictEqual(
                dropdown.className,
                "o-dropdown dropdown o_dropdown_kanban o_kanban_manage_button_section my_class o-dropdown--no-caret"
            );
            assert.notOk(dropdown.hasAttribute("placeholder"));
        }
    );

    QUnit.test("declaring only the menu does not insert a dropdown", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                                <ul class="o_kanban_card_manage_pane dropdown-menu" role="menu">
                                    <li>Hello</li>
                                </ul>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
        });

        assert.containsNone(target, ".o_kanban_record .o-dropdown");
    });

    QUnit.test("support multiple dropdowns", async (assert) => {
        assert.expect(4);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <field name="bar" />
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo" />
                            <t t-if="record.bar.raw_value">
                                <div class="dropdown dropdown-true">
                                    <div class="dropdown-toggle">
                                        <span class="toggler-true">TOGGLER TRUE</span>
                                    </div>
                                    <div class="dropdown-menu">
                                        <span class="menu-true">MENU TRUE</span>
                                    </div>
                                </div>
                            </t>
                            <t t-else="">
                                <div class="dropdown-toggle">
                                    <span class="toggler-false">TOGGLER FALSE</span>
                                </div>
                                <div class="dropdown-menu">
                                    <span class="menu-false">MENU FALSE</span>
                                </div>
                            </t>
                        </div>
                    </templates>
                </kanban>
            `,
        });

        assert.containsN(target, ".o_kanban_renderer .dropdown-true", 3);
        assert.containsN(target, ".o_kanban_renderer .dropdown", 4);

        await toggleRecordDropdown(2);

        assert.strictEqual(getCardTexts()[2], "gnap\nTOGGLER TRUE\nMENU TRUE");

        await toggleRecordDropdown(3);

        assert.strictEqual(getCardTexts()[3], "blip\nTOGGLER FALSE\nMENU FALSE");
    });

    QUnit.test("can use JSON in kanban template", async (assert) => {
        serverData.models.partner.records = [{ id: 1, foo: '["g", "e", "d"]' }];
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="foo"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <span t-foreach="JSON.parse(record.foo.raw_value)" t-as="v" t-key="v_index" t-esc="v"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
        });
        assert.containsOnce(target, ".o_kanban_record:not(.o_kanban_ghost)");
        assert.containsN(target, ".o_kanban_record span", 3);
        assert.strictEqual(target.querySelector(".o_kanban_record").innerText, "ged");
    });

    QUnit.test("Dropdowns in subtemplates", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <div class="dropdown-menu">
                                MENU
                            </div>
                            <field name="foo" />
                            <t t-call="another-template"/>
                        </div>
                        <span t-name="another-template">
                            <div class="dropdown-toggle">
                                TOGGLER
                            </div>
                        </span>
                    </templates>
                </kanban>`,
        });

        assert.containsN(target, ".o_kanban_record .dropdown", 4);

        await toggleRecordDropdown(0);

        assert.strictEqual(getCardTexts()[0], "yop\nTOGGLER\nMENU");
    });

    QUnit.test(
        "Color '200' (gray) can be used twice (for false value and another value) in progress bar",
        async (assert) => {
            serverData.models.partner.records.push({ id: 5, bar: true }, { id: 6, bar: false });
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                <kanban>
                    <field name="bar"/>
                    <field name="foo"/>
                    <progressbar field="foo" colors='{"yop": "200", "gnap": "warning", "blip": "danger"}'/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="state"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
                groupBy: ["bar"],
            });

            assert.containsN(target, ".o_kanban_group:nth-child(1) .progress-bar", 2);
            assert.deepEqual(
                [...target.querySelectorAll(".o_kanban_group:nth-child(1) .progress-bar")].map(
                    (el) => el.dataset.tooltip
                ),
                ["1 blip", "1 Other"]
            );
            assert.containsN(target, ".o_kanban_group:nth-child(2) .progress-bar", 4);
            assert.deepEqual(
                [...target.querySelectorAll(".o_kanban_group:nth-child(2) .progress-bar")].map(
                    (el) => el.dataset.tooltip
                ),
                ["1 yop", "1 gnap", "1 blip", "1 Other"]
            );
            assert.deepEqual(getCounters(), ["2", "4"]);

            await click(target.querySelector(".o_kanban_group:nth-child(2) .progress-bar"));

            assert.deepEqual(getCounters(), ["2", "1"]);
            assert.strictEqual(
                target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").innerText,
                "ABC"
            );
            assert.containsNone(target, ".o_kanban_group:nth-child(2) .o_kanban_load_more");

            await click(
                target.querySelector(".o_kanban_group:nth-child(2) .progress-bar:nth-child(2)")
            );

            assert.deepEqual(getCounters(), ["2", "1"]);
            assert.strictEqual(
                target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").innerText,
                "GHI"
            );
            assert.containsNone(target, ".o_kanban_group:nth-child(2) .o_kanban_load_more");

            await click(
                target.querySelector(".o_kanban_group:nth-child(2) .progress-bar:nth-child(4)")
            );

            assert.deepEqual(getCounters(), ["2", "1"]);
            assert.strictEqual(
                target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").innerText,
                ""
            );
            assert.containsNone(target, ".o_kanban_group:nth-child(2) .o_kanban_load_more");
        }
    );

    QUnit.test("update field on which progress bars are computed", async (assert) => {
        serverData.models.partner.records.push({ id: 5, state: "abc", bar: true });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                    <templates>
                        <div t-name="kanban-box">
                            <field name="state" widget="state_selection" />
                            <field name="id" />
                        </div>
                    </templates>
                </kanban>
            `,
            groupBy: ["bar"],
        });

        // Initial state: 2 columns, the "Yes" column contains 2 records "abc", 1 "def" and 1 "ghi"
        assert.deepEqual(getCounters(), ["1", "4"]);
        assert.containsN(getColumn(1), ".o_kanban_record", 4);
        assert.containsN(getColumn(1), ".o_kanban_counter_progress .progress-bar", 3);
        assert.strictEqual(getProgressBars(1)[0].style.width, "50%"); // abc: 2
        assert.strictEqual(getProgressBars(1)[1].style.width, "25%"); // def: 1
        assert.strictEqual(getProgressBars(1)[2].style.width, "25%"); // ghi: 1

        // Filter on state "abc" => matches 2 records
        await click(getProgressBars(1)[0]);

        assert.deepEqual(getCounters(), ["1", "2"]);
        assert.containsN(getColumn(1), ".o_kanban_record", 2);
        assert.containsN(getColumn(1), ".o_kanban_counter_progress .progress-bar", 3);
        assert.strictEqual(getProgressBars(1)[0].style.width, "50%"); // abc: 2
        assert.strictEqual(getProgressBars(1)[1].style.width, "25%"); // def: 1
        assert.strictEqual(getProgressBars(1)[2].style.width, "25%"); // ghi: 1

        // Changes the state of the first record of the "Yes" column to "def"
        // The updated record should remain visible
        await click(getCard(2), ".o_status");
        await click(getCard(2), ".o_field_state_selection .dropdown-item:first-child");

        assert.deepEqual(getCounters(), ["1", "1"]);
        assert.containsN(getColumn(1), ".o_kanban_record", 2);
        assert.containsN(getColumn(1), ".o_kanban_counter_progress .progress-bar", 3);
        assert.strictEqual(getProgressBars(1)[0].style.width, "25%"); // abc: 1
        assert.strictEqual(getProgressBars(1)[1].style.width, "50%"); // def: 2
        assert.strictEqual(getProgressBars(1)[2].style.width, "25%"); // ghi: 1

        // Filter on state "def" => matches 2 records (including the one we just changed)
        await click(getProgressBars(1)[1]);

        assert.deepEqual(getCounters(), ["1", "2"]);
        assert.containsN(getColumn(1), ".o_kanban_record", 2);
        assert.strictEqual(getProgressBars(1)[0].style.width, "25%"); // abc: 1
        assert.strictEqual(getProgressBars(1)[1].style.width, "50%"); // def: 2
        assert.strictEqual(getProgressBars(1)[2].style.width, "25%"); // ghi: 1

        // Filter back on state "abc" => matches only 1 record
        await click(getProgressBars(1)[0]);

        assert.deepEqual(getCounters(), ["1", "1"]);
        assert.containsN(getColumn(1), ".o_kanban_record", 1);
        assert.strictEqual(getProgressBars(1)[0].style.width, "25%"); // abc: 1
        assert.strictEqual(getProgressBars(1)[1].style.width, "50%"); // def: 2
        assert.strictEqual(getProgressBars(1)[2].style.width, "25%"); // ghi: 1
    });

    QUnit.test("click on the progressBar of a new column", async (assert) => {
        serverData.models.partner.records = [];
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                    <progressbar field="state" colors='{"abc": "success", "def": "warning", "ghi": "danger"}' />
                    <templates>
                        <div t-name="kanban-box">
                            <field name="state" widget="state_selection" />
                            <field name="id" />
                        </div>
                    </templates>
                </kanban>
            `,
            groupBy: ["product_id"],
            domain: [["id", ">", 0]],
            mockRPC: (route, args) => {
                const { method, kwargs } = args;
                if (args.method === "web_search_read") {
                    assert.step(method);
                    assert.deepEqual(kwargs.domain, [
                        "&",
                        "&",
                        ["id", ">", 0],
                        ["product_id", "=", 6],
                        "!",
                        ["state", "in", ["abc", "def", "ghi"]],
                    ]);
                }
            },
        });

        // Create a new column
        await editColumnName("new column");
        await validateColumn();

        // Crete a record in the new column
        await quickCreateRecord();
        await editQuickCreateInput("display_name", "new product");
        await validateRecord();
        assert.containsOnce(target, ".o_kanban_record");

        // Togggle the progressBar
        await click(getProgressBars(0)[0]);
        assert.containsOnce(target, ".o_kanban_record");

        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test(
        "keep focus inside control panel when pressing arrowdown and no kanban card",
        async (assert) => {
            serverData.models.partner.records = [];
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                groupBy: ["product_id"],
                arch: /* xml */ `
                    <kanban on_create="quick_create">
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="display_name"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                `,
            });

            // Check that there is a column quick create
            assert.containsOnce(target, ".o_column_quick_create");
            await editColumnName("new col");
            await validateColumn();

            // Check that there is only one group and no kanban card
            assert.containsOnce(target, ".o_kanban_group");
            assert.containsOnce(target, ".o_kanban_group.o_kanban_no_records");
            assert.containsNone(target, ".o_kanban_record");

            // Check that the focus is on the searchview input
            await quickCreateRecord();
            assert.containsOnce(target, ".o_kanban_group.o_kanban_no_records");
            assert.containsOnce(target, ".o_kanban_quick_create");
            assert.containsNone(target, ".o_kanban_record");

            // Somehow give the focus in the control panel, i.e. in the search view
            // Note that a simple click in the control panel should normally close the quick
            // create, so in order to give the focus in the search input, the user would
            // normally have to right-click on it then press escape. These are behaviors
            // handled through the browser, so we simply call focus directly here.
            target.querySelector(".o_searchview_input").focus();

            // Make sure no async code will have a side effect on the focused element
            await nextTick();
            assert.hasClass(document.activeElement, "o_searchview_input");

            // Trigger the ArrowDown hotkey
            triggerHotkey("ArrowDown");
            await nextTick();
            assert.hasClass(document.activeElement, "o_searchview_input");
        }
    );

    QUnit.test("quick create record with bottom quick create button", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "product",
            serverData,
            groupBy: ["name"],
            arch: /* xml */ `
                <kanban on_create="quick_create">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="display_name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
        });

        // quick create at the bottom and verify the order
        await quickCreateRecord(1, "bottom");
        await editQuickCreateInput("display_name", "new product");
        await validateRecord();
        assert.deepEqual(getCardTexts(1), ["xmo", "new product"]);
        // directly re-create another records at the bottom
        await editQuickCreateInput("display_name", "new product 2");
        await validateRecord();
        assert.deepEqual(getCardTexts(1), ["xmo", "new product", "new product 2"]);
    });

    QUnit.test("no leak of TransactionInProgress (grouped case)", async (assert) => {
        let def;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="state"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            groupBy: ["state"],
            async mockRPC(route) {
                if (route === "/web/dataset/resequence") {
                    assert.step("resequence");
                    await Promise.resolve(def);
                }
            },
        });

        def = makeDeferred();

        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_record");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(1) .o_kanban_record").innerText,
            "yop"
        );
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").innerText,
            "blip"
        );
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 2);

        assert.verifySteps([]);

        // move "yop" from first to second column
        await dragAndDrop(
            ".o_kanban_group:nth-child(1) .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        assert.containsNone(target, ".o_kanban_group:nth-child(1) .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_group:nth-child(2) .o_kanban_record")].map(
                (el) => el.innerText
            ),
            ["blip", "yop"]
        );
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 2);

        assert.verifySteps(["resequence"]);

        // try to move "yop" from second to third column
        await dragAndDrop(
            ".o_kanban_group:nth-child(2) .o_kanban_record:nth-child(3)", // move yop
            ".o_kanban_group:nth-child(3)"
        );

        assert.containsNone(target, ".o_kanban_group:nth-child(1) .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_group:nth-child(2) .o_kanban_record")].map(
                (el) => el.innerText
            ),
            ["blip", "yop"]
        );
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 2);

        assert.verifySteps([]);

        def.resolve();
        await nextTick();

        // try again to move "yop" from second to third column
        await dragAndDrop(
            ".o_kanban_group:nth-child(2) .o_kanban_record:nth-child(3)", // move yop
            ".o_kanban_group:nth-child(3)"
        );

        assert.containsNone(target, ".o_kanban_group:nth-child(1) .o_kanban_record");
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 3);
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_group:nth-child(3) .o_kanban_record")].map(
                (el) => el.innerText
            ),
            ["gnap", "blip", "yop"]
        );

        assert.verifySteps(["resequence"]);
    });

    QUnit.test("no leak of TransactionInProgress (not grouped case)", async (assert) => {
        let def;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban records_draggable="1">
                    <field name="int_field" widget="handle" />
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            async mockRPC(route) {
                if (route === "/web/dataset/resequence") {
                    assert.step("resequence");
                    await Promise.resolve(def);
                }
            },
        });

        def = makeDeferred();

        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].map(
                (el) => el.innerText
            ),
            ["yop", "blip", "gnap", "blip"]
        );

        assert.verifySteps([]);

        // move "yop" to second place
        await dragAndDrop(".o_kanban_record", ".o_kanban_record:nth-child(2)");

        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].map(
                (el) => el.innerText
            ),
            ["yop", "blip", "gnap", "blip"]
        );
        assert.verifySteps(["resequence"]);

        // try again
        await dragAndDrop(".o_kanban_record", ".o_kanban_record:nth-child(2)");

        assert.verifySteps([]);

        def.resolve();
        await nextTick();

        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].map(
                (el) => el.innerText
            ),
            ["blip", "yop", "gnap", "blip"]
        );

        await dragAndDrop(".o_kanban_record:nth-child(2)", ".o_kanban_record:nth-child(3)");

        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].map(
                (el) => el.innerText
            ),
            ["blip", "gnap", "yop", "blip"]
        );
        assert.verifySteps(["resequence"]);
    });

    QUnit.test("dragged record cannot be saved", async (assert) => {
        let def;
        serverData.models.partner.records = [
            { id: 1, bar: false, state: "abc" },
            { id: 2, bar: true, state: "def", foo: "blip" },
        ];
        serverData.models.partner.onchanges = {
            bar() {},
        };

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo" required="[('bar', '=', True)]"/>
                                <field name="state"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            groupBy: ["bar"],
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step("onchange");
                    await Promise.resolve(def);
                }
            },
        });

        patchWithCleanup(kanban.env.services.notification, {
            add(message, options) {
                assert.step("notification");
                assert.strictEqual(options.title, "Invalid fields: ");
                assert.strictEqual(`${message}`, "<ul><li>Foo</li></ul>");
            },
        });

        def = makeDeferred();

        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_record");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(1) .o_kanban_record").innerText,
            "ABC"
        );
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").innerText,
            "blipDEF"
        );

        assert.verifySteps([]);

        // move "yop" from first to second column
        await dragAndDrop(
            ".o_kanban_group:nth-child(1) .o_kanban_record",
            ".o_kanban_group:nth-child(2)"
        );

        assert.containsNone(target, ".o_kanban_group:nth-child(1) .o_kanban_record");
        assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_group:nth-child(2) .o_kanban_record")].map(
                (el) => el.innerText
            ),
            ["blipDEF", "ABC"]
        );
        assert.verifySteps(["onchange"]);

        def.resolve();
        await nextTick();

        assert.containsOnce(target, ".o_kanban_group:nth-child(1) .o_kanban_record");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(1) .o_kanban_record").innerText,
            "ABC"
        );
        assert.containsOnce(target, ".o_kanban_group:nth-child(2) .o_kanban_record");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").innerText,
            "blipDEF"
        );
        assert.verifySteps(["notification"]);
    });

    QUnit.test("renders banner_route", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban banner_route="/mybody/isacage">
                    <templates>
                        <t t-name="kanban-box">
                            <div/>
                        </t>
                    </templates>
                </kanban>
            `,
            groupBy: ["bar"],
            async mockRPC(route) {
                if (route === "/mybody/isacage") {
                    assert.step(route);
                    return { html: `<div class="setmybodyfree">myBanner</div>` };
                }
            },
        });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(target, ".setmybodyfree");
    });

    QUnit.test("fieldDependencies support for fields", async (assert) => {
        class CustomField extends Component {}
        CustomField.fieldDependencies = {
            int_field: { type: "integer" },
        };
        CustomField.template = xml`<span t-esc="props.record.data.int_field"/>`;
        registry.category("fields").add("custom_field", CustomField);

        await makeView({
            resModel: "partner",
            type: "kanban",
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo" widget="custom_field"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            serverData,
        });

        assert.strictEqual(target.querySelector("[name=foo] span").innerText, "10");
    });

    QUnit.test(
        "fieldDependencies support for fields: dependence on a relational field",
        async (assert) => {
            class CustomField extends Component {}
            CustomField.fieldDependencies = {
                product_id: { type: "many2one", relation: "product" },
            };
            CustomField.template = xml`<span t-esc="props.record.data.product_id[1]"/>`;
            registry.category("fields").add("custom_field", CustomField);

            await makeView({
                resModel: "partner",
                type: "kanban",
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="foo" widget="custom_field"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                `,
                serverData,
                mockRPC: (route, args) => {
                    assert.step(args.method);
                },
            });

            assert.strictEqual(target.querySelector("[name=foo] span").innerText, "hello");
            assert.verifySteps(["get_views", "web_search_read"]);
        }
    );

    QUnit.test("column quick create - title and placeholder", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
        });

        const productFieldName = serverData.models.partner.fields.product_id.string;
        assert.strictEqual(
            target.querySelector(".o_column_quick_create .o_quick_create_folded").innerText,
            productFieldName
        );

        await click(target, "button.o_kanban_add_column");
        assert.strictEqual(
            target
                .querySelector(
                    ".o_column_quick_create .o_quick_create_unfolded .input-group .o_input"
                )
                .getAttribute("placeholder"),
            productFieldName + "..."
        );
    });

    QUnit.test("fold a column and drag record on it should unfold it", async (assert) => {
        let searchReadProm;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="id"/>
                        </div>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(_route, { method }) {
                if (method === "web_search_read") {
                    await searchReadProm;
                }
            },
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsN(getColumn(0), ".o_kanban_record", 2);
        assert.containsN(getColumn(1), ".o_kanban_record", 2);

        const clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Fold");

        assert.containsN(getColumn(0), ".o_kanban_record", 2);
        assert.hasClass(getColumn(1), "o_column_folded");
        assert.strictEqual(getColumn(1).innerText, "xmo (2)");

        searchReadProm = makeDeferred();

        await dragAndDrop(".o_kanban_group:first-child .o_kanban_record", ".o_column_folded");

        assert.containsN(getColumn(0), ".o_kanban_record", 1);
        assert.hasClass(getColumn(1), "o_column_folded");
        assert.strictEqual(getColumn(1).innerText, "xmo (3)");

        searchReadProm.resolve();
        await nextTick();

        assert.containsN(getColumn(0), ".o_kanban_record", 1);
        assert.doesNotHaveClass(getColumn(1), "o_column_folded");
        assert.containsN(getColumn(1), ".o_kanban_record", 3);
    });

    QUnit.test("drag record on initially folded column should load it", async (assert) => {
        let searchReadProm;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="id"/>
                        </div>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(route, args, performRPC) {
                if (args.method === "web_read_group") {
                    const result = await performRPC(route, args);
                    result.groups[1].__fold = true;
                    return result;
                } else if (args.method === "web_search_read") {
                    await searchReadProm;
                }
            },
        });

        assert.containsN(getColumn(0), ".o_kanban_record", 2);
        assert.hasClass(getColumn(1), "o_column_folded");
        assert.strictEqual(getColumn(1).innerText, "xmo (2)");

        searchReadProm = makeDeferred();

        await dragAndDrop(".o_kanban_group:first-child .o_kanban_record", ".o_column_folded");

        assert.containsN(getColumn(0), ".o_kanban_record", 1);
        assert.hasClass(getColumn(1), "o_column_folded");
        assert.strictEqual(getColumn(1).innerText, "xmo (3)");

        searchReadProm.resolve();
        await nextTick();

        assert.containsN(getColumn(0), ".o_kanban_record", 1);
        assert.doesNotHaveClass(getColumn(1), "o_column_folded");
        assert.containsN(getColumn(1), ".o_kanban_record", 3);
    });

    QUnit.test("quick create record in grouped kanban in a form view dialog", async (assert) => {
        serverData.models.partner.fields.foo.default = "ABC";
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="bar"/>
                </form>
            `,
        };

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban on_create="quick_create">
                    <field name="product_id"/>
                    <templates>
                        <t t-name="kanban-box">
                            <t t-if="record.foo.raw_value" t-set="foo"/>
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            groupBy: ["product_id"],
            async mockRPC(route, { method }) {
                assert.step(method || route);
                if (method === "name_create") {
                    throw new RPCError();
                }
            },
        });

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "first column should contain two records"
        );

        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_group:first-child .o_kanban_record")].map(
                (el) => el.innerText
            ),
            ["yop", "gnap"]
        );

        assert.containsNone(target, ".modal");

        // click on 'Create', fill the quick create and validate
        await createRecord();
        await editQuickCreateInput("display_name", "new partner");
        await validateRecord();

        assert.containsOnce(target, ".modal");
        await clickSave(target.querySelector(".modal"));

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            3,
            "first column should contain three records"
        );

        assert.deepEqual(
            [...target.querySelectorAll(".o_kanban_group:first-child .o_kanban_record")].map(
                (el) => el.innerText
            ),
            ["ABC", "yop", "gnap"]
        );

        assert.verifySteps([
            "get_views",
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "onchange", // quick create
            "name_create", // should perform a name_create to create the record
            "get_views", // load views for form view dialog
            "onchange", // load of a virtual record in form view dialog
            "create", // save virtual record
            "read", // read the created record to get foo value
            "onchange", // reopen the quick create automatically
        ]);
    });

    QUnit.test("Move new record with onchanges and different active fields", async (assert) => {
        serverData.models.partner.fields.foo.default = "abc";
        serverData.models.partner.onchanges = {
            bar(obj) {
                obj.foo = [...obj.foo].reverse().join("");
            },
        };
        serverData.views["partner,some_view_ref,form"] = /* xml */ `
            <form>
                <field name="int_field" />
                <field name="category_ids" widget="many2many_tags" />
            </form>`;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban on_create="quick_create" quick_create_view="some_view_ref">
                    <field name="foo" />
                    <field name="bar" />
                    <templates>
                        <div t-name="kanban-box">
                            <t t-esc="record.foo.raw_value" />
                            <field name="int_field" />
                        </div>
                    </templates>
                </kanban>
            `,
            groupBy: ["bar"],
        });

        assert.deepEqual(getCardTexts(0), ["blip-4"]);
        assert.deepEqual(getCardTexts(1), ["yop10", "blip9", "gnap17"]);

        await quickCreateRecord(0);
        await editQuickCreateInput("int_field", "13");
        await selectDropdownItem(target, "category_ids", "gold");
        await validateRecord();

        assert.deepEqual(getCardTexts(0), ["abc13", "blip-4"]);
        assert.deepEqual(getCardTexts(1), ["yop10", "blip9", "gnap17"]);

        await dragAndDrop(".o_kanban_record", ".o_kanban_group:nth-child(2)");

        assert.deepEqual(getCardTexts(0), ["blip-4"]);
        assert.deepEqual(getCardTexts(1), ["yop10", "blip9", "gnap17", "cba13"]);
    });

    QUnit.test("no sample data when all groups are folded then one is unfolded", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban sample="1">
                    <templates>
                        <div t-name="kanban-box">
                            <field name="id"/>
                        </div>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
            async mockRPC(route, args, performRPC) {
                if (args.method === "web_read_group") {
                    const result = await performRPC(route, args);
                    for (const group of result.groups) {
                        group.__fold = true;
                    }
                    return result;
                }
            },
        });

        assert.containsN(target, ".o_column_folded", 2);

        const groupHandle = target.querySelector(".o_kanban_group");
        await click(groupHandle);

        assert.containsOnce(target, ".o_column_folded");
        assert.containsN(target, ".o_kanban_record", 2);
        assert.containsNone(target, "o_view_sample_data");
    });

    QUnit.test(
        "no content helper when all groups are folded but there are (unloaded) records",
        async (assert) => {
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: /* xml */ `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="id"/>
                        </div>
                    </templates>
                </kanban>`,
                groupBy: ["product_id"],
                async mockRPC(route, args, performRPC) {
                    if (args.method === "web_read_group") {
                        const result = await performRPC(route, args);
                        for (const group of result.groups) {
                            group.__fold = true;
                        }
                        return result;
                    }
                },
            });

            assert.containsN(target, ".o_column_folded", 2);

            assert.strictEqual(
                getNodesTextContent(target.querySelectorAll("span.o_column_title")).join(" "),
                "hello (2) xmo (2)"
            );

            assert.containsNone(target, ".o_nocontent_help");
        }
    );

    QUnit.test("Move multiple records in different columns simultaneously", async (assert) => {
        let def;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="id" />
                        </div>
                    </templates>
                </kanban>
            `,
            groupBy: ["state"],
            async mockRPC(_route, { method }) {
                if (method === "read") {
                    await def;
                }
            },
        });

        def = makeDeferred();

        assert.deepEqual(getCardTexts(), ["1", "2", "3", "4"]);

        // Move 3 at end of 1st column
        await dragAndDrop(".o_kanban_group:last-of-type .o_kanban_record", ".o_kanban_group");

        assert.deepEqual(getCardTexts(), ["1", "3", "2", "4"]);

        // Move 4 at end of 1st column
        await dragAndDrop(".o_kanban_group:last-of-type .o_kanban_record", ".o_kanban_group");

        assert.deepEqual(getCardTexts(), ["1", "3", "4", "2"]);

        def.resolve();
        await nextTick();

        assert.deepEqual(getCardTexts(), ["1", "3", "4", "2"]);
    });
});
