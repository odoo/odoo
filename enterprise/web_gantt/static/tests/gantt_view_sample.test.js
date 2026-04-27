import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryFirst, queryAll } from "@odoo/hoot-dom";
import { mockDate, animationFrame } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import {
    getService,
    mountWithCleanup,
    switchView,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { Tasks, defineGanttModels } from "./gantt_mock_models";
import { SELECTORS, mountGanttView } from "./web_gantt_test_helpers";

import { Domain } from "@web/core/domain";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

defineGanttModels();
beforeEach(() => mockDate("2018-12-20T08:00:00", +1));

test(`empty grouped gantt with sample="1"`, async () => {
    Tasks._views = {
        gantt: `<gantt date_start="start" date_stop="stop" sample="1"/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [
            [false, "gantt"],
            [false, "graph"],
        ],
        domain: Domain.FALSE.toList(),
        groupBy: ["project_id"],
    });
    await animationFrame();

    expect(SELECTORS.viewContent).toHaveClass("o_view_sample_data");
    expect(queryAll(SELECTORS.pill).length).toBeWithin(0, 16);
    expect(SELECTORS.noContentHelper).toHaveCount(1);

    const content = queryFirst(SELECTORS.viewContent).innerHTML;
    await switchView("gantt");
    await animationFrame();
    expect(SELECTORS.viewContent).toHaveClass("o_view_sample_data");
    expect(SELECTORS.viewContent).toHaveProperty("innerHTML", content);
    expect(SELECTORS.noContentHelper).toHaveCount(1);
});

test("empty gantt with sample data and default_group_by", async () => {
    Tasks._views = {
        gantt: `<gantt date_start="start" date_stop="stop" sample="1" default_group_by="project_id"/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [
            [false, "gantt"],
            [false, "graph"],
        ],
        domain: Domain.FALSE.toList(),
    });
    await animationFrame();

    expect(SELECTORS.viewContent).toHaveClass("o_view_sample_data");
    expect(queryAll(SELECTORS.pill).length).toBeWithin(0, 16);
    expect(SELECTORS.noContentHelper).toHaveCount(1);

    const content = queryFirst(SELECTORS.viewContent).innerHTML;
    await switchView("gantt");
    await animationFrame();

    expect(SELECTORS.viewContent).toHaveClass("o_view_sample_data");
    expect(SELECTORS.viewContent).toHaveProperty("innerHTML", content);
    expect(SELECTORS.noContentHelper).toHaveCount(1);
});

test("empty gantt with sample data and default_group_by (switch view)", async () => {
    Tasks._views = {
        gantt: `<gantt date_start="start" date_stop="stop" sample="1" default_group_by="project_id"/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [
            [false, "gantt"],
            [false, "list"],
        ],
        domain: Domain.FALSE.toList(),
    });
    await animationFrame();

    // the gantt view should be in sample mode
    expect(SELECTORS.viewContent).toHaveClass("o_view_sample_data");
    expect(queryAll(SELECTORS.pill).length).toBeWithin(0, 16);
    expect(SELECTORS.noContentHelper).toHaveCount(1);
    const content = queryFirst(SELECTORS.viewContent).innerHTML;

    // switch to list view
    await switchView("list");
    expect(SELECTORS.view).toHaveCount(0);

    // go back to gantt view
    await switchView("gantt");
    await animationFrame();

    expect(SELECTORS.view).toHaveCount(1);

    // the gantt view should be still in sample mode
    expect(SELECTORS.viewContent).toHaveClass("o_view_sample_data");
    expect(SELECTORS.noContentHelper).toHaveCount(1);
    expect(SELECTORS.viewContent).toHaveProperty("innerHTML", content);
});

test(`empty gantt with sample="1"`, async () => {
    Tasks._views = {
        gantt: `<gantt date_start="start" date_stop="stop" sample="1"/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "tasks",
        type: "ir.actions.act_window",
        views: [
            [false, "gantt"],
            [false, "graph"],
        ],
        domain: Domain.FALSE.toList(),
    });
    await animationFrame();
    expect(SELECTORS.viewContent).toHaveClass("o_view_sample_data");
    expect(queryAll(SELECTORS.pill).length).toBeWithin(0, 16);
    expect(SELECTORS.noContentHelper).toHaveCount(1);

    const content = queryFirst(SELECTORS.viewContent).innerHTML;

    await switchView("gantt");
    await animationFrame();
    expect(SELECTORS.viewContent).toHaveClass("o_view_sample_data");
    expect(SELECTORS.viewContent).toHaveProperty("innerHTML", content);
    expect(SELECTORS.noContentHelper).toHaveCount(1);
});

test(`non empty gantt with sample="1"`, async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="year" sample="1"/>`,
        searchViewArch: `
            <search>
                <filter name="filter" string="False Domain" domain="[(0, '=', 1)]"/>
            </search>
        `,
    });
    expect(SELECTORS.viewContent).not.toHaveClass("o_view_sample_data");
    expect(SELECTORS.cell).toHaveCount(12);
    expect(SELECTORS.pill).toHaveCount(7);
    expect(SELECTORS.noContentHelper).toHaveCount(0);

    await toggleSearchBarMenu();
    await toggleMenuItem("False Domain");
    expect(SELECTORS.viewContent).not.toHaveClass("o_view_sample_data");
    expect(SELECTORS.pill).toHaveCount(0);
    expect(SELECTORS.noContentHelper).toHaveCount(0);
    expect(SELECTORS.cell).toHaveCount(12);
});

test(`non empty grouped gantt with sample="1"`, async () => {
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" default_scale="year" sample="1"/>`,
        groupBy: ["project_id"],
        searchViewArch: `
            <search>
                <filter name="filter" string="False Domain" domain="[(0, '=', 1)]"/>
            </search>
        `,
    });
    expect(SELECTORS.viewContent).not.toHaveClass("o_view_sample_data");
    expect(SELECTORS.cell).toHaveCount(24);
    expect(SELECTORS.pill).toHaveCount(7);

    await toggleSearchBarMenu();
    await toggleMenuItem("False Domain");
    expect(SELECTORS.viewContent).not.toHaveClass("o_view_sample_data");
    expect(SELECTORS.pill).toHaveCount(0);
    expect(SELECTORS.noContentHelper).toHaveCount(0);
    expect(SELECTORS.cell).toHaveCount(12);
});

test("no content helper from action when no data and sample mode", async () => {
    Tasks._records = [];
    await mountGanttView({
        resModel: "tasks",
        arch: `<gantt date_start="start" date_stop="stop" sample="1"/>`,
        noContentHelp: markup(`<p class="hello">click to add a partner</p>`),
    });
    expect(SELECTORS.noContentHelper).toHaveCount(1);
    expect(`${SELECTORS.noContentHelper} p.hello:contains(add a partner)`).toHaveCount(1);
});
