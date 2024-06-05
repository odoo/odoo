import { expect, test, describe } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";

import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { ProjectRightSidePanel } from "@project/components/project_right_side_panel/project_right_side_panel";

defineMailModels();
describe.current.tags("desktop");

const FAKE_DATA = {
    user: {
        is_project_user: true,
    },
    buttons: [
        {
            icon: "check",
            text: "Tasks",
            number: "0 / 0",
            action_type: "object",
            action: "action_view_tasks",
            show: true,
            sequence: 1,
        },
    ],
    show_project_profitability_helper: false,
    show_milestones: true,
    milestones: {
        data: [
            {
                id: 1,
                name: "Milestone Zero",
            },
        ],
    },
    profitability_items: {
        costs: {
            data: [],
        },
        revenues: {
            data: [],
        },
    },
};

test("Right side panel will not be rendered without data and settings set false", async () => {
    onRpc(() => {
        const deepCopy = JSON.parse(JSON.stringify(FAKE_DATA));
        deepCopy.buttons.pop();
        deepCopy.milestones.data.pop();
        deepCopy.show_milestones = false;
        return { ...deepCopy };
    });

    await mountWithCleanup(ProjectRightSidePanel, {
        props: {
            context: { active_id: 1 },
            domain: new Array(),
        },
    });

    expect(queryAll("div.o_rightpanel").length).toBe(0, {
        message: "Right panel should not be rendered",
    });
});

test("Right side panel will be rendered if settings are turned on but doesnt have any data", async () => {
    onRpc(() => {
        const deepCopy = JSON.parse(JSON.stringify(FAKE_DATA));
        deepCopy.buttons.pop();
        deepCopy.milestones.data.pop();
        deepCopy.show_milestones = true;
        return { ...deepCopy };
    });

    await mountWithCleanup(ProjectRightSidePanel, {
        props: {
            context: { active_id: 1 },
            domain: new Array(),
        },
    });

    expect(queryAll("div.o_rightpanel").length).toBe(1, {
        message: "Right panel should be rendered",
    });
});

test("Right side panel will be not rendered if settings are turned off but does have data", async () => {
    onRpc(() => {
        const deepCopy = JSON.parse(JSON.stringify(FAKE_DATA));
        deepCopy.show_milestones = false;
        return { ...deepCopy };
    });

    await mountWithCleanup(ProjectRightSidePanel, {
        props: {
            context: { active_id: 1 },
            domain: new Array(),
        },
    });

    expect(queryAll("div.o_rightpanel").length).toBe(0, {
        message: "Right panel should not be rendered",
    });
});

test("Right side panel will be rendered if both setting is turned on and does have data", async () => {
    onRpc(() => {
        return { ...FAKE_DATA };
    });

    await mountWithCleanup(ProjectRightSidePanel, {
        props: {
            context: { active_id: 1 },
            domain: new Array(),
        },
    });

    expect(queryAll("div.o_rightpanel").length).toBe(1, {
        message: "Right panel should be rendered",
    });
});
