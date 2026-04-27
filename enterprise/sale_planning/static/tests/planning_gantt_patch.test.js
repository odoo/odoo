import { defineMailModels, click } from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { queryAll, queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    selectFieldDropdownItem,
} from "@web/../tests/web_test_helpers";
import {
    clickCell,
    editPill,
    hoverGridCell,
    getGridContent,
    mountGanttView,
    SELECTORS,
} from "@web_gantt/../tests/web_gantt_test_helpers";

import { Component, onWillStart, useState, xml } from "@odoo/owl";
import { PlanningGanttRenderer } from "@planning/views/planning_gantt/planning_gantt_renderer";
import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

describe.current.tags("desktop");

class PlanningSlot extends models.Model {
    _name = "planning.slot";

    name = fields.Char({ string: "Name" });
    role_id = fields.Many2one({ relation: "planning.role" });
    sale_line_id = fields.Many2one({ string: "Sale Order Item", relation: "sale.order.line" });
    resource_id = fields.Many2one({ string: "Resource", relation: "resource.resource" });
    start_datetime = fields.Datetime({ string: "Start Datetime" });
    end_datetime = fields.Datetime({ string: "End Datetime" });
    allocated_percentage = fields.Float({ string: "Allocated percentage" });

    _records = [
        {
            id: 1,
            name: "Shift 1",
            role_id: 1,
            sale_line_id: 1,
            resource_id: false,
            start_datetime: "2021-10-12 08:00:00",
            end_datetime: "2021-10-12 12:00:00",
            allocated_percentage: 0.5,
        },
    ];
}

class PlanningRole extends models.Model {
    _name = "planning.role";

    name = fields.Char();

    _records = [
        { id: 1, name: "Developer" },
        { id: 2, name: "Support Tech" },
    ];
}

class Resource extends models.Model {
    _name = "resource.resource";

    name = fields.Char({ string: "Name" });

    _records = [
        { id: 1, name: "Chaganlal" },
        { id: 2, name: "Jarvo" },
    ];
}

class SaleOrderLine extends models.Model {
    _name = "sale.order.line";

    name = fields.Char();

    _records = [{ id: 1, name: "Computer Configuration" }];
}

defineMailModels();
defineModels([PlanningSlot, PlanningRole, Resource, SaleOrderLine]);

beforeEach(() => {
    mockDate("2021-10-10 07:00:00", +1);
    onRpc("has_group", () => false);
});

test("Process domain for plan dialog", async function () {
    let renderer;
    patchWithCleanup(PlanningGanttRenderer.prototype, {
        setup() {
            super.setup(...arguments);
            renderer = this;
        },
    });

    onRpc("gantt_resource_work_interval", () => [
        { false: [["2021-10-12 08:00:00", "2022-10-12 12:00:00"]] },
    ]);

    class Parent extends Component {
        static template = xml`<View t-props="state"/>`;
        static components = { View };
        static props = ["*"];
        setup() {
            this.state = useState({
                arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" default_scale="week"/>`,
                resModel: "planning.slot",
                type: "gantt",
                domain: [
                    ["start_datetime", "!=", false],
                    ["end_datetime", "!=", false],
                ],
            });
            this.field = useService("field");
            onWillStart(async () => {
                this.state.fields = await this.field.loadFields("planning.slot");
            });
        }
    }

    const parent = await mountWithCleanup(Parent);
    await animationFrame();

    let expectedDomain = Domain.and([
        Domain.and([
            new Domain(["&", ...Domain.TRUE.toList({}), ...Domain.TRUE.toList({})]),
            ["|", ["start_datetime", "=", false], ["end_datetime", "=", false]],
        ]),
        [["sale_line_id.state", "!=", "cancel"]],
        [["sale_line_id", "!=", false]],
    ]);
    expect(renderer.getPlanDialogDomain()).toEqual(expectedDomain.toList());

    parent.state.domain = [
        "|",
        ["role_id", "=", false],
        "&",
        ["resource_id", "!=", false],
        ["start_datetime", "=", false],
    ];
    await animationFrame();

    expectedDomain = Domain.and([
        Domain.and([
            new Domain([
                "|",
                ["role_id", "=", false],
                "&",
                ["resource_id", "!=", false],
                ...Domain.TRUE.toList({}),
            ]),
            ["|", ["start_datetime", "=", false], ["end_datetime", "=", false]],
        ]),
        [["sale_line_id.state", "!=", "cancel"]],
        [["sale_line_id", "!=", false]],
    ]);
    expect(renderer.getPlanDialogDomain()).toEqual(expectedDomain.toList());

    parent.state.domain = ["|", ["start_datetime", "=", false], ["end_datetime", "=", false]];
    await animationFrame();

    expectedDomain = Domain.and([
        Domain.and([
            Domain.TRUE,
            ["|", ["start_datetime", "=", false], ["end_datetime", "=", false]],
        ]),
        [["sale_line_id.state", "!=", "cancel"]],
        [["sale_line_id", "!=", false]],
    ]);
    expect(renderer.getPlanDialogDomain()).toEqual(expectedDomain.toList());
});

