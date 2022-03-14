/** @odoo-module **/

import { makeFakeDialogService } from "@web/../tests/helpers/mock_services";
import {
    click,
    dragAndDrop,
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
    triggerEvents,
} from "@web/../tests/helpers/utils";
import {
    getFacetTexts,
    getPagerLimit,
    getPagerValue,
    pagerNext,
    validateSearch,
} from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { KanbanAnimatedNumber } from "@web/views/kanban/kanban_animated_number";
import { KanbanView } from "@web/views/kanban/kanban_view";

const serviceRegistry = registry.category("services");

const { markup } = owl;

// WOWL remove after adapting tests
let testUtils,
    Widget,
    widgetRegistry,
    widgetRegistryOwl,
    FormRenderer,
    AbstractField,
    modalCancel,
    modalOk,
    FieldChar,
    KanbanRenderer,
    fieldRegistry;

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

// Kanban
const reload = async (kanban, params = {}) => {
    kanban.env.searchModel.reload(params);
    kanban.env.searchModel.search();
    await nextTick();
};
const getCard = (cardIndex = 0) =>
    target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")[cardIndex];
const getColumn = (groupIndex = 0) => target.querySelectorAll(".o_kanban_group")[groupIndex];
const getCardTexts = (groupIndex) => {
    const root = groupIndex >= 0 ? getColumn(groupIndex) : target;
    return [...root.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")]
        .map((card) => card.innerText.trim())
        .filter(Boolean);
};
const getCounters = () =>
    [...target.querySelectorAll(".o_kanban_counter_side")].map((counter) => counter.innerText);
const getTooltips = (groupIndex) => {
    const root = groupIndex >= 0 ? getColumn(groupIndex) : target;
    return [...root.querySelectorAll(".o_kanban_counter_progress .progress-bar")]
        .map((card) => card.dataset.tooltip)
        .filter(Boolean);
};

// Record
const createRecord = async () => {
    await click(target, "button.o-kanban-button-new");
};
const quickCreateRecord = async (groupIndex) => {
    await click(getColumn(groupIndex), ".o_kanban_quick_add");
};
const editQuickCreateInput = async (field, value) => {
    await editInput(target, `.o_kanban_quick_create .o_field_widget[name=${field}] input`, value);
};
const validateRecord = async () => {
    await click(target, ".o_kanban_quick_create .o_kanban_add");
};
const editRecord = async () => {
    await click(target, ".o_kanban_quick_create .o_kanban_edit");
};
const discardRecord = async () => {
    await click(target, ".o_kanban_quick_create .o_kanban_cancel");
};
const toggleRecordDropdown = async (recordIndex) => {
    const group = target.querySelectorAll(`.o_kanban_record`)[recordIndex];
    await click(group, ".o_dropdown_kanban .dropdown-toggle");
};

// Column
const createColumn = async () => {
    await click(target, ".o_column_quick_create > .o_quick_create_folded");
};
const editColumnName = async (value) => {
    await editInput(target, ".o_column_quick_create input", value);
};
const validateColumn = async () => {
    await click(target, ".o_column_quick_create .o_kanban_add");
};
const toggleColumnActions = async (columnIndex) => {
    const group = target.querySelectorAll(`.o_kanban_group`)[columnIndex];
    await click(group, ".o_kanban_config .dropdown-toggle");
    const buttons = group.querySelectorAll(".o_kanban_config .dropdown-menu .dropdown-item");
    return (buttonText) => {
        const re = new RegExp(`\\b${buttonText}\\b`, "i");
        const button = [...buttons].find((b) => re.test(b.innerText));
        return click(button);
    };
};
const loadMore = async (columnIndex) => {
    const group = target.querySelectorAll(`.o_kanban_group`)[columnIndex];
    await click(group, ".o_kanban_load_more a");
};

// /!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\
// TODO: do not forget KanbanModel tests
// /!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\/!\

let addDialog;
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
        addDialog = (cls, props) => props.confirm();

        setupViewRegistries();
        serviceRegistry.add(
            "dialog",
            makeFakeDialogService((...args) => addDialog(...args)),
            { force: true }
        );
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
                assert.ok(args.kwargs.context.bin_size, "should not request direct binary payload");
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
            arch: /* xml */ `
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
            assert.expect(11);

            // add active field on partner model and make all records active
            serverData.models.partner.fields.active = {
                string: "Active",
                type: "char",
                default: true,
            };
            addDialog = (cls, props) => {
                assert.step("open-dialog");
                props.confirm();
            };

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban class="o_kanban_test">' +
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
            assert.expect(11);

            // add active field on partner model and make all records active
            serverData.models.partner.fields.active = {
                string: "Active",
                type: "char",
                default: true,
            };
            addDialog = (cls, props) => {
                assert.step("open-dialog");
                props.confirm();
            };

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban class="o_kanban_test" archivable="true">' +
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
            assert.expect(2);

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
                    '<kanban class="o_kanban_test" archivable="false">' +
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

    QUnit.skipWOWL(
        "m2m grouped rendering with active field and archive enabled (archivable true)",
        async (assert) => {
            assert.expect(7);

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
                <kanban class="o_kanban_test" archivable="true">
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
            assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
            assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 2);
            assert.containsN(target, ".o_kanban_group:nth-child(3) .o_kanban_record", 2);

            assert.deepEqual(
                [...target.querySelectorAll(".o_kanban_group")].map((el) =>
                    el.innerText.replace(/\s/g, " ")
                ),
                ["None blork", "gold yopblip", "silver yopgnap"]
            );

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

    QUnit.test("context can be used in kanban template", async (assert) => {
        assert.expect(2);

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

    QUnit.test("pager should be hidden in grouped mode", async (assert) => {
        assert.expect(1);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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
                '<kanban class="o_kanban_test">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            async mockRPC(route, { kwargs }) {
                assert.strictEqual(kwargs.limit, 40, "default limit should be 40 in Kanban");
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
                '<kanban class="o_kanban_test">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            async mockRPC(route, { kwargs }) {
                assert.strictEqual(kwargs.limit, 2);
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
                '<kanban class="o_kanban_test" limit="3">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            async mockRPC(route, { kwargs }) {
                assert.strictEqual(kwargs.limit, 3);
            },
            limit: 2,
        });

        assert.deepEqual(getPagerValue(target), [1, 3]);
        assert.strictEqual(getPagerLimit(target), 4);
    });

    QUnit.test(
        "pager, ungrouped, deleting all records from last page should move to previous page",
        async (assert) => {
            assert.expect(7);

            addDialog = (cls, props) => {
                assert.step("open-dialog");
                props.confirm();
            };

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `<kanban class="o_kanban_test" limit="3">
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

    QUnit.test("create in grouped on m2o", async (assert) => {
        assert.expect(5);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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
        assert.expect(4);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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
        assert.expect(2);

        serverData.models.partner.records[0].category_ids = [6, 7];
        serverData.models.partner.records[3].category_ids = [7];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban class="o_kanban_test">
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

    QUnit.test("quick create record without quick_create_view", async (assert) => {
        assert.expect(15);

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
        assert.expect(18);

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
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "load_views", // form view in quick create
            "onchange", // quick create
            "create", // should perform a create to create the record
            "read", // read the created record
            "onchange", // new quick create
        ]);
    });

    QUnit.test("quick create record in grouped on m2o (no quick_create_view)", async (assert) => {
        assert.expect(13);

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
        assert.expect(14);

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
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "load_views", // form view in quick create
            "onchange", // quick create
            "create", // should perform a create to create the record
            "read", // read the created record
            "onchange", // reopen the quick create automatically
        ]);
    });

    QUnit.test("quick create record with default values and onchanges", async (assert) => {
        assert.expect(10);

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
            "web_read_group", // initial read_group
            "web_search_read", // initial search_read (first column)
            "web_search_read", // initial search_read (second column)
            "load_views", // form view in quick create
            "onchange", // quick create
            "onchange", // onchange due to 'foo' field change
        ]);
    });

    QUnit.test("quick create record with quick_create_view: modifiers", async (assert) => {
        assert.expect(3);

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

    QUnit.test("quick create record and change state in grouped mode", async (assert) => {
        assert.expect(1);

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
            arch: /* xml */ `
                <kanban class="o_kanban_test" on_create="quick_create">
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

    QUnit.skipWOWL("window resize should not change quick create form size", async (assert) => {
        assert.expect(2);

        patchWithCleanup(FormRenderer, {
            start: function () {
                this._super(...arguments);

                window.addEventListener("resize", () => this._applyFormSizeClass());
            },
        });
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

        // click to add an element and cancel the quick creation by pressing ESC
        await quickCreateRecord();

        const quickCreate = target.querySelector(".o_kanban_quick_create");
        assert.hasClass(quickCreate.querySelector(".o_form_view"), "o_xxs_form_view");

        // trigger window resize explicitly to call _applyFormSizeClass
        await triggerEvent(window, "", "resize");

        assert.hasClass(quickCreate.querySelector(".o_form_view"), "o_xxs_form_view");
    });

    QUnit.test(
        "quick create record: cancel and validate without using the buttons",
        async (assert) => {
            assert.expect(8);

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
            await click(target, ".o_kanban_group:first-child .o_kanban_record:last-child");
            assert.containsNone(
                target,
                ".o_kanban_quick_create",
                "the quick create should be destroyed when the user clicks outside"
            );

            // click to input and drag the mouse outside, should not cancel the quick creation
            await quickCreateRecord();
            await triggerEvent(target, ".o_kanban_quick_create input", "mousedown");
            await click(target, ".o_kanban_group:first-child .o_kanban_record:last-child");
            assert.containsOnce(
                target,
                ".o_kanban_quick_create",
                "the quick create should not have been destroyed after clicking outside"
            );

            // click to really add an element
            await quickCreateRecord();
            await editQuickCreateInput("foo", "new partner");

            // clicking outside should no longer destroy the quick create as it is dirty
            await click(target, ".o_kanban_group:first-child .o_kanban_record:last-child");
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
            assert.deepEqual(getCardTexts(0), ["blip", "new partner"]);
        }
    );

    QUnit.test("quick create record: validate with ENTER", async (assert) => {
        assert.expect(3);

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
        assert.expect(9);

        serverData.views["partner,some_view_ref,form"] =
            "<form>" + '<field name="foo"/>' + '<field name="int_field"/>' + "</form>";

        let prom = makeDeferred();

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
        assert.expect(9);

        serverData.views["partner,some_view_ref,form"] =
            "<form>" + '<field name="foo"/>' + '<field name="int_field"/>' + "</form>";

        let prom = makeDeferred();
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
            let prom = makeDeferred();
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
            let prom = makeDeferred();
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
        assert.expect(6);

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
        assert.expect(11);

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
        await click(target, ".o_kanban_group:first-child .o_kanban_record:last-child");
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

    QUnit.skipWOWL("quick create record: cancel when modal is opened", async (assert) => {
        assert.expect(3);

        serverData.views["partner,some_view_ref,form"] =
            "<form>" + '<field name="product_id"/>' + "</form>";

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
            groupBy: ["bar"],
        });

        // click to add an element
        await quickCreateRecord();
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "should have open the quick create widget"
        );

        await editInput(target, ".o_kanban_quick_create input", "test");
        await triggerEvents(target, ".o_kanban_quick_create input", ["keyup", "blur"]);

        // When focusing out of the many2one, a modal to add a 'product' will appear.
        // The following assertions ensures that a click on the body element that has 'modal-open'
        // will NOT close the quick create.
        // This can happen when the user clicks out of the input because of a race condition between
        // the focusout of the m2o and the global 'click' handler of the quick create.
        // Check odoo/odoo#61981 for more details.
        const $body = target.querySelectorel.closest("body");
        assert.hasClass($body, "modal-open", "modal should be opening after m2o focusout");
        await click($body);
        assert.containsOnce(
            target,
            ".o_kanban_quick_create",
            "quick create should stay open while modal is opening"
        );
    });

    QUnit.test("quick create record: cancel when dirty", async (assert) => {
        assert.expect(7);

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
        assert.expect(6);

        let newRecordID;
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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
        });

        patchWithCleanup(kanban.env.services.action, {
            async switchView(viewType, props) {
                assert.strictEqual(viewType, "form");
                assert.strictEqual(props.resId, newRecordID);
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
        assert.expect(6);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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
        assert.expect(6);

        let prom = makeDeferred();
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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

    QUnit.skipWOWL("quick create record fail in grouped by many2one", async (assert) => {
        assert.expect(8);

        serverData.views["partner,false,form"] =
            '<form string="Partner">' +
            '<field name="product_id"/>' +
            '<field name="foo"/>' +
            "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (args.method === "name_create") {
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: $.Event(),
                    });
                }
            },
        });

        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "there should be 2 records in first column"
        );

        await createRecord(); // Click on 'Create'

        assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_quick_create");

        await editQuickCreateInput("foo", "test");
        await validateRecord();

        assert.strictEqual(
            $(".modal .o_form_view.o_form_editable").length,
            1,
            "a form view dialog should have been opened (in edit)"
        );
        assert.strictEqual(
            $(".modal .o_field_many2one input").value,
            "hello",
            "the correct product_id should already be set"
        );

        // specify a name and save
        await editInput(document, ".modal input[name=foo]", "test");
        await click(document, ".modal .btn-primary");

        assert.containsNone(document, ".modal", "the modal should be closed");
        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            3,
            "there should be 3 records in first column"
        );
        const firstRecord = target.querySelector(
            ".o_kanban_group:first-child .o_kanban_record:first-child"
        );
        assert.strictEqual(
            firstRecord.innerText,
            "test",
            "the first record of the first column should be the new one"
        );
        assert.containsOnce(
            target,
            ".o_kanban_quick_create:not(.o_disabled)",
            "quick create should be enabled"
        );
    });

    QUnit.skipWOWL("quick create record is re-enabled after discard on failure", async (assert) => {
        assert.expect(4);

        serverData.views["partner,false,form"] =
            '<form string="Partner">' +
            '<field name="product_id"/>' +
            '<field name="foo"/>' +
            "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (args.method === "name_create") {
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: $.Event(),
                    });
                }
            },
        });

        await createRecord();

        assert.containsOnce(target, ".o_kanban_quick_create", "should have a quick create widget");

        await editQuickCreateInput("display_name", "test");

        assert.strictEqual(
            $(".modal .o_form_view.o_form_editable").length,
            1,
            "a form view dialog should have been opened (in edit)"
        );

        await testUtils.modal.clickButton("Discard");

        assert.strictEqual($(".modal").length, 0, "the modal should be closed");
        assert.strictEqual(
            target.querySelector(".o_kanban_quick_create:not(.o_disabled)").length,
            1,
            "quick create widget should have been re-enabled"
        );
    });

    QUnit.skipWOWL("quick create record fails in grouped by char", async (assert) => {
        assert.expect(7);

        serverData.views["partner,false,form"] = "<form>" + '<field name="foo"/>' + "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            async mockRPC(route, args) {
                if (args.method === "name_create") {
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: $.Event(),
                    });
                }
                if (args.method === "create") {
                    assert.deepEqual(
                        args.args[0],
                        { foo: "yop" },
                        "should write the correct value for foo"
                    );
                    assert.deepEqual(
                        args.kwargs.context,
                        { default_foo: "yop", default_name: "test" },
                        "should send the correct default value for foo"
                    );
                }
            },
            groupBy: ["foo"],
        });

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "there should be 1 record in first column"
        );

        await quickCreateRecord();
        await editQuickCreateInput("foo", "test");
        await validateRecord();

        assert.strictEqual(
            $(".modal .o_form_view.o_form_editable").length,
            1,
            "a form view dialog should have been opened (in edit)"
        );
        assert.strictEqual(
            $(".modal .o_field_widget[name=foo]").value,
            "yop",
            "the correct default value for foo should already be set"
        );
        await testUtils.modal.clickButton("Save");

        assert.strictEqual($(".modal").length, 0, "the modal should be closed");
        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "there should be 2 records in first column"
        );
    });

    QUnit.skipWOWL("quick create record fails in grouped by selection", async (assert) => {
        assert.expect(7);

        serverData.views["partner,false,form"] = "<form>" + '<field name="state"/>' + "</form>";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="state"/></div>' +
                "</t></templates>" +
                "</kanban>",
            async mockRPC(route, args) {
                if (args.method === "name_create") {
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: $.Event(),
                    });
                }
                if (args.method === "create") {
                    assert.deepEqual(
                        args.args[0],
                        { state: "abc" },
                        "should write the correct value for state"
                    );
                    assert.deepEqual(
                        args.kwargs.context,
                        { default_state: "abc", default_name: "test" },
                        "should send the correct default value for state"
                    );
                }
            },
            groupBy: ["state"],
        });

        assert.containsOnce(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            "there should be 1 record in first column"
        );

        await quickCreateRecord();
        await editQuickCreateInput("foo", "test");
        await validateRecord();

        assert.strictEqual(
            $(".modal .o_form_view.o_form_editable").length,
            1,
            "a form view dialog should have been opened (in edit)"
        );
        assert.strictEqual(
            $(".modal .o_field_widget[name=state]").value,
            '"abc"',
            "the correct default value for state should already be set"
        );

        await testUtils.modal.clickButton("Save");

        assert.strictEqual($(".modal").length, 0, "the modal should be closed");
        assert.containsN(
            target,
            ".o_kanban_group:first-child .o_kanban_record",
            2,
            "there should be 2 records in first column"
        );
    });

    QUnit.test("quick create record in empty grouped kanban", async (assert) => {
        assert.expect(3);

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
        assert.expect(6);

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="display_name"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["date"],
        });

        patchWithCleanup(kanban.env.services.action, {
            async switchView(viewType, props) {
                assert.deepEqual([props.resId, viewType], [false, "form"]);
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
    });

    QUnit.test(
        "quick create record if grouped on date(time) field with attribute allow_group_range_value: true",
        async (assert) => {
            assert.expect(6);

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
            assert.expect(3);

            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban class="o_kanban_test" on_create="quick_create">' +
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
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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
        assert.expect(10);

        let prom = makeDeferred();
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
        assert.expect(6);

        serverData.views["partner,some_view_ref,form"] = '<form><field name="int_field"/></form>';

        let prom = makeDeferred();
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
            async mockRPC(route, { method }) {
                if (method === "load_views") {
                    await prom;
                }
            },
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsNone(target, ".o_column_folded");

        // click to quick create a new record in the first column (this operation is delayed)
        await quickCreateRecord();

        assert.containsNone(target, ".o_form_view");

        // click to fold the first column
        const clickColumnAction = await toggleColumnActions(0);
        await clickColumnAction("Fold");

        assert.containsOnce(target, ".o_column_folded");

        prom.resolve();
        await nextTick();

        assert.containsNone(target, ".o_form_view");
        assert.containsOnce(target, ".o_column_folded");
    });

    QUnit.test(
        "quick create record: open on a column while another column has already one",
        async (assert) => {
            assert.expect(6);

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
        assert.expect(12);

        serverData.models.partner.records[0].category_ids = [6, 7];
        serverData.models.partner.records[1].category_ids = [7, 8];
        serverData.models.category.records.push({
            id: 8,
            name: "hello",
            color: 0,
        });

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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
        });

        patchWithCleanup(kanban.env.services.action, {
            async switchView(viewType, props) {
                assert.deepEqual(
                    [props.resId, viewType],
                    [1, "form"],
                    "should trigger an event to open the clicked record in a form view"
                );
            },
        });

        assert.containsN(
            getCard(0),
            ".o_field_many2manytags .o_tag",
            2,
            "first record should contain 2 tags"
        );
        assert.containsOnce(getCard(0), ".o_tag.o_tag_color_2", "first tag should have color 2");
        assert.verifySteps(
            ["/web/dataset/call_kw/partner/web_search_read", "/web/dataset/call_kw/category/read"],
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
            ".o_kanban_record:first-child .o_field_many2manytags .o_tag",
            2,
            "first record should still contain only 2 tags"
        );

        // click on a tag (should trigger switch_view)
        await click(target, ".o_kanban_record:first-child .o_tag:first-child");
    });

    QUnit.test("Do not open record when clicking on `a` with `href`", async (assert) => {
        assert.expect(5);

        serverData.models.partner.records = [{ id: 1, foo: "yop" }];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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

        const kanban = await makeView({
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
        });

        patchWithCleanup(kanban.env.services.action, {
            async switchView(viewType, props) {
                assert.deepEqual(
                    [props.resId, viewType],
                    [1, "form"],
                    "should trigger an event to open the form view"
                );
            },
        });

        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

        await click(target, ".oe_kanban_global_click:first-child .o_field_monetary[name=salary]");
    });

    QUnit.test("o2m loaded in only one batch", async (assert) => {
        assert.expect(9);

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
                '<kanban class="o_kanban_test">' +
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
        assert.expect(9);

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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

    QUnit.skipWOWL("fetch reference in only one batch", async (assert) => {
        assert.expect(9);

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
            arch:
                '<kanban class="o_kanban_test">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click">' +
                '<field name="ref_product"/>' +
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
        assert.expect(8);

        let prom = Promise.resolve();
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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
        assert.expect(9);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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

    QUnit.test("drag and drop a record, grouped by selection", async (assert) => {
        assert.expect(7);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
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
        assert.expect(14);

        serverData.models.partner.fields.foo.readonly = true;
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                "<templates>" +
                '<t t-name="kanban-box"><div>' +
                '<field name="foo"/>' +
                '<field name="state" readonly="1"/>' +
                "</div></t>" +
                "</templates>" +
                "</kanban>",
            groupBy: ["state"],
            async mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    return true;
                }
                if (args.model === "partner" && args.method === "write") {
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

        assert.deepEqual(getCardTexts(0), ["blipdef", "blipghi"]);

        // second record of first column moved at first place
        await dragAndDrop(
            ".o_kanban_group:first-child .o_kanban_record:last-child",
            ".o_kanban_group:first-child .o_kanban_record"
        );

        // should still be able to resequence
        assert.deepEqual(getCardTexts(0), ["blipghi", "blipdef"]);
    });

    QUnit.test("prevent drag and drop if grouped by date/datetime field", async (assert) => {
        assert.expect(10);

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
                '<kanban class="o_kanban_test">' +
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
        assert.expect(13);

        serverData.models.partner.records[0].category_ids = [6, 7];
        serverData.models.partner.records[3].category_ids = [7];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban class="o_kanban_test">
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
                            assert.deepEqual(args[1], { datetime: "2017-02-28 23:59:59" });
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

    QUnit.test(
        "completely prevent drag and drop if records_draggable set to false",
        async (assert) => {
            assert.expect(8);

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban class="o_kanban_test" records_draggable="false">' +
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
                ".o_kanban_group:first-child .o_kanban_record:last-child"
            );

            assert.deepEqual(
                getCardTexts(),
                ["yop", "gnap", "blip", "blip"],
                "Records should not have moved"
            );
        }
    );

    QUnit.test("prevent drag and drop of record if onchange fails", async (assert) => {
        assert.expect(4);

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
                '<kanban class="o_kanban_test" default_group_by="bar">' +
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
        assert.expect(3);

        patchWithCleanup(KanbanView, { searchMenuTypes: ["filter", "favorite"] });

        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter string="candle" name="itsName" context="{'group_by': 'foo'}"/>
            </search>
        `;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <kanban class="o_kanban_test" default_group_by="bar">
                    <field name="bar"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>
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
    });

    QUnit.test("kanban view with create=False", async (assert) => {
        assert.expect(1);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" create="0">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
        });

        assert.containsNone(target, ".o-kanban-button-new");
    });

    QUnit.skipWOWL("clicking on a link triggers correct event", async (assert) => {
        assert.expect(2);

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                '<div><a type="edit">Edit</a></div>' +
                "</t></templates></kanban>",
        });

        patchWithCleanup(kanban.env.services.action, {
            async switchView(viewType, props) {
                assert.strictEqual(viewType, "form");
                assert.deepEqual(props, {
                    resId: 1,
                    // FIXME: no more edit mode or resModel specified here?
                    // mode: "edit",
                    // resModel: "partner",
                });
            },
        });

        await click(getCard(0), "a");
    });

    QUnit.test("environment is updated when (un)folding groups", async (assert) => {
        assert.expect(3);

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

    QUnit.skipWOWL("create a column in grouped on m2o", async (assert) => {
        assert.expect(14);

        let nbRPCs = 0;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, { method }) {
                nbRPCs++;
                if (method === "name_create") {
                    assert.step("name_create");
                }
                //Create column will call resequence to set column order
                if (route === "/web/dataset/resequence") {
                    assert.step("resequence");
                    return true;
                }
            },
        });
        assert.containsOnce(target, ".o_column_quick_create", "should have a quick create column");
        assert.notOk(
            target.querySelector(".o_column_quick_create input").is(":visible"),
            "the input should not be visible"
        );

        await createColumn();

        assert.ok(
            target.querySelector(".o_column_quick_create input").is(":visible"),
            "the input should be visible"
        );

        // discard the column creation and click it again
        await target.querySelector(".o_column_quick_create input").trigger(
            $.Event("keydown", {
                keyCode: $.ui.keyCode.ESCAPE,
                which: $.ui.keyCode.ESCAPE,
            })
        );
        assert.notOk(
            target.querySelector(".o_column_quick_create input").is(":visible"),
            "the input should not be visible after discard"
        );

        await createColumn();
        assert.ok(
            target.querySelector(".o_column_quick_create input").is(":visible"),
            "the input should be visible"
        );

        await editColumnName("new value");
        await validateColumn();

        assert.strictEqual(
            target.querySelector(".o_kanban_group:last-child span:contains(new value)").length,
            1,
            "the last column should be the newly created one"
        );
        assert.ok(
            !isNaN(target.querySelector(".o_kanban_group:last-child").dataset.id),
            "the created column should have the correct id"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_group:last-child"),
            "o_column_folded",
            "the created column should not be folded"
        );

        // fold and unfold the created column, and check that no RPC is done (as there is no record)
        nbRPCs = 0;
        const clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Fold");

        assert.hasClass(
            target.querySelector(".o_kanban_group:last-child"),
            "o_column_folded",
            "the created column should now be folded"
        );
        await click(target, ".o_kanban_group:last-child");
        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_group:last-child"),
            "o_column_folded"
        );
        assert.strictEqual(nbRPCs, 0, "no rpc should have been done when folding/unfolding");

        // quick create a record
        await createRecord();
        assert.hasClass(
            target.querySelector(".o_kanban_group:first-child > div:nth(1)"),
            "o_kanban_quick_create",
            "clicking on create should open the quick_create in the first column"
        );
    });

    QUnit.skipWOWL("auto fold group when reach the limit", async (assert) => {
        assert.expect(9);

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
                '<kanban class="o_kanban_test">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (args.method === "web_read_group") {
                    return this._super.apply(this, arguments).then(function (result) {
                        result.groups[2].__fold = true;
                        result.groups[8].__fold = true;
                        return result;
                    });
                }
                return this._super(route, args);
            },
        });

        // we look if column are fold/unfold according what is expected
        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_group:nth-child(2)"),
            "o_column_folded"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_group:nth-child(4)"),
            "o_column_folded"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_kanban_group:nth-child(10)"),
            "o_column_folded"
        );
        assert.hasClass(target.querySelector(".o_kanban_group:nth-child(3)"), "o_column_folded");
        assert.hasClass(target.querySelector(".o_kanban_group:nth-child(9)"), "o_column_folded");

        // we look if columns are actually fold after we reached the limit
        assert.hasClass(target.querySelector(".o_kanban_group:nth-child(13)"), "o_column_folded");
        assert.hasClass(target.querySelector(".o_kanban_group:nth-child(14)"), "o_column_folded");

        // we look if we have the right count of folded/unfolded column
        assert.containsN(target, ".o_kanban_group:not(.o_column_folded)", 10);
        assert.containsN(target, ".o_kanban_group.o_column_folded", 4);
    });

    QUnit.skipWOWL("hide and display help message (ESC) in kanban quick create", async (assert) => {
        assert.expect(2);

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
        assert.ok(
            target.querySelector(".o_discard_msg").is(":visible"),
            "the ESC to discard message is visible"
        );

        // click outside the column (to lose focus)
        await testUtils.dom.clickFirst(target, ".o_kanban_header");
        assert.notOk(
            target.querySelector(".o_discard_msg").is(":visible"),
            "the ESC to discard message is no longer visible"
        );
    });

    QUnit.skipWOWL("delete a column in grouped on m2o", async (assert) => {
        assert.expect(37);

        testUtils.mock.patch(KanbanRenderer, {
            _renderGrouped: function () {
                this._super.apply(this, arguments);
                // set delay and revert animation time to 0 so dummy drag and drop works
                if (this.el.querySelectorel.sortable("instance")) {
                    this.el.querySelectorel.sortable("option", { delay: 0, revert: 0 });
                }
            },
        });

        let resequencedIDs;

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                if (route === "/web/dataset/resequence") {
                    resequencedIDs = args.ids;
                    assert.strictEqual(
                        _.reject(args.ids, !isNaN).length,
                        0,
                        "column resequenced should be existing records with IDs"
                    );
                    return true;
                }
                if (args.method) {
                    assert.step(args.method);
                }
            },
        });

        // check the initial rendering
        assert.containsN(target, ".o_kanban_group", 2, "should have two columns");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:first-child").dataset.id,
            3,
            'first column should be [3, "hello"]'
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:last-child").dataset.id,
            5,
            'second column should be [5, "xmo"]'
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:last-child .o_column_title").innerText,
            "xmo",
            "second column should have correct title"
        );
        assert.containsN(
            target,
            ".o_kanban_group:last-child .o_kanban_record",
            2,
            "second column should have two records"
        );

        // check available actions in kanban header's config dropdown
        assert.ok(
            target.querySelector(".o_kanban_group:first-child .o_kanban_toggle_fold").length,
            "should be able to fold the column"
        );
        assert.ok(
            target.querySelector(".o_kanban_group:first-child .o_column_edit").length,
            "should be able to edit the column"
        );
        assert.ok(
            target.querySelector(".o_kanban_group:first-child .o_column_delete").length,
            "should be able to delete the column"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_column_archive_records").length,
            "should not be able to archive all the records"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_column_unarchive_records").length,
            "should not be able to restore all the records"
        );

        // delete second column (first cancel the confirm request, then confirm)
        let clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Delete");

        assert.containsOnce(target, ".modal", "a confirm modal should be displayed");

        await modalCancel(); // click on cancel

        assert.strictEqual(
            target.querySelector(".o_kanban_group:last-child").dataset.id,
            5,
            'column [5, "xmo"] should still be there'
        );
        clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Delete");

        assert.containsOnce(target, ".modal", "a confirm modal should be displayed");

        await modalOk(); // click on confirm

        assert.strictEqual(
            target.querySelector(".o_kanban_group:last-child").dataset.id,
            3,
            'last column should now be [3, "hello"]'
        );
        assert.containsN(target, ".o_kanban_group", 2, "should still have two columns");
        assert.ok(
            isNaN(target.querySelector(".o_kanban_group:first-child").dataset.id),
            "first column should have no id (Undefined column)"
        );
        // check available actions on 'Undefined' column
        assert.ok(
            target.querySelector(".o_kanban_group:first-child .o_kanban_toggle_fold").length,
            "should be able to fold the column"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_column_delete").length,
            "Undefined column could not be deleted"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_column_edit").length,
            "Undefined column could not be edited"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_column_archive_records").length,
            "Records of undefined column could not be archived"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_column_unarchive_records").length,
            "Records of undefined column could not be restored"
        );
        assert.verifySteps(["web_read_group", "unlink", "web_read_group"]);
        assert.strictEqual(
            kanban.renderer.widgets.length,
            2,
            "the old widgets should have been correctly deleted"
        );

        // test column drag and drop having an 'Undefined' column
        await testUtils.dom.dragAndDrop(
            target.querySelector(".o_column_title:first-child"),
            target.querySelector(".o_column_title:last"),
            { position: "right" }
        );
        assert.strictEqual(
            resequencedIDs,
            undefined,
            "resequencing require at least 2 not Undefined columns"
        );
        await createColumn();
        await editColumnName("once third column");
        await validateColumn();

        const newColumnID = target.querySelector(".o_kanban_group:last-child").dataset.id;
        await testUtils.dom.dragAndDrop(
            target.querySelector(".o_column_title:first-child"),
            target.querySelector(".o_column_title:last"),
            { position: "right" }
        );
        assert.deepEqual(
            [3, newColumnID],
            resequencedIDs,
            "moving the Undefined column should not affect order of other columns"
        );
        await testUtils.dom.dragAndDrop(
            target.querySelector(".o_column_title:first-child"),
            target.querySelector(".o_column_title:nth(1)"),
            { position: "right" }
        );
        await nextTick(); // wait for resequence after drag and drop
        assert.deepEqual(
            [newColumnID, 3],
            resequencedIDs,
            "moved column should be resequenced accordingly"
        );
        assert.verifySteps(["name_create", "read", "read", "read"]);
        testUtils.mock.unpatch(KanbanRenderer);
    });

    QUnit.skipWOWL("create a column, delete it and create another one", async (assert) => {
        assert.expect(5);

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

        assert.containsN(target, ".o_kanban_group", 2, "should have two columns");

        await createColumn();
        await editColumnName("new column 1");
        await validateColumn();

        assert.containsN(target, ".o_kanban_group", 3, "should have two columns");

        const clickColumnAction = await toggleColumnActions(1);
        await clickColumnAction("Delete");
        await modalOk();

        assert.containsN(target, ".o_kanban_group", 2, "should have twos columns");

        await createColumn();
        await editColumnName("new column 2");
        await validateColumn();

        assert.containsN(target, ".o_kanban_group", 3, "should have three columns");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:last-child span:contains(new column 2)").length,
            1,
            "the last column should be the newly created one"
        );
    });

    QUnit.skipWOWL("edit a column in grouped on m2o", async (assert) => {
        assert.expect(12);

        serverData.views["product,false,form"] =
            '<form string="Product"><field name="display_name"/></form>';

        let nbRPCs = 0;
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            async mockRPC(route, args) {
                nbRPCs++;
                return this._super(route, args);
            },
        });
        assert.strictEqual(
            target.querySelector(".o_kanban_group[data-id=5] .o_column_title").innerText,
            "xmo",
            'title of the column should be "xmo"'
        );

        // edit the title of column [5, 'xmo'] and close without saving
        let clickColumnAction = await toggleColumnActions(4);
        await clickColumnAction("Edit");

        assert.containsOnce(
            document.body,
            ".modal .o_form_editable",
            "a form view should be open in a modal"
        );
        assert.strictEqual(
            document.querySelector(".modal .o_form_editable input").value,
            "xmo",
            'the name should be "xmo"'
        );
        await editInput(document, ".modal .o_form_editable input", "ged"); // change the value
        nbRPCs = 0;
        await click(document, ".modal-header .close");
        assert.containsNone(document.body, ".modal");
        assert.strictEqual(
            target.querySelector(".o_kanban_group[data-id=5] .o_column_title").innerText,
            "xmo",
            'title of the column should still be "xmo"'
        );
        assert.strictEqual(nbRPCs, 0, "no RPC should have been done");

        // edit the title of column [5, 'xmo'] and discard
        clickColumnAction = await toggleColumnActions(4);
        await clickColumnAction("Edit");
        await editInput(document, ".modal .o_form_editable input", "ged"); // change the value
        nbRPCs = 0;
        await click(document, ".model .btn-secondary");
        assert.containsNone(document.body, ".modal");
        assert.strictEqual(
            target.querySelector(".o_kanban_group[data-id=5] .o_column_title").innerText,
            "xmo",
            'title of the column should still be "xmo"'
        );
        assert.strictEqual(nbRPCs, 0, "no RPC should have been done");

        // edit the title of column [5, 'xmo'] and save
        clickColumnAction = await toggleColumnActions(4);
        await clickColumnAction("Edit");
        await editInput(document, ".modal .o_form_editable input", "ged"); // change the value
        nbRPCs = 0;
        await click(document, ".modal .btn-primary"); // click on save
        assert.containsNone(document, ".modal", "the modal should be closed");
        assert.strictEqual(
            target.querySelector(".o_kanban_group[data-id=5] .o_column_title").innerText,
            "ged",
            'title of the column should be "ged"'
        );
        assert.strictEqual(nbRPCs, 4, "should have done 1 write, 1 read_group and 2 search_read");
    });

    QUnit.skipWOWL("edit a column propagates right context", async (assert) => {
        assert.expect(4);

        serverData.views["product,false,form"] =
            '<form string="Product"><field name="display_name"/></form>';

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test" on_create="quick_create">' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["product_id"],
            session: { user_context: { lang: "brol" } },
            async mockRPC(route, args) {
                let context;
                if (route === "web_search_read" && args.model === "partner") {
                    context = args.context;
                    assert.strictEqual(
                        context.lang,
                        "brol",
                        "lang is present in context for partner operations"
                    );
                }
                if (args.model === "product") {
                    context = args.kwargs.context;
                    assert.strictEqual(
                        context.lang,
                        "brol",
                        "lang is present in context for product operations"
                    );
                }
            },
        });
        const clickColumnAction = await toggleColumnActions(4);
        await clickColumnAction("Edit");
    });

    QUnit.test("quick create column should be opened if there is no column", async (assert) => {
        assert.expect(3);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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

    // WOWL Fix typo in test name before merge
    QUnit.test(
        "quick create column should not be closed on widnow click if there is no column",
        async (assert) => {
            assert.expect(4);

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                <kanban class="o_kanban_test">
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
        assert.expect(10);

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

    QUnit.test("quick create column and examples", async (assert) => {
        assert.expect(12);

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
                    description: markup(`A <b>fantastic</b> description.`),
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

        assert.strictEqual(
            $(".modal .o_kanban_examples_dialog").length,
            1,
            "should have open the examples dialog"
        );
        assert.strictEqual(
            $(".modal .o_kanban_examples_dialog_nav li").length,
            2,
            "should have two examples (in the menu)"
        );
        assert.strictEqual(
            target.querySelector(".modal .o_kanban_examples_dialog_nav").innerText,
            "A first example\nA second example",
            "example names should be correct"
        );
        assert.strictEqual(
            $(".modal .o_kanban_examples_dialog_content .tab-pane").length,
            2,
            "should have two examples"
        );

        const $panes = $(".modal .o_kanban_examples_dialog_content .tab-pane");
        const $firstPane = $panes.eq(0);
        assert.strictEqual(
            $firstPane.find(".o_kanban_examples_group").length,
            3,
            "there should be 3 stages in the first example"
        );
        assert.strictEqual(
            $firstPane.find("h6").text(),
            "Column 1Column 2Column 3",
            "column titles should be correct"
        );
        assert.strictEqual(
            $firstPane.find(".o_kanban_examples_description").html().trim(),
            "A weak description.",
            "An escaped description should be displayed"
        );

        const $secondPane = $panes.eq(1);
        assert.strictEqual(
            $secondPane.find(".o_kanban_examples_group").length,
            2,
            "there should be 2 stages in the second example"
        );
        assert.strictEqual(
            $secondPane.find("h6").text(),
            "Col 1Col 2",
            "column titles should be correct"
        );
        assert.strictEqual(
            $secondPane.find(".o_kanban_examples_description").html().trim(),
            "A <b>fantastic</b> description.",
            "A formatted description should be displayed."
        );
    });

    QUnit.test("quick create column's apply button's display text", async (assert) => {
        assert.expect(1);

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
            assert.expect(4);

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
            assert.expect(4);

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
            assert.expect(3);

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
            assert.expect(3);

            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban class="o_kanban_test" on_create="quick_create">' +
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
        assert.expect(4);

        // add active field on partner model to have archive option
        serverData.models.partner.fields.active = {
            string: "Active",
            type: "boolean",
            default: true,
        };
        // remove last records to have only one column
        serverData.models.partner.records = serverData.models.partner.records.slice(0, 3);
        addDialog = (cls, props) => {
            assert.step("open-dialog");
            props.confirm();
        };
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `<kanban class="o_kanban_test">
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
        assert.expect(3);

        const records = serverData.models.partner.records;

        serverData.models.partner.records = [];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                "<div>" +
                '<t t-esc="record.foo.value"/>' +
                '<field name="foo"/>' +
                "</div>" +
                "</t></templates></kanban>",
            noContentHelp: markup('<p class="hello">click to add a partner</p>'),
        });

        assert.containsOnce(target, ".o_view_nocontent", "should display the no content helper");

        assert.strictEqual(
            target.querySelector(".o_view_nocontent p.hello").innerText,
            "click to add a partner",
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
        assert.expect(2);

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
        assert.expect(4);

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
        assert.expect(3);

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
        assert.expect(2);

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
        assert.expect(2);

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
        assert.expect(2);

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
            assert.expect(1);

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
        "nocontent helper for grouped kanban with no records with no group_create",
        async (assert) => {
            assert.expect(4);

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

    QUnit.test("empty grouped kanban with sample data and no columns", async (assert) => {
        assert.expect(3);

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
        assert.expect(11);

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
        assert.expect(12);

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
        assert.expect(5);

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
        assert.expect(6);

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
        assert.expect(6);

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
            target.querySelectorAll(".o_field_many2manytags .o_tag").length >= 1,
            "there should be tags"
        );

        assert.verifySteps(["web_read_group"], "should not read the tags");
    });

    QUnit.test("sample data does not change after reload with sample data", async (assert) => {
        assert.expect(4);

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
        assert.expect(5);

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
        assert.expect(6);

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
        assert.expect(5);

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
        assert.expect(8);

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
        assert.expect(5);

        serverData.models.partner.records = [];

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
                let result = await performRpc(...arguments);
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
            assert.expect(9);

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
        assert.expect(2);

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `<kanban class="o_kanban_test"><templates><t t-name="kanban-box">
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
        assert.expect(2);

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

    QUnit.test("button executes action and reloads", async (assert) => {
        assert.expect(7);

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><div t-name="kanban-box">' +
                '<field name="foo"/>' +
                '<button type="object" name="a1" class="a1"/>' +
                "</div></templates>" +
                "</kanban>",
            async mockRPC(route) {
                assert.step(route);
            },
        });
        assert.verifySteps(["/web/dataset/call_kw/partner/web_search_read"]);

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
        await click(target.querySelector("button.a1"));
        assert.strictEqual(count, 1, "should have triggered a execute action");

        assert.verifySteps(
            ["/web/dataset/call_kw/partner/web_search_read"],
            "the records should be reloaded after executing a button action"
        );

        await click(target.querySelector("button.a1"));
        assert.strictEqual(count, 1, "double-click on kanban actions should be debounced");
    });

    QUnit.test("button executes action and check domain", async (assert) => {
        assert.expect(2);

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
        assert.expect(1);

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

    QUnit.test("rendering date and datetime", async (assert) => {
        assert.expect(2);

        serverData.models.partner.records[0].date = "2017-01-25";
        serverData.models.partner.records[1].datetime = "2016-12-12 10:55:05";

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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

        patchWithCleanup(luxon.Settings, { defaultLocale: "en" });

        assert.strictEqual(getCard(0).querySelector(".date").innerText, "Wed Jan 25 2017");
        assert.strictEqual(getCard(1).querySelector(".datetime").innerText, "Mon Dec 12 2016");
    });

    QUnit.test("evaluate conditions on relational fields", async (assert) => {
        assert.expect(3);

        serverData.models.partner.records[0].product_id = false;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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

    QUnit.skipWOWL("resequence columns in grouped by m2o", async (assert) => {
        assert.expect(6);

        let envIDs = [1, 3, 2, 4]; // the ids that should be in the environment during this test
        const kanban = await makeView({
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

        assert.hasClass(
            target.querySelector(".o_kanban_renderer"),
            "o_kanban_sortable",
            "columns should be sortable"
        );
        assert.containsN(target, ".o_kanban_group", 2, "should have two columns");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:first-child").dataset.id,
            3,
            "first column should be id 3 before resequencing"
        );
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // there is a 100ms delay on the d&d feature (jquery sortable) for
        // kanban columns, making it hard to test. So we rather bypass the d&d
        // for this test, and directly call the event handler
        envIDs = [2, 4, 1, 3]; // the columns will be inverted
        kanban._onResequenceColumn({ data: { ids: [5, 3] } });

        await nextTick(); // wait for resequencing before re-rendering
        await reload(kanban, {}, { reload: false }); // re-render without reloading

        assert.strictEqual(
            target.querySelector(".o_kanban_group:first-child").dataset.id,
            5,
            "first column should be id 5 after resequencing"
        );
        assert.deepEqual(kanban.exportState().resIds, envIDs);
    });

    QUnit.skipWOWL("properly evaluate more complex domains", async (assert) => {
        assert.expect(1);

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
                "<button type=\"object\" attrs=\"{'invisible':['|', ('bar','=',True), ('category_ids', '!=', [])]}\" class=\"btn btn-primary float-right\" name=\"arbitrary\">Join</button>" +
                "</div>" +
                "</t>" +
                "</templates>" +
                "</kanban>",
        });

        assert.containsOnce(
            target,
            "button.oe_kanban_action_button",
            "only one button should be visible"
        );
    });

    QUnit.test("edit the kanban color with the colorpicker", async (assert) => {
        assert.expect(6);

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
                '<a class="dropdown-toggle o-no-caret btn" data-toggle="dropdown" href="#">' +
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

    QUnit.skipWOWL("load more records in column", async (assert) => {
        assert.expect(13);

        let envIDs = [1, 2, 4]; // the ids that should be in the environment during this test
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
            limit: 2,
            async mockRPC(route, args) {
                if (route === "web_search_read") {
                    assert.step(args.limit + " - " + args.offset);
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").length,
            2,
            "there should be 2 records in the column"
        );
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // load more
        envIDs = [1, 2, 3, 4]; // id 3 will be loaded
        await click(
            target.querySelector(".o_kanban_group:nth-child(2)").find(".o_kanban_load_more")
        );

        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").length,
            3,
            "there should now be 3 records in the column"
        );
        assert.verifySteps(
            ["2 - undefined", "2 - undefined", "2 - 2"],
            "the records should be correctly fetched"
        );
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // reload
        await reload(kanban);

        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").length,
            3,
            "there should still be 3 records in the column after reload"
        );
        assert.deepEqual(kanban.exportState().resIds, envIDs);
        assert.verifySteps(["4 - undefined", "2 - undefined"]);
    });

    QUnit.skipWOWL("load more records in column with x2many", async (assert) => {
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
            arch:
                "<kanban>" +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="category_ids"/>' +
                '<field name="foo"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            groupBy: ["bar"],
            limit: 2,
            async mockRPC(route, args) {
                if (args.model === "category" && args.method === "read") {
                    assert.step(String(args.args[0]));
                }
                if (route === "web_search_read") {
                    if (args.limit) {
                        assert.strictEqual(args.limit, 2, "the limit should be correctly set");
                    }
                    if (args.offset) {
                        assert.strictEqual(
                            args.offset,
                            2,
                            "the offset should be correctly set at load more"
                        );
                    }
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").length,
            2,
            "there should be 2 records in the column"
        );

        assert.verifySteps(["7"], "only the appearing category should be fetched");

        // load more
        await click(
            target.querySelector(".o_kanban_group:nth-child(2)").find(".o_kanban_load_more")
        );

        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").length,
            3,
            "there should now be 3 records in the column"
        );

        assert.verifySteps(["6"], "the other categories should not be fetched");
    });

    QUnit.skipWOWL("update buttons after column creation", async (assert) => {
        assert.expect(2);

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

        await createColumn();
        await editColumnName("new column");
        await validateColumn();

        assert.containsOnce(target, ".o-kanban-button-new");
    });

    QUnit.skipWOWL("group_by_tooltip option when grouping on a many2one", async (assert) => {
        assert.expect(12);
        delete serverData.models.partner.records[3].product_id;
        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban default_group_by="bar">' +
                '<field name="bar"/>' +
                '<field name="product_id" ' +
                'options=\'{"group_by_tooltip": {"name": "Kikou"}}\'/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
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
        assert.containsN(target, ".o_kanban_group", 2, "should have " + 2 + " columns");

        // simulate an update coming from the searchview, with another groupby given
        await reload(kanban, { groupBy: ["product_id"] });

        assert.containsN(target, ".o_kanban_group", 3, "should have " + 3 + " columns");
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").length,
            1,
            "column should contain 1 record(s)"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_record").length,
            2,
            "column should contain 2 record(s)"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(3) .o_kanban_record").length,
            1,
            "column should contain 1 record(s)"
        );
        assert.ok(
            target.querySelector(".o_kanban_group:first-child span.o_column_title:contains(None)")
                .length,
            "first column should have a default title for when no value is provided"
        );
        assert.ok(
            !target.querySelector(".o_kanban_group:first-child .o_kanban_header_title").dataset
                .tooltip,
            "tooltip of first column should not defined, since group_by_tooltip title and the many2one field has no value"
        );
        assert.ok(
            target.querySelector(".o_kanban_group:nth-child(2) span.o_column_title:contains(hello)")
                .length,
            "second column should have a title with a value from the many2one"
        );
        assert.strictEqual(
            target.querySelector(".o_kanban_group:nth-child(2) .o_kanban_header_title").dataset
                .tooltip,
            "<div>Kikou</br>hello</div>",
            "second column should have a tooltip with the group_by_tooltip title and many2one field value"
        );
    });

    QUnit.test("move a record then put it again in the same column", async (assert) => {
        assert.expect(6);

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
        assert.expect(9);

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
            ["record1", "record2"],
            "records should be correctly ordered"
        );

        await dragAndDrop(".o_kanban_record:nth-child(2)", ".o_kanban_record:nth-child(3)");

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.deepEqual(
            getCardTexts(),
            ["record2", "record1"],
            "records should be correctly ordered"
        );

        await dragAndDrop(".o_kanban_record:nth-child(3)", ".o_kanban_record:nth-child(2)");

        assert.containsN(target, ".o_kanban_group:first-child .o_kanban_record", 2);
        assert.deepEqual(
            getCardTexts(),
            ["record1", "record2"],
            "records should be correctly ordered"
        );
        assert.verifySteps(["resequence", "resequence"], "should have resequenced twice");
    });

    QUnit.skipWOWL("basic support for widgets", async (assert) => {
        // This test could be removed as soon as we drop the support of legacy widgets (see test
        // below, which is a duplicate of this one, but with an Owl Component instead).
        assert.expect(1);

        const MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                serverData.models = dataPoint.data;
            },
            start: function () {
                this.el.querySelectorel.text(JSON.stringify(serverData.models));
            },
        });
        widgetRegistry.add("test", MyWidget);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                "<div>" +
                '<t t-esc="record.foo.value"/>' +
                '<field name="foo" blip="1"/>' +
                '<widget name="test"/>' +
                "</div>" +
                "</t></templates></kanban>",
        });

        assert.strictEqual(
            target.querySelector(".o_widget:nth-child(2)").innerText,
            '{"foo":"gnap","id":3}',
            "widget should have been instantiated"
        );
        delete widgetRegistry.map.test;
    });

    QUnit.skipWOWL("basic support for widgets (being Owl Components)", async (assert) => {
        assert.expect(1);

        class MyComponent extends owl.Component {
            get value() {
                return JSON.stringify(this.props.record.data);
            }
        }
        MyComponent.template = owl.xml`<div t-esc="value"/>`;
        widgetRegistryOwl.add("test", MyComponent);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
            <kanban class="o_kanban_test">
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

        assert.strictEqual(
            target.querySelector(".o_widget:nth-child(2)").innerText,
            '{"foo":"gnap","id":3}'
        );
        delete widgetRegistryOwl.map.test;
    });

    QUnit.skipWOWL(
        "subwidgets with on_attach_callback when changing record color",
        async (assert) => {
            assert.expect(3);

            let counter = 0;
            const MyTestWidget = AbstractField.extend({
                on_attach_callback: function () {
                    counter++;
                },
            });
            fieldRegistry.add("test_widget", MyTestWidget);

            await makeView({
                type: "kanban",
                resModel: "category",
                serverData,
                arch:
                    '<kanban class="o_kanban_test">' +
                    '<field name="color"/>' +
                    "<templates>" +
                    '<t t-name="kanban-box">' +
                    '<div color="color">' +
                    '<div class="o_dropdown_kanban dropdown">' +
                    '<a class="dropdown-toggle o-no-caret btn" data-toggle="dropdown" href="#">' +
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

            // set a color to kanban record
            testUtils.kanban.toggleRecordDropdown(getCard(0));
            await click(getCard(0), ".oe_kanban_colorpicker a.oe_kanban_color_9");

            // first record has replaced its $el with a new one
            assert.hasClass(getCard(0), "oe_kanban_color_9");
            assert.strictEqual(counter, 3, "on_attach_callback method should be called 3 times");

            delete fieldRegistry.map.test_widget;
        }
    );

    QUnit.test("column progressbars properly work", async (assert) => {
        assert.expect(2);

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
        assert.expect(8);

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
            ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-muted",
            "should have false kanban color"
        );
        assert.hasClass(
            target.querySelector(
                ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-muted"
            ),
            "bg-muted"
        );

        await click(
            target,
            ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-muted"
        );

        assert.hasClass(
            target.querySelector(
                ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-muted"
            ),
            "progress-bar-animated"
        );
        assert.hasClass(
            target.querySelector(".o_kanban_group:last-child"),
            "o_kanban_group_show_muted"
        );
        assert.deepEqual(getCounters(), ["1", "1"]);
    });

    QUnit.test('column progressbars: "false" bar with sum_field', async (assert) => {
        assert.expect(4);

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
            ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-muted"
        );

        assert.hasClass(
            target.querySelector(
                ".o_kanban_group:last-child .o_kanban_counter_progress .progress-bar.bg-muted"
            ),
            "progress-bar-animated"
        );
        assert.deepEqual(getCounters(), ["-4", "15"]);
    });

    QUnit.test("column progressbars should not crash in non grouped views", async (assert) => {
        assert.expect(3);

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
        assert.verifySteps(["web_search_read"], "no read on progress bar data is done");
    });

    QUnit.test(
        "column progressbars: creating a new column should create a new progressbar",
        async (assert) => {
            assert.expect(2);

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
        assert.expect(3);

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
        assert.expect(2);

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
            assert.expect(2);

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
        assert.expect(4);

        // add active field on partner model and make all records active
        serverData.models.partner.fields.active = { string: "Active", type: "char", default: true };

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
            assert.expect(2);

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
        assert.expect(9);

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
        assert.expect(11);

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
        assert.expect(4);

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
        assert.expect(2);

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
            assert.expect(4);

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
        assert.expect(3);

        // Add a sequence number and initialize
        serverData.models.partner.fields.sequence = { type: "integer" };
        serverData.models.partner.records.forEach((el, i) => {
            el.sequence = i;
        });

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
            ".o_kanban_group:last-child"
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
            assert.expect(2);

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
            assert.expect(7);

            serverData.views["partner,some_view_ref,form"] = /* xml */ `
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
            assert.expect(2);

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
        assert.expect(1);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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
        assert.expect(1);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban class="o_kanban_test">
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
        });
    });

    QUnit.test("test displaying image (binary & placeholder)", async (assert) => {
        assert.expect(2);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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
        assert.expect(2);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
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
        assert.expect(2);
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
            'img[data-src*="/web/image"][data-src$="&id=1"]',
            "image url should contain id of set partner_id"
        );
        assert.containsOnce(
            target,
            'img[data-src*="/web/image"][data-src$="&id="]',
            "image url should contain an empty id if partner_id is not set"
        );
    });

    QUnit.test(
        "grouped kanban becomes ungrouped when clearing domain then clearing groupby",
        async (assert) => {
            // in this test, we simulate that clearing the domain is slow, so that
            // clearing the groupby does not corrupt the data handled while
            // reloading the kanban view.
            assert.expect(4);

            const prom = makeDeferred();

            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban class="o_kanban_test">' +
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
        assert.expect(2);
        serverData.models.partner.records = [];

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            // force group_create to false, otherwise the CREATE button in control panel is hidden
            arch:
                '<kanban class="o_kanban_test" group_create="0" on_create="quick_create"><templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="name"/>' +
                "</div>" +
                "</t></templates></kanban>",
            groupBy: ["product_id"],
        });

        patchWithCleanup(kanban.env.services.action, {
            async switchView() {
                assert.step("switch_view");
            },
        });

        await createRecord();
        assert.verifySteps(["switch_view"]);
    });

    QUnit.skipWOWL("keyboard navigation on kanban basic rendering", async (assert) => {
        assert.expect(3);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                "<div>" +
                '<t t-esc="record.foo.value"/>' +
                '<field name="foo"/>' +
                "</div>" +
                "</t></templates></kanban>",
        });

        getCard(0).focus();
        assert.strictEqual(document.activeElement, getCard(0), "the kanban cards are focussable");

        await triggerEvent(getCard(0), null, "keydown", { key: "ArrowRight" });

        assert.strictEqual(
            document.activeElement,
            getCard(1),
            "the second card should be focussed"
        );

        await triggerEvent(getCard(1), null, "keydown", { key: "ArrowLeft" });

        assert.strictEqual(document.activeElement, getCard(0), "the first card should be focussed");
    });

    QUnit.skipWOWL("keyboard navigation on kanban grouped rendering", async (assert) => {
        assert.expect(3);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
                '<field name="bar"/>' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["bar"],
        });

        const $firstColumnFisrtCard = target.querySelector(".o_kanban_record:first-child");
        const $secondColumnFirstCard = target.querySelector(
            ".o_kanban_group:nth-child(2) .o_kanban_record:first-child"
        );
        const $secondColumnSecondCard = target.querySelector(
            ".o_kanban_group:nth-child(2) .o_kanban_record:nth-child(2)"
        );

        $firstColumnFisrtCard.focus();

        //RIGHT should select the next column
        $firstColumnFisrtCard.trigger(
            $.Event("keydown", { which: $.ui.keyCode.RIGHT, keyCode: $.ui.keyCode.RIGHT })
        );
        assert.strictEqual(
            document.activeElement,
            $secondColumnFirstCard[0],
            "RIGHT should select the first card of the next column"
        );

        //DOWN should move up one card
        $secondColumnFirstCard.trigger(
            $.Event("keydown", { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN })
        );
        assert.strictEqual(
            document.activeElement,
            $secondColumnSecondCard[0],
            "DOWN should select the second card of the current column"
        );

        //LEFT should go back to the first column
        $secondColumnSecondCard.trigger(
            $.Event("keydown", { which: $.ui.keyCode.LEFT, keyCode: $.ui.keyCode.LEFT })
        );
        assert.strictEqual(
            document.activeElement,
            $firstColumnFisrtCard[0],
            "LEFT should select the first card of the first column"
        );
    });

    QUnit.skipWOWL(
        "keyboard navigation on kanban grouped rendering with empty columns",
        async (assert) => {
            assert.expect(2);

            serverData.models.partner.records[1].state = "abc";

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban class="o_kanban_test">' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    "</t></templates></kanban>",
                groupBy: ["state"],
                async mockRPC(route, args) {
                    if (args.method === "web_read_group") {
                        // override read_group to return empty groups, as this is
                        // the case for several models (e.g. project.task grouped
                        // by stage_id)
                        return this._super.apply(this, arguments).then(function (result) {
                            // add 2 empty columns in the middle
                            result.groups.splice(1, 0, {
                                state_count: 0,
                                state: "def",
                                __domain: [["state", "=", "def"]],
                            });
                            result.groups.splice(1, 0, {
                                state_count: 0,
                                state: "def",
                                __domain: [["state", "=", "def"]],
                            });

                            // add 1 empty column in the beginning and the end
                            result.groups.unshift({
                                state_count: 0,
                                state: "def",
                                __domain: [["state", "=", "def"]],
                            });
                            result.groups.push({
                                state_count: 0,
                                state: "def",
                                __domain: [["state", "=", "def"]],
                            });
                            return result;
                        });
                    }
                },
            });

            /**
             * DEF columns are empty
             *
             *    | DEF | ABC  | DEF | DEF | GHI  | DEF
             *    |-----|------|-----|-----|------|-----
             *    |     | yop  |     |     | gnap |
             *    |     | blip |     |     | blip |
             */
            const $yop = target.querySelector(".o_kanban_record:first-child");
            const $gnap = target.querySelector(
                ".o_kanban_group:nth-child(4) .o_kanban_record:first-child"
            );

            $yop.focus();

            //RIGHT should select the next column that has a card
            $yop.trigger(
                $.Event("keydown", { which: $.ui.keyCode.RIGHT, keyCode: $.ui.keyCode.RIGHT })
            );
            assert.strictEqual(
                document.activeElement,
                $gnap[0],
                "RIGHT should select the first card of the next column that has a card"
            );

            //LEFT should go back to the first column that has a card
            $gnap.trigger(
                $.Event("keydown", { which: $.ui.keyCode.LEFT, keyCode: $.ui.keyCode.LEFT })
            );
            assert.strictEqual(
                document.activeElement,
                $yop[0],
                "LEFT should select the first card of the first column that has a card"
            );
        }
    );

    QUnit.skipWOWL(
        "keyboard navigation on kanban when the focus is on a link that " +
            "has an action and the kanban has no oe_kanban_global_... class",
        async (assert) => {
            assert.expect(1);
            const kanban = await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch:
                    '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div><a type="edit">Edit</a></div>' +
                    "</t></templates></kanban>",
            });

            testUtils.mock.intercept(kanban, "switch_view", function (event) {
                assert.deepEqual(
                    event.data,
                    {
                        view_type: "form",
                        res_id: 1,
                        mode: "edit",
                        resModel: "partner",
                    },
                    "When selecting focusing a card and hitting ENTER, the first link or button is clicked"
                );
            });

            await triggerEvents(getCard(0), null, ["focus", ["keydown", { key: "Enter" }]]);
        }
    );

    QUnit.skipWOWL("asynchronous rendering of a field widget (ungrouped)", async (assert) => {
        assert.expect(4);

        let fooFieldProm = makeDeferred();
        fieldRegistry.get("char").add(
            "asyncwidget",
            FieldChar.extend({
                willStart: function () {
                    return fooFieldProm;
                },
                start: function () {
                    this.el.innerText = "LOADED";
                },
            })
        );

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                '<div><field name="foo" widget="asyncwidget"/></div>' +
                "</t></templates></kanban>",
        });

        assert.strictEqual($(".o_kanban_record").length, 0, "kanban view is not ready yet");

        fooFieldProm.resolve();
        await nextTick();
        assert.strictEqual($(".o_kanban_record").innerText, "LOADEDLOADEDLOADEDLOADED");

        // reload with a domain
        fooFieldProm = makeDeferred();
        await reload(kanban, { domain: [["id", "=", 1]] });

        assert.strictEqual($(".o_kanban_record").innerText, "LOADEDLOADEDLOADEDLOADED");

        fooFieldProm.resolve();
        await nextTick();
        assert.strictEqual($(".o_kanban_record").innerText, "LOADED");
    });

    QUnit.skipWOWL("asynchronous rendering of a field widget (grouped)", async (assert) => {
        assert.expect(4);

        let fooFieldProm = makeDeferred();
        fieldRegistry.get("char").add(
            "asyncwidget",
            FieldChar.extend({
                willStart: function () {
                    return fooFieldProm;
                },
                start: function () {
                    this.el.innerText = "LOADED";
                },
            })
        );

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                '<div><field name="foo" widget="asyncwidget"/></div>' +
                "</t></templates></kanban>",
            groupBy: ["foo"],
        });

        assert.strictEqual($(".o_kanban_record").length, 0, "kanban view is not ready yet");

        fooFieldProm.resolve();
        await nextTick();
        assert.strictEqual($(".o_kanban_record").innerText, "LOADEDLOADEDLOADEDLOADED");

        // reload with a domain
        fooFieldProm = makeDeferred();
        await reload(kanban, { domain: [["id", "=", 1]] });

        assert.strictEqual($(".o_kanban_record").innerText, "LOADEDLOADEDLOADEDLOADED");

        fooFieldProm.resolve();
        await nextTick();
        assert.strictEqual($(".o_kanban_record").innerText, "LOADED");
    });

    QUnit.skipWOWL("asynchronous rendering of a field widget with display attr", async (assert) => {
        assert.expect(3);

        const fooFieldDef = makeDeferred();
        fieldRegistry.get("char").add(
            "asyncwidget",
            FieldChar.extend({
                willStart: function () {
                    return fooFieldDef;
                },
                start: function () {
                    this.el.innerText = "LOADED";
                },
            })
        );

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                '<div><field name="foo" display="right" widget="asyncwidget"/></div>' +
                "</t></templates></kanban>",
        });

        assert.containsNone(document.body, ".o_kanban_record");

        fooFieldDef.resolve();
        await nextTick();
        assert.strictEqual(getCard(0).innerText, "LOADEDLOADEDLOADEDLOADED");
        assert.hasClass(getCard(0).querySelector(".o_field_char"), "float-right");
    });

    QUnit.skipWOWL("asynchronous rendering of a widget", async (assert) => {
        assert.expect(2);

        const widgetDef = makeDeferred();
        widgetRegistry.add(
            "asyncwidget",
            Widget.extend({
                willStart: function () {
                    return widgetDef;
                },
                start: function () {
                    this.el.innerText = "LOADED";
                },
            })
        );

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                '<div><widget name="asyncwidget"/></div>' +
                "</t></templates></kanban>",
        });

        assert.containsNone(document.body, ".o_kanban_record");

        widgetDef.resolve();
        await nextTick();

        assert.strictEqual(
            getCard(0).querySelector(".o_widget").innerText,
            "LOADEDLOADEDLOADEDLOADED"
        );
    });

    QUnit.skipWOWL("update kanban with asynchronous field widget", async (assert) => {
        assert.expect(3);

        const fooFieldDef = makeDeferred();
        fieldRegistry.get("char").add(
            "asyncwidget",
            FieldChar.extend({
                willStart: function () {
                    return fooFieldDef;
                },
                start: function () {
                    this.el.innerText = "LOADED";
                },
            })
        );

        const kanban = await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                '<div><field name="foo" widget="asyncwidget"/></div>' +
                "</t></templates></kanban>",
            domain: [["id", "=", "0"]], // no record matches this domain
        });

        assert.containsNone(target, ".o_kanban_record:not(.o_kanban_ghost)");

        reload(kanban, { domain: [] }); // this rendering will be async

        assert.containsNone(target, ".o_kanban_record:not(.o_kanban_ghost)");

        fooFieldDef.resolve();
        await nextTick();

        assert.strictEqual(getCard(0).innerText, "LOADEDLOADEDLOADEDLOADED");
    });

    QUnit.skipWOWL("set cover image", async (assert) => {
        assert.expect(7);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
                "<templates>" +
                '<t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click">' +
                '<field name="name"/>' +
                '<div class="o_dropdown_kanban dropdown">' +
                '<a class="dropdown-toggle o-no-caret btn" data-toggle="dropdown" href="#">' +
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
            async mockRPC(route, args) {
                if (args.model === "partner" && args.method === "write") {
                    assert.step(String(args.args[0][0]));
                    return this._super(route, args);
                }
                return this._super(route, args);
            },
            intercepts: {
                switch_view: function (event) {
                    assert.deepEqual(
                        _.pick(event.data, "mode", "model", "res_id", "view_type"),
                        {
                            mode: "readonly",
                            resModel: "partner",
                            res_id: 1,
                            view_type: "form",
                        },
                        "should trigger an event to open the clicked record in a form view"
                    );
                },
            },
        });

        testUtils.kanban.toggleRecordDropdown(getCard(0));
        await click(getCard(0), "[data-type=set_cover]");
        assert.containsNone(getCard(0), "img", "Initially there is no image.");

        await click($(".modal").find("img[data-id='1']"));
        await testUtils.modal.clickButton("Select");
        assert.containsOnce(target, 'img[data-src*="/web/image/1"]');

        testUtils.kanban.toggleRecordDropdown(getCard(1));
        await click(getCard(1), "[data-type=set_cover]");
        $(".modal").find("img[data-id='2']").dblclick();
        await nextTick();
        assert.containsOnce(target, 'img[data-src*="/web/image/2"]');
        await click(target, ".o_kanban_record:first-child .o_attachment_image");
        assert.verifySteps(["1", "2"], "should writes on both kanban records");
    });

    QUnit.test("ungrouped kanban with handle field", async (assert) => {
        assert.expect(4);

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

        assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_sortable");
        assert.deepEqual(getCardTexts(), ["yop", "blip", "gnap", "blip"]);

        await dragAndDrop(".o_kanban_record", ".o_kanban_record:nth-child(4)");

        assert.deepEqual(getCardTexts(), ["blip", "gnap", "blip", "yop"]);
    });

    QUnit.test("ungrouped kanban without handle field", async (assert) => {
        assert.expect(3);

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

        assert.doesNotHaveClass(target.querySelector(".o_kanban_renderer"), "o_kanban_sortable");
        assert.deepEqual(getCardTexts(), ["yop", "blip", "gnap", "blip"]);

        await dragAndDrop(".o_kanban_record", ".o_kanban_record:nth-child(4)");

        assert.deepEqual(getCardTexts(), ["yop", "blip", "gnap", "blip"]);
    });

    QUnit.skipWOWL("click on image field in kanban with oe_kanban_global_click", async (assert) => {
        assert.expect(2);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch:
                '<kanban class="o_kanban_test">' +
                '<templates><t t-name="kanban-box">' +
                '<div class="oe_kanban_global_click">' +
                '<field name="image" widget="image"/>' +
                "</div>" +
                "</t></templates>" +
                "</kanban>",
            async mockRPC(route) {
                if (route.startsWith("data:image")) {
                    return true;
                }
            },
            intercepts: {
                switch_view: function (event) {
                    assert.deepEqual(
                        _.pick(event.data, "mode", "model", "res_id", "view_type"),
                        {
                            mode: "readonly",
                            resModel: "partner",
                            res_id: 1,
                            view_type: "form",
                        },
                        "should trigger an event to open the clicked record in a form view"
                    );
                },
            },
        });

        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 4);

        await click(target, ".o_field_image");
    });

    QUnit.skipWOWL("kanban view with boolean field", async (assert) => {
        assert.expect(2);

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

        assert.containsN(target, ".o_kanban_record:contains(True)", 3);
        assert.containsOnce(target, ".o_kanban_record:contains(False)");
    });

    QUnit.skipWOWL("kanban view with boolean widget", async (assert) => {
        assert.expect(1);

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

        assert.containsOnce(getCard(0), "div.custom-checkbox.o_field_boolean");
    });

    QUnit.skipWOWL(
        "kanban view with monetary and currency fields without widget",
        async (assert) => {
            assert.expect(1);

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
                session: {
                    currencies: _.indexBy(serverData.models.currency.records, "id"),
                },
            });

            const kanbanRecords = target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)");
            assert.deepEqual(
                [...kanbanRecords].map((r) => r.innerText),
                ["$ 1750.00", "$ 1500.00", "2000.00 €", "$ 2222.00"]
            );
        }
    );

    QUnit.skipWOWL("quick create: keyboard navigation to buttons", async (assert) => {
        assert.expect(2);

        const kanban = await makeView({
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
        await triggerEvent(kanban, ".o_field_widget[name=display_name]", "keydown", { key: "Tab" });

        assert.hasClass(document.activeElement, "btn btn-primary o_kanban_add");
    });

    QUnit.skipWOWL("kanban with isHtmlEmpty method", async (assert) => {
        assert.expect(3);

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
                .html()
                .trim(),
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
            assert.expect(16);

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
            assert.expect(25);

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
            assert.expect(19);

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
        assert.expect(32);

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
        ]);
    });

    QUnit.skipWOWL("kanban widget supports options parameters", async (assert) => {
        assert.expect(2);

        widgetRegistry.add(
            "widget_test_option",
            Widget.extend({
                init(parent, state, options) {
                    this._super(...arguments);
                    this.title = options.attrs.title;
                },
                start() {
                    this.el.querySelectorel.append(
                        $("<div>", { text: this.title, class: "o-test-widget-option" })
                    );
                },
            })
        );

        await makeView({
            arch: `<kanban>
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
            target.querySelector(".o-test-widget-option")[0].textContent,
            "Widget with Option"
        );
        delete widgetRegistry.map.optionwidget;
    });
});
