import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, runAllTimers } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountView,
    onRpc,
    quickCreateKanbanColumn,
} from "@web/../tests/web_test_helpers";

class Lead extends models.Model {
    _name = "crm.lead";

    name = fields.Char();
    date_deadline = fields.Date({ string: "Expected closing" });
}

defineModels([Lead]);
defineMailModels();

const kanbanArch = `
    <kanban js_class="forecast_kanban">
        <templates>
            <t t-name="card">
                <field name="name"/>
            </t>
        </templates>
    </kanban>
`;

test.tags("desktop");
test("filter out every records before the start of the current month with forecast_filter for a date field", async () => {
    mockDate("2021-02-10 00:00:00");
    Lead._records = [
        { id: 1, name: "Lead 1", date_deadline: "2021-01-01" },
        { id: 2, name: "Lead 2", date_deadline: "2021-01-20" },
        { id: 3, name: "Lead 3", date_deadline: "2021-02-01" },
        { id: 4, name: "Lead 4", date_deadline: "2021-02-20" },
        { id: 5, name: "Lead 5", date_deadline: "2021-03-01" },
        { id: 6, name: "Lead 6", date_deadline: "2021-03-20" },
    ];

    await mountView({
        arch: kanbanArch,
        searchViewArch: `
                <search>
                    <filter name="forecast" string="Forecast" context="{'forecast_filter':1}"/>
                    <filter name='groupby_date_deadline' context="{'group_by':'date_deadline'}"/>
                </search>`,
        resModel: "crm.lead",
        type: "kanban",
        context: {
            search_default_forecast: true,
            search_default_groupby_date_deadline: true,
            forecast_field: "date_deadline",
        },
        groupBy: ["date_deadline"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:eq(0) .o_kanban_record").toHaveCount(2, {
        message: "1st column (February) should contain 2 record",
    });
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(2, {
        message: "2nd column (March) should contain 2 records",
    });

    await contains(".o_searchview_facet:contains(Forecast) .o_facet_remove").click();

    expect(".o_kanban_group").toHaveCount(3);
    expect(".o_kanban_group:eq(0) .o_kanban_record").toHaveCount(2, {
        message: "1st column (January) should contain 2 record",
    });
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(2, {
        message: "2nd column (February) should contain 2 records",
    });
    expect(".o_kanban_group:eq(2) .o_kanban_record").toHaveCount(2, {
        message: "3nd column (March) should contain 2 records",
    });
});

test.tags("desktop");
test("filter out every records before the start of the current month with forecast_filter for a datetime field", async () => {
    mockDate("2021-02-10 00:00:00");
    Lead._fields.date_closed = fields.Datetime({ string: "Closed Date" });
    Lead._records = [
        {
            id: 1,
            name: "Lead 1",
            date_deadline: "2021-01-01",
            date_closed: "2021-01-01 00:00:00",
        },
        {
            id: 2,
            name: "Lead 2",
            date_deadline: "2021-01-20",
            date_closed: "2021-01-20 00:00:00",
        },
        {
            id: 3,
            name: "Lead 3",
            date_deadline: "2021-02-01",
            date_closed: "2021-02-01 00:00:00",
        },
        {
            id: 4,
            name: "Lead 4",
            date_deadline: "2021-02-20",
            date_closed: "2021-02-20 00:00:00",
        },
        {
            id: 5,
            name: "Lead 5",
            date_deadline: "2021-03-01",
            date_closed: "2021-03-01 00:00:00",
        },
        {
            id: 6,
            name: "Lead 6",
            date_deadline: "2021-03-20",
            date_closed: "2021-03-20 00:00:00",
        },
    ];
    await mountView({
        arch: kanbanArch,
        searchViewArch: `
                <search>
                    <filter name="forecast" string="Forecast" context="{'forecast_filter':1}"/>
                    <filter name='groupby_date_deadline' context="{'group_by':'date_deadline'}"/>
                    <filter name='groupby_date_closed' context="{'group_by':'date_closed'}"/>
                </search>`,
        resModel: "crm.lead",
        type: "kanban",
        context: {
            search_default_forecast: true,
            search_default_groupby_date_closed: true,
            forecast_field: "date_closed",
        },
        groupBy: ["date_closed"],
    });

    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:eq(0) .o_kanban_record").toHaveCount(2, {
        message: "1st column (February) should contain 2 record",
    });
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(2, {
        message: "2nd column (March) should contain 2 records",
    });

    await contains(".o_searchview_facet:contains(Forecast) .o_facet_remove").click();

    expect(".o_kanban_group").toHaveCount(3);
    expect(".o_kanban_group:eq(0) .o_kanban_record").toHaveCount(2, {
        message: "1st column (January) should contain 2 record",
    });
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(2, {
        message: "2nd column (February) should contain 2 records",
    });
    expect(".o_kanban_group:eq(2) .o_kanban_record").toHaveCount(2, {
        message: "3nd column (March) should contain 2 records",
    });
});

