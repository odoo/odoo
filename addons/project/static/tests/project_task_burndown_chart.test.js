import { describe, expect, test } from "@odoo/hoot";
import { click, queryAll } from "@odoo/hoot-dom";
import {
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { defineProjectModels } from "./project_models";

class ProjectTaskBurndownChartReport extends models.Model {
    _name = "project.task.burndown.chart.report";

    date = fields.Date();
    project_id = fields.Many2one({ relation: "project.project" });
    stage_id = fields.Many2one({ relation: "project.task.type" });
    is_closed = fields.Selection({
        string: "Burnup chart",
        selection: [
            ["closed", "Closed tasks"],
            ["open", "Open tasks"],
        ],
    });
    nb_tasks = fields.Integer({
        string: "Number of Tasks",
        type: "integer",
        aggregator: "sum",
    });

    _records = [
        {
            id: 1,
            project_id: 1,
            stage_id: 1,
            is_closed: "open",
            date: "2020-01-01",
            nb_tasks: 10,
        },
        {
            id: 2,
            project_id: 1,
            stage_id: 2,
            is_closed: "open",
            date: "2020-02-01",
            nb_tasks: 5,
        },
        {
            id: 3,
            project_id: 1,
            stage_id: 3,
            is_closed: "closed",
            date: "2020-03-01",
            nb_tasks: 2,
        },
    ];
}

defineProjectModels();
defineModels([ProjectTaskBurndownChartReport]);

describe.current.tags("desktop");

mockService("notification", () => ({
    add() {
        expect.step("notification");
    },
}));

const mountViewParams = {
    resModel: "project.task.burndown.chart.report",
    type: "graph",
    arch: `
        <graph type="line" js_class="burndown_chart">
            <field name="date" string="Date" interval="month"/>
            <field name="stage_id"/>
            <field name="is_closed"/>
            <field name="nb_tasks" type="measure"/>
        </graph>
    `,
};

async function mountViewWithSearch(mountViewContext = null) {
    await mountView({
        ...mountViewParams,
        searchViewId: false,
        searchViewArch: `
            <search string="Burndown Chart">
                <filter name="date" context="{'group_by': 'date'}"/>
                <filter name="stage" context="{'group_by': 'stage_id'}"/>
                <filter name="is_closed" context="{'group_by': 'is_closed'}"/>
            </search>
        `,
        context: mountViewContext || {
            search_default_date: 1,
            search_default_stage: 1,
        },
    });
}

async function toggleGroupBy(fieldLabel) {
    await toggleSearchBarMenu();
    await toggleMenuItem(fieldLabel);
}

function checkGroupByOrder() {
    const searchFacets = queryAll(".o_facet_value");
    expect(searchFacets).toHaveCount(2);
    const [dateSearchFacet, stageSearchFacet] = searchFacets;
    expect(dateSearchFacet).toHaveText("Date: Month");
    expect(stageSearchFacet).toHaveText("Stage");
}

test("burndown.chart: check that the sort buttons are invisible", async () => {
    await mountView(mountViewParams);
    expect(".o_cp_bottom_left:has(.btn-group[role=toolbar][aria-label='Sort graph'])").toHaveCount(
        0,
        {
            message: "The sort buttons shouldn't be rendered",
        }
    );
});

test("burndown.chart: check that removing the group by 'Date: Month > Stage' in the search bar triggers a notification", async () => {
    await mountViewWithSearch();
    await click(".o_facet_remove");
    // Only the notification will be triggered and the file won't be uploaded.
    expect.verifySteps(["notification"]);
});

test("burndown.chart: check that removing the group by 'Date' triggers a notification", async () => {
    await mountViewWithSearch();
    await toggleGroupBy("Date");
    await toggleMenuItemOption("Date", "Month");
    // Only the notification will be triggered and the file won't be uploaded.
    expect.verifySteps(["notification"]);
});

test("burndown.chart: check that adding a group by 'Date' actually toggles it", async () => {
    await mountViewWithSearch();
    await toggleGroupBy("Date");
    await toggleMenuItemOption("Date", "Year");
    expect(".o_accordion_values .selected").toHaveCount(1, {
        message: "There should be only one selected item",
    });
    expect(".o_accordion_values .selected").toHaveText("Year", {
        message: "The selected item should be the one we clicked on",
    });
});

test("burndown.chart: check that groupby 'Date > Stage' results in 'Date > Stage'", async () => {
    await mountViewWithSearch({
        search_default_date: 1,
        search_default_stage: 1,
    });
    checkGroupByOrder();
});

test("burndown.chart: check that groupby 'Stage > Date' results in 'Date > Stage'", async () => {
    await mountViewWithSearch({
        search_default_stage: 1,
        search_default_date: 1,
    });
    checkGroupByOrder();
});

test("burndown.chart: check the toggle between 'Stage' and 'Burnup chart'", async () => {
    await mountViewWithSearch();
    await toggleGroupBy("Stage");
    const searchFacets = queryAll(".o_facet_value");
    expect(searchFacets).toHaveCount(2);

    const [dateSearchFacet, stageSearchFacet] = searchFacets;
    expect(dateSearchFacet).toHaveText("Date: Month");
    expect(stageSearchFacet).toHaveText("Burnup chart");
    await toggleMenuItem("Burnup chart");
    checkGroupByOrder();
});
