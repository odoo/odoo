import { describe, expect, test } from "@odoo/hoot";
import { contains, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("check that the sort buttons are invisible", async () => {
    await mountView({
        resModel: "project.task.burndown.chart.report",
        type: "graph",
    });
    expect(`.o_cp_bottom_left:has(.btn-group[role=toolbar][aria-label="Sort graph"])`).not.toBeDisplayed();
});

test("check that removing the group by 'Date: Month > Stage' in the search bar triggers a notification", async () => {
    onRpc("project.task.burndown.chart.report", "web_read_group", () => {
        expect.step("notification_triggered");
    });
    await mountView({
        resModel: "project.task.burndown.chart.report",
        type: "graph",
        searchViewArch: `
            <search string="Burndown Chart">
                <filter string="Date" name="date" context="{'group_by': 'date'}" />
                <filter string="Stage - Burndown chart" name="stage" context="{'group_by': 'stage_id'}" />
                <filter string="Is Closed - Burnup chart" name="is_closed" context="{'group_by': 'is_closed'}"/>
            </search>`,
        context: { search_default_date: 1, search_default_stage: 1 },
    });
    expect(["notification_triggered"]).toVerifySteps();
    await contains(".o_facet_remove").click();
    expect(["notification_triggered"]).toVerifySteps();
});

test("check that removing the group by 'Date' triggers a notification", async () => {
    onRpc("project.task.burndown.chart.report", "web_read_group", () => {
        expect.step("notification_triggered");
    });

    await mountView({
        resModel: "project.task.burndown.chart.report",
        type: "graph",
        searchViewArch: `
            <search string="Burndown Chart">
                <filter string="Date" name="date" context="{'group_by': 'date'}" />
                <filter string="Stage - Burndown chart" name="stage" context="{'group_by': 'stage_id'}" />
                <filter string="Is Closed - Burnup chart" name="is_closed" context="{'group_by': 'is_closed'}"/>
            </search>`,
        context: { search_default_date: 1 },
    });
    expect(["notification_triggered"]).toVerifySteps();
    await contains(".o_facet_remove").click();
    expect(["notification_triggered"]).toVerifySteps();
});

test("check that adding a group by 'Date' actually toggle it", async () => {
    await mountView({
        resModel: "project.task.burndown.chart.report",
        type: "graph",
        searchViewArch: `
            <search string="Burndown Chart">
                <filter string="Date" name="date" context="{'group_by': 'date'}" />
                <filter string="Stage - Burndown chart" name="stage" context="{'group_by': 'stage_id'}" />
                <filter string="Is Closed - Burnup chart" name="is_closed" context="{'group_by': 'is_closed'}"/>
            </search>`,
    });
    await contains(".o_searchview_input").click();
    await contains(".o_group_by_menu button").click();
    await contains(".o_group_by_menu .o_accordion_values .dropdown-item").click();
    expect("span.o_item_option.selected").toBeVisible();
});

test("check that the group by is always sorted 'Date' first, 'Stage' second", async () => {
    await mountView({
        resModel: "project.task.burndown.chart.report",
        type: "graph",
        searchViewArch: `
            <search string="Burndown Chart">
                <filter string="Date" name="date" context="{'group_by': 'date'}" />
                <filter string="Stage - Burndown chart" name="stage" context="{'group_by': 'stage_id'}" />
                <filter string="Is Closed - Burnup chart" name="is_closed" context="{'group_by': 'is_closed'}"/>
            </search>`,
        context: { search_default_date: 1, search_default_stage: 1 },
    });
    expect(".o_facet_value").toHaveCount(2);
    const facets = document.querySelectorAll(".o_facet_value");
    expect(facets[0]).toHaveText("Date: Month");
    expect(facets[1]).toHaveText("Stage - Burndown chart");
});

test("check that the group by is always sorted 'Date' first, 'Stage' second, even with switched context", async () => {
    await mountView({
        resModel: "project.task.burndown.chart.report",
        type: "graph",
        searchViewArch: `
            <search string="Burndown Chart">
                <filter string="Date" name="date" context="{'group_by': 'date'}" />
                <filter string="Stage - Burndown chart" name="stage" context="{'group_by': 'stage_id'}" />
                <filter string="Is Closed - Burnup chart" name="is_closed" context="{'group_by': 'is_closed'}"/>
            </search>`,
        context: { search_default_stage: 1, search_default_date: 1 },
    });
    expect(".o_facet_value").toHaveCount(2);
    const facets = document.querySelectorAll(".o_facet_value");
    expect(facets[0]).toHaveText("Date: Month");
    expect(facets[1]).toHaveText("Stage - Burndown chart");
});

test("check that the toggle between 'Stage' and 'Burnup chart' are working as intended", async () => {
    await mountView({
        resModel: "project.task.burndown.chart.report",
        type: "graph",
        searchViewArch: `
            <search string="Burndown Chart">
                <filter string="Date" name="date" context="{'group_by': 'date'}" />
                <filter string="Stage - Burndown chart" name="stage" context="{'group_by': 'stage_id'}" />
                <filter string="Is Closed - Burnup chart" name="is_closed" context="{'group_by': 'is_closed'}"/>
            </search>`,
        context: { search_default_stage: 1 },
    });
    await contains(".o_searchview_input").click();
    const menuItems = document.querySelectorAll(".o_group_by_menu span.dropdown-item");
    await contains(menuItems[1]).click();
    expect(".o_facet_value").toHaveCount(2);
    const facets = document.querySelectorAll(".o_facet_value");
    expect(facets[0]).toHaveText("Stage - Burndown chart");
    expect(facets[1]).toHaveText("Is Closed - Burnup chart");
});