test("check default planned dates on the plan dialog", async function () {
    expect.assertions(4);
    mockTimeZone(0);
    patchWithCleanup(SelectCreateDialog.prototype, {
        setup() {
            super.setup(...arguments);
            expect(this.props.context.default_start_datetime).toMatch(/^2021-10-11/);
            expect(this.props.context.default_end_datetime).toMatch(/^2021-10-12/);
            expect(this.props.context.focus_date).toMatch(/^2021-10-13/);
            expect(this.props.context.scale).toBe("week");
        },
    });

    PlanningSlot._records.push({
        id: 2,
        role_id: 1,
        sale_line_id: 1,
        resource_id: false,
        start_datetime: false,
        end_datetime: false,
    });

    onRpc("gantt_resource_work_interval", () => []);

    await mountGanttView({
        resModel: "planning.slot",
        arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" default_scale="week"/>`,
    });
    await clickCell("11 W41 2021");
});

test("Show shift form dialog only when shifts to plan", async function () {
    // Additionally to 'Shift 1', we create a new unplanned shift 'Shift 2' which has a sale_line_id, no start_datetime and no end_datetime values
    PlanningSlot._records.push({
        id: 2,
        name: "Shift 2",
        role_id: 1,
        sale_line_id: 1,
    });
    PlanningSlot._views = {
        form: `<form js_class="planning_form"><field name="name"/></form>`,
        list: `<list><field name="name"/></list>`,
    };

    onRpc("gantt_resource_work_interval", () => [
        { false: [["2021-10-12 08:00:00", "2022-10-12 12:00:00"]] },
    ]);
    await mountGanttView({
        resModel: "planning.slot",
        arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" default_scale="week"/>`,
    });
    await hoverGridCell("13 W41 2021");
    await clickCell("13 W41 2021");

    expect(".o_dialog").toHaveCount(1);
    expect(".modal-title").toHaveText("Plan");
    expect(".o_data_cell").toHaveText("Shift 2");

    await click(".o_data_cell");
    await animationFrame();

    const { rows } = getGridContent();
    expect(rows).toEqual([
        {
            pills: [
                {
                    colSpan: "12 W41 2021 -> 12 W41 2021",
                    level: 0,
                    title: "Shift 1",
                },
                {
                    colSpan: "13 W41 2021 -> 13 W41 2021",
                    level: 0,
                    title: "Shift 2",
                },
            ],
        },
    ]);
    await hoverGridCell("13 W41 2021");
    await clickCell("13 W41 2021");
    expect(".o_dialog").toHaveCount(1);
    expect(".modal-title").toHaveText("Add Shift");
});

test("Open a dialog to schedule a plan using Open Shift", async function () {
    PlanningSlot._records.push({
        id: 2,
        sale_line_id: 1,
    });
    PlanningSlot._views = {
        list: `<list><field name="sale_line_id"/></list>`,
        form: `
            <form>
                <field name="resource_id"/>
                <field name="start_datetime"/>
                <field name="end_datetime"/>
                <field name="name"/>
            </form>
        `,
    };

    onRpc("gantt_resource_work_interval", () => [
        { false: [["2021-10-12 08:00:00", "2022-10-12 12:00:00"]] },
    ]);

    await mountGanttView({
        resModel: "planning.slot",
        arch: '<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" default_scale="week"/>',
        groupBy: ["resource_id"],
    });
    await hoverGridCell("13 W41 2021");
    await clickCell("13 W41 2021");
    await click(".modal-footer .o_create_button");

    await selectFieldDropdownItem("resource_id", "Jarvo");
    await contains(`[name='name'] input`).edit("Shift-2");
    await contains(`[name='start_datetime'] input`).edit('2021-10-12 09:00:00');
    await contains(`[name='end_datetime'] input`).edit('2021-10-12 12:00:00');

    await click(".o_form_button_save");
    await animationFrame();

    const shift2Pill = queryAll(SELECTORS.pill)[1];
    await contains(shift2Pill).click();
    expect(queryAllTexts`.o_popover .popover-body span`).toEqual([
        "Shift-2",
        "10/12/2021, 9:00 AM",
        "10/12/2021, 12:00 PM",
    ]);

    await editPill("Shift-2");
    expect(".o_field_widget[name=resource_id] input").toHaveValue("Jarvo");
});