test("Forecast on months, until the end of the year of the latest data", async () => {
    expect.assertions(3);
    mockDate("2021-10-10 00:00:00");

    Lead._records = [
        { id: 1, name: "Lead 1", date_deadline: "2021-01-01" },
        { id: 2, name: "Lead 2", date_deadline: "2021-02-01" },
        { id: 3, name: "Lead 3", date_deadline: "2021-11-01" },
        { id: 4, name: "Lead 4", date_deadline: "2022-01-01" },
    ];
    onRpc("crm.lead", "web_read_group", ({ kwargs }) => {
        expect(kwargs.context.fill_temporal).toEqual({
            fill_from: "2021-10-01",
            min_groups: 4,
        });
        expect(kwargs.domain).toEqual([
            "&",
            "|",
            ["date_deadline", "=", false],
            ["date_deadline", ">=", "2021-10-01"],
            "|",
            ["date_deadline", "=", false],
            ["date_deadline", "<", "2023-01-01"],
        ]);
    });
    await mountView({
        arch: kanbanArch,
        searchViewArch: `
                <search>
                    <filter name="forecast" string="Forecast" context="{'forecast_filter':1}"/>
                    <filter name='groupby_date_deadline' context="{'group_by':'date_deadline'}"/>
                </search>`,
        resModel: "crm.lead",
        type: "kanban",
        context: {
            search_default_forecast: true,
            search_default_groupby_date_deadline: true,
            forecast_field: "date_deadline",
        },
        groupBy: ["date_deadline"],
    });

    expect(
        getService("fillTemporalService")
            .getFillTemporalPeriod({
                modelName: "crm.lead",
                field: {
                    name: "date_deadline",
                    type: "date",
                },
                granularity: "month",
            })
            .end.toFormat("yyyy-MM-dd"),
    ).toBe("2022-02-01");
});

test("Forecast on years, until the end of the year of the latest data", async () => {
    expect.assertions(3);
    mockDate("2021-10-10 00:00:00");

    Lead._records = [
        { id: 1, name: "Lead 1", date_deadline: "2021-01-01" },
        { id: 2, name: "Lead 2", date_deadline: "2022-02-01" },
        { id: 3, name: "Lead 3", date_deadline: "2027-11-01" },
    ];
    onRpc("crm.lead", "web_read_group", ({ kwargs }) => {
        expect(kwargs.context.fill_temporal).toEqual({
            fill_from: "2021-01-01",
            min_groups: 4,
        });
        expect(kwargs.domain).toEqual([
            "&",
            "|",
            ["date_deadline", "=", false],
            ["date_deadline", ">=", "2021-01-01"],
            "|",
            ["date_deadline", "=", false],
            ["date_deadline", "<", "2025-01-01"],
        ]);
    });
    await mountView({
        arch: kanbanArch,
        searchViewArch: `
                <search>
                    <filter name="forecast" string="Forecast" context="{'forecast_filter':1}"/>
                    <filter name='groupby_date_deadline' context="{'group_by':'date_deadline:year'}"/>
                </search>`,
        resModel: "crm.lead",
        type: "kanban",
        context: {
            search_default_forecast: true,
            search_default_groupby_date_deadline: true,
            forecast_field: "date_deadline",
        },
        groupBy: ["date_deadline:year"],
    });
    expect(
        getService("fillTemporalService")
            .getFillTemporalPeriod({
                modelName: "crm.lead",
                field: {
                    name: "date_deadline",
                    type: "date",
                },
                granularity: "year",
            })
            .end.toFormat("yyyy-MM-dd"),
    ).toBe("2023-01-01");
});

