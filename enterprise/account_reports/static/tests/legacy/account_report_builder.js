/** @odoo-module **/

import { click, drag, editInput, getFixture } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { sortableDrag } from "@web/../tests/core/utils/nested_sortable_tests"

let arch;
let serverData;
let target;

QUnit.module("Account Reports Builder", ({ beforeEach }) => {
    beforeEach(async () => {
        arch = `
            <form>
                <field class="w-100" name="line_ids" widget="account_report_lines_list_x2many">
                    <list>
                        <field name="id" column_invisible="1"/>
                        <field name="sequence" column_invisible="1"/>
                        <field name="parent_id" column_invisible="1"/>
                        <field name="hierarchy_level" column_invisible="1"/>
                        <field name="name"/>
                        <field name="code" optional="hide"/>
                    </list>
                </field>
            </form>
        `;

        serverData = {
            models: {
                report: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        line_ids: {
                            string: "Lines",
                            type: "one2many",
                            relation: "report_lines",
                            relation_field: "report_id",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            line_ids: [1, 2, 3, 4, 5],
                        }
                    ]
                },
                report_lines: {
                    fields: {
                        report_id: { string: "Report ID", type: "many2one", relation: "report" },
                        id: { string: "ID", type: "integer" },
                        sequence: { string: "Sequence", type: "integer" },
                        parent_id: {
                            string: "Parent Line",
                            type: "many2one",
                            relation: "report_lines",
                            relation_field: "id",
                        },
                        hierarchy_level: { string: "Level", type: "integer" },
                        name: { string: "Name", type: "char" },
                        code: { string: "Code", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            sequence: null,
                            parent_id: false,
                            hierarchy_level: 1,
                            name: "Root without children",
                            code: "RWOC",
                        },
                        {
                            id: 2,
                            sequence: null,
                            parent_id: false,
                            hierarchy_level: 0,
                            name: "Root with children",
                            code: "RC",
                        },
                        {
                            id: 3,
                            sequence: null,
                            parent_id: 2,
                            hierarchy_level: 3,
                            name: "Child #1",
                            code: "C1",
                        },
                        {
                            id: 4,
                            sequence: null,
                            parent_id: 3,
                            hierarchy_level: 5,
                            name: "Grandchild",
                            code: "GC",
                        },
                        {
                            id: 5,
                            sequence: null,
                            parent_id: 2,
                            hierarchy_level: 3,
                            name: "Child #2",
                            code: "C2",
                        },
                    ]
                },
            },
            views: {
                "report_lines,false,form": `
                    <form>
                        <field name="name"/>
                    </form>
                `,
            }
        };

        target = getFixture();

        // Make fixture in visible range, so that document.elementFromPoint work as expected
        target.style.position = "absolute";
        target.style.top = "0";
        target.style.left = "0";
        target.style.height = "100%";
        target.style.opacity = QUnit.config.debug ? "" : "0";

        registerCleanup(async () => {
            target.style.position = "";
            target.style.top = "";
            target.style.left = "";
            target.style.height = "";
            target.style.opacity = "";
        });

        setupViewRegistries();
    });

    //------------------------------------------------------------------------------------------------------------------
    // Structure
    //------------------------------------------------------------------------------------------------------------------
    QUnit.test("have correct descendants count", async (assert) => {
        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
        });

        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li[data-descendants_count='0'] span:contains('Root without children')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li[data-descendants_count='3'] span:contains('Root with children')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li[data-descendants_count='1'] span:contains('Child #1')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li[data-descendants_count='0'] span:contains('Grandchild')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li[data-descendants_count='0'] span:contains('Child #2')");
    });

    //------------------------------------------------------------------------------------------------------------------
    // Create
    //------------------------------------------------------------------------------------------------------------------
    QUnit.test("can create a line", async (assert) => {
        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
        });

        await click(target.querySelector(".account_report_lines_list_x2many"), "li:last-of-type a");

        assert.containsOnce(target, ".o_dialog");

        await editInput(target.querySelector("div[name='name'] input"), null, "Created line");
        await click(target.querySelector(".o_dialog"), ".o_form_button_save");

        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Created line')");
    });

    //------------------------------------------------------------------------------------------------------------------
    // Edit
    //------------------------------------------------------------------------------------------------------------------
    QUnit.test("can edit a line", async (assert) => {
        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
        });

        await click(target.querySelector(".account_report_lines_list_x2many"), "li[data-record_id='1'] .column");

        assert.containsOnce(target, ".o_dialog");

        await editInput(target.querySelector("div[name='name'] input"), null, "Line without children (edited)");
        await click(target.querySelector(".o_dialog"), ".o_form_button_save");

        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Line without children (edited)')");
    });

    //------------------------------------------------------------------------------------------------------------------
    // Delete
    //------------------------------------------------------------------------------------------------------------------
    QUnit.test("can delete a root", async (assert) => {
        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
        });

        await click(target.querySelector(".account_report_lines_list_x2many"), "li[data-record_id='1'] > div > .trash");

        assert.containsNone(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Root without children')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Root with children')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Child #1')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Grandchild')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Child #2')");
    });

    QUnit.test("can delete a root with children", async (assert) => {
        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
        });

        await click(target.querySelector(".account_report_lines_list_x2many"), "li[data-record_id='2'] > div > .trash");

        // Confirmation dialog "This line and all its children will be deleted. Are you sure you want to proceed?"
        assert.containsOnce(target, ".o_dialog");

        await click(target.querySelector(".o_dialog"), ".btn-primary");

        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Root without children')");
        assert.containsNone(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Root with children')");
        assert.containsNone(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Child #1')");
        assert.containsNone(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Grandchild')");
        assert.containsNone(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Child #2')");
    });

    QUnit.test("can delete a last child", async (assert) => {
        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
        });

        await click(target.querySelector(".account_report_lines_list_x2many"), "li[data-record_id='4'] > div > .trash");

        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Root without children')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li[data-descendants_count='2'] span:contains('Root with children')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li[data-descendants_count='0'] span:contains('Child #1')");
        assert.containsNone(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Grandchild')");
        assert.containsOnce(target.querySelector(".account_report_lines_list_x2many"), "li span:contains('Child #2')");
    });

    //------------------------------------------------------------------------------------------------------------------
    // Drag and drop
    //------------------------------------------------------------------------------------------------------------------
    QUnit.test("can move a root down", async (assert) => {
        serverData.models.report.records[0].line_ids = [1, 2, 3, 4];
        serverData.models.report_lines.records = [
            {
                id: 1,
                sequence: null,
                parent_id: false,
                hierarchy_level: 1,
                name: "dragged",
                code: "D",
            },
            {
                id: 2,
                sequence: null,
                parent_id: false,
                hierarchy_level: 1,
                name: "noChild",
                code: "N",
            },
            {
                id: 3,
                sequence: null,
                parent_id: false,
                hierarchy_level: 0,
                name: "parent",
                code: "P",
            },
            {
                id: 4,
                sequence: null,
                parent_id: 3,
                hierarchy_level: 3,
                name: "child",
                code: "C",
            },
        ];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
            mockRPC: (route, args) => {
                if (args.method === 'web_save') {
                    const lineIds = args.args[1].line_ids;

                    // Parents
                    assert.equal(lineIds[0][2].parent_id, 3);

                    // Hierarchy levels
                    assert.equal(lineIds[0][2].hierarchy_level, 3);

                    // Sequences
                    assert.equal(lineIds[0][2].sequence, 4);
                    assert.equal(lineIds[1][2].sequence, 1);
                    assert.equal(lineIds[2][2].sequence, 2);
                    assert.equal(lineIds[3][2].sequence, 3);
                }
            }
        });

        const { drop, moveUnder } = await sortableDrag("li[data-record_id='1']");

        await moveUnder("li[data-record_id='2']");
        await moveUnder("li[data-record_id='4']");
        await drop();

        await click(target.querySelector(".o_form_button_save"));
    });

    QUnit.test("can move a root up", async (assert) => {
        serverData.models.report.records[0].line_ids = [1, 2, 3, 4];
        serverData.models.report_lines.records = [
            {
                id: 1,
                sequence: null,
                parent_id: false,
                hierarchy_level: 0,
                name: "parent",
                code: "P",
            },
            {
                id: 2,
                sequence: null,
                parent_id: 1,
                hierarchy_level: 3,
                name: "child",
                code: "C",
            },
            {
                id: 3,
                sequence: null,
                parent_id: false,
                hierarchy_level: 1,
                name: "noChild",
                code: "N",
            },
            {
                id: 4,
                sequence: null,
                parent_id: false,
                hierarchy_level: 1,
                name: "dragged",
                code: "D",
            },
        ];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
            mockRPC: (route, args) => {
                if (args.method === 'web_save') {
                    const lineIds = args.args[1].line_ids;

                    // Parents
                    assert.equal(lineIds[0][2].parent_id, 1);

                    // Hierarchy levels
                    assert.equal(lineIds[0][2].hierarchy_level, 3);

                    // Sequences
                    assert.equal(lineIds[0][2].sequence, 2);
                    assert.equal(lineIds[1][2].sequence, 1);
                    assert.equal(lineIds[2][2].sequence, 3);
                    assert.equal(lineIds[3][2].sequence, 4);
                }
            }
        });

        const { drop, moveAbove } = await sortableDrag("li[data-record_id='4']");

        await moveAbove("li[data-record_id='3']");
        await moveAbove("li[data-record_id='2']");
        await drop();

        await click(target.querySelector(".o_form_button_save"));
    });

    QUnit.test("can move a child down", async (assert) => {
        serverData.models.report.records[0].line_ids = [1, 2, 3, 4];
        serverData.models.report_lines.records = [
            {
                id: 1,
                sequence: null,
                parent_id: false,
                hierarchy_level: 0,
                name: "parent",
                code: "P",
            },
            {
                id: 2,
                sequence: null,
                parent_id: 1,
                hierarchy_level: 3,
                name: "dragged",
                code: "D",
            },
            {
                id: 3,
                sequence: null,
                parent_id: 1,
                hierarchy_level: 3,
                name: "child",
                code: "C",
            },
            {
                id: 4,
                sequence: null,
                parent_id: false,
                hierarchy_level: 1,
                name: "noChild",
                code: "N",
            },
        ];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
            mockRPC: (route, args) => {
                if (args.method === 'web_save') {
                    const lineIds = args.args[1].line_ids;

                    // Parents
                    assert.equal(lineIds[0][2].parent_id, false);

                    // Hierarchy levels
                    assert.equal(lineIds[0][2].hierarchy_level, 1);

                    // Sequences
                    assert.equal(lineIds[0][2].sequence, 4);
                    assert.equal(lineIds[1][2].sequence, 1);
                    assert.equal(lineIds[2][2].sequence, 2);
                    assert.equal(lineIds[3][2].sequence, 3);
                }
            }
        });

        const { drop, moveUnder } = await sortableDrag("li[data-record_id='2']");

        await moveUnder("li[data-record_id='3']");
        await moveUnder("li[data-record_id='4']");
        await drop();

        await click(target.querySelector(".o_form_button_save"));
    });

    QUnit.test("can move a child up", async (assert) => {
        serverData.models.report.records[0].line_ids = [1, 2, 3];
        serverData.models.report_lines.records = [
            {
                id: 1,
                sequence: null,
                parent_id: false,
                hierarchy_level: 0,
                name: "parent",
                code: "P",
            },
            {
                id: 2,
                sequence: null,
                parent_id: 1,
                hierarchy_level: 3,
                name: "child",
                code: "C",
            },
            {
                id: 3,
                sequence: null,
                parent_id: 1,
                hierarchy_level: 3,
                name: "dragged",
                code: "D",
            },
        ];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
            mockRPC: (route, args) => {
                if (args.method === 'web_save') {
                    const lineIds = args.args[1].line_ids;

                    // Parents
                    assert.equal(lineIds[0][2].parent_id, false);

                    // Hierarchy levels
                    assert.equal(lineIds[0][2].hierarchy_level, 1);

                    // Sequences
                    assert.equal(lineIds[0][2].sequence, 1);
                    assert.equal(lineIds[1][2].sequence, 2);
                    assert.equal(lineIds[2][2].sequence, 3);
                }
            }
        });

        const { drop, moveAbove } = await sortableDrag("li[data-record_id='3']");

        await moveAbove("li[data-record_id='2']");
        await moveAbove("li[data-record_id='1']");
        await drop();

        await click(target.querySelector(".o_form_button_save"));
    });

    QUnit.test("can move a new root into a child", async (assert) => {
        serverData.models.report.records[0].line_ids = [1, 2, 3];
        serverData.models.report_lines.records = [
            {
                id: 1,
                sequence: null,
                parent_id: false,
                hierarchy_level: 0,
                name: "parent",
                code: "P",
            },
            {
                id: 2,
                sequence: null,
                parent_id: 1,
                hierarchy_level: 3,
                name: "child",
                code: "C",
            },
            {
                id: 3,
                sequence: null,
                parent_id: false,
                hierarchy_level: 1,
                name: "noChild",
                code: "N",
            },
        ];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
            mockRPC: (route, args) => {
                if (args.method === 'web_save' && !target.querySelector(".o_dialog")) {
                    const lineIds = args.args[1].line_ids;

                    // Parents
                    assert.equal(lineIds[0][2].parent_id, 1);

                    // Hierarchy levels
                    assert.equal(lineIds[0][2].hierarchy_level, 3);

                    // Sequences
                    assert.equal(lineIds[0][2].sequence, 2);
                    assert.equal(lineIds[1][2].sequence, 1);
                    assert.equal(lineIds[2][2].sequence, 3);
                    assert.equal(lineIds[3][2].sequence, 4);
                }
            }
        });

        await click(target.querySelector(".account_report_lines_list_x2many"), "li:last-of-type a");
        await editInput(target.querySelector("div[name='name'] input"), null, "dragged");
        await click(target.querySelector(".o_dialog"), ".o_form_button_save");

        const { drop, moveAbove } = await sortableDrag("li[data-record_id='4']");

        await moveAbove("li[data-record_id='3']");
        await moveAbove("li[data-record_id='2']");
        await drop();

        await click(target.querySelector(".o_form_button_save"));
    });

    QUnit.test("can move a child into a new root", async (assert) => {
        serverData.models.report.records[0].line_ids = [];
        serverData.models.report_lines.records = [];

        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
            mockRPC: (route, args) => {
                if (args.method === 'web_save' && !target.querySelector(".o_dialog")) {
                    const lineIds = args.args[1].line_ids;

                    // Parents
                    assert.equal(lineIds[0][2].parent_id, 1);

                    // Hierarchy levels
                    assert.equal(lineIds[0][2].hierarchy_level, 3);

                    // Sequences
                    assert.equal(lineIds[0][2].sequence, 2);
                    assert.equal(lineIds[1][2].sequence, 1);
                }
            }
        });

        await click(target.querySelector(".account_report_lines_list_x2many"), "li:last-of-type a");
        await editInput(target.querySelector("div[name='name'] input"), null, "parent");
        await click(target.querySelector(".o_dialog"), ".o_form_button_save");

        await click(target.querySelector(".account_report_lines_list_x2many"), "li:last-of-type a");
        await editInput(target.querySelector("div[name='name'] input"), null, "dragged");
        await click(target.querySelector(".o_dialog"), ".o_form_button_save");

        const toSelector = target.querySelector("li[data-record_id='2']");
        const { drop, moveTo } = await drag(toSelector);

        await moveTo(toSelector, { x: 600 });
        await drop();

        await click(target.querySelector(".o_form_button_save"));
    });

    QUnit.test("can display and hide 'Code' column when toggled in optional fields", async (assert) => {
        await makeView({
            type: "form",
            resId: 1,
            resModel: "report",
            serverData,
            arch,
        });
        // Ensure `code` column is hidden by default
        assert.containsNone(
            target.querySelector(".account_report_lines_list_x2many"),
            "span.fw-bold.fixed:contains('Code')",
            "The 'Code' column should be hidden initially"
        );

        // simulate toggling the `code` field to make it visible
        await click(target.querySelector(".o-dropdown.dropdown-toggle"));
        await click(target.querySelector("input[name='code']"));

        // Check that the column is now visible
        assert.containsOnce(
            target.querySelector(".account_report_lines_list_x2many"),
            "span.fw-bold.fixed:contains('Code')",
            "The 'Code' column should now be visible after toggling"
        );

        // Toggle it back to hide and verify
        await click(target.querySelector("input[name='code']"));
        assert.containsNone(
            target.querySelector(".account_report_lines_list_x2many"),
            "span.fw-bold.fixed:contains('Code')",
            "The 'Code' column should be hidden after toggling back"
        );
    });
});