test.tags("desktop");
test("Add column extends the period the view is actually grouped by", async () => {
    // The renderer used to read `granularity` off the field descriptor, which
    // has no such property: it always resolved to "month" and expanded a period
    // nothing read, so Add column did nothing at any other granularity.
    mockDate("2021-10-10 00:00:00");
    Lead._records = [{ id: 1, name: "Lead 1", date_deadline: "2021-10-15" }];
    const endBounds = [];
    onRpc("crm.lead", "web_read_group", ({ kwargs }) => {
        const leaf = kwargs.domain.find((d) => Array.isArray(d) && d[1] === "<");
        endBounds.push(leaf ? leaf[2] : null);
    });
    await mountView({
        arch: kanbanArch,
        searchViewArch: `
                <search>
                    <filter name="forecast" string="Forecast" context="{'forecast_filter':1}"/>
                    <filter name='groupby_date_deadline' context="{'group_by':'date_deadline:year'}"/>
                </search>`,
        resModel: "crm.lead",
        type: "kanban",
        context: {
            search_default_forecast: true,
            search_default_groupby_date_deadline: true,
            forecast_field: "date_deadline",
        },
        groupBy: ["date_deadline:year"],
    });
    const beforeAdd = endBounds.at(-1);

    await quickCreateKanbanColumn();

    // mount asks for the computed 4-year period; loadGroupedList then shrinks the
    // period to the last group holding data (2022-01-01), so that is what one
    // expand() must build on.
    expect(beforeAdd).toBe("2025-01-01");
    expect(endBounds.at(-1)).toBe("2023-01-01", {
        message:
            "Add column must extend the YEAR period; expanding the month slot " +
            "instead would leave this at 2022-01-01",
    });
});

test.tags("desktop");
test("Forecast drag&drop and add column", async () => {
    mockDate("2023-09-01 00:00:00");
    Lead._fields.color = fields.Char();
    Lead._fields.int_field = fields.Integer({ string: "Value" });
    Lead._records = [
        {
            id: 1,
            int_field: 7,
            color: "d",
            name: "Lead 1",
            date_deadline: "2023-09-03",
        },
        {
            id: 2,
            int_field: 20,
            color: "w",
            name: "Lead 2",
            date_deadline: "2023-09-05",
        },
        {
            id: 3,
            int_field: 300,
            color: "s",
            name: "Lead 3",
            date_deadline: "2023-10-10",
        },
    ];

    onRpc(({ route, method }) => {
        expect.step(method || route);
    });
    await mountView({
        arch: `
                <kanban js_class="forecast_kanban">
                    <progressbar field="color" colors='{"s": "success", "w": "warning", "d": "danger"}'  sum_field="int_field"/>
                    <templates>
                        <t t-name="card">
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>`,
        searchViewArch: `
                <search>
                    <filter name="forecast" string="Forecast" context="{'forecast_filter':1}"/>
                    <filter name='groupby_date_deadline' context="{'group_by':'date_deadline'}"/>
                </search>`,
        resModel: "crm.lead",
        type: "kanban",
        context: {
            search_default_forecast: true,
            search_default_groupby_date_deadline: true,
            forecast_field: "date_deadline",
        },
        groupBy: ["date_deadline"],
    });

    const getProgressBarsColors = () =>
        queryAll(".o_column_progress").map((columnProgressEl) =>
            queryAll(".progress-bar", { root: columnProgressEl }).map((progressBarEl) =>
                [...progressBarEl.classList].find((htmlClass) =>
                    htmlClass.startsWith("bg-"),
                ),
            ),
        );

    expect(queryAllTexts(".o_animated_number")).toEqual(["27", "300"]);
    expect(getProgressBarsColors()).toEqual([
        ["bg-warning", "bg-danger"],
        ["bg-success"],
    ]);

    await contains(".o_kanban_group:first .o_kanban_record").dragAndDrop(
        ".o_kanban_group:eq(1)",
    );
    await runAllTimers();

    expect(queryAllTexts(".o_animated_number")).toEqual(["20", "307"]);
    expect(getProgressBarsColors()).toEqual([
        ["bg-warning"],
        ["bg-success", "bg-danger"],
    ]);

    await quickCreateKanbanColumn();

    expect(queryAllTexts(".o_animated_number")).toEqual(["20", "307"]);
    expect(getProgressBarsColors()).toEqual([
        ["bg-warning"],
        ["bg-success", "bg-danger"],
    ]);

    expect.verifySteps([
        "get_views",
        "read_progress_bar",
        "web_read_group",
        "web_save",
        "read_progress_bar",
        "formatted_read_group",
        "read_progress_bar",
        "web_read_group",
    ]);
});
