import { expect, test, describe } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";

import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { ProjectRightSidePanel } from "@project/components/project_right_side_panel/project_right_side_panel";

defineMailModels();
describe.current.tags("desktop");

const FAKE_DATA = {
    "user": {
        "is_project_user": true,
    },
    "buttons": [
        {
            "icon": "check",
            "text": "Tasks",
            "number": "0 / 0",
            "action_type": "object",
            "action": "action_view_tasks",
            "show": true,
            "sequence": 1,
        }
    ],
    "show_project_profitability_helper": false,
    "milestones": {
        "data": [
            {
                "id": 1,
                "name": "Milestone Zero",
            }
        ]
    },
    "profitability_items": {
        "costs": {
            "data": []
        },
        "revenues": {
            "data": []
        },
    },
}


test("Right side panel will not be rendered without data", async () => {
    onRpc(() => {
        const deepCopy = JSON.parse(JSON.stringify(FAKE_DATA))
        deepCopy.buttons.pop();
        deepCopy.milestones.data.pop();
        return { ...deepCopy };
    });

    await mountWithCleanup(ProjectRightSidePanel, {
        props: {
            context: { active_id: 1 },
            domain: new Array(),
        },
    });

    expect(queryAll('div.o_rightpanel').length).toBe(0);
});

test("Right side panel will be only rendered data", async () => {
    onRpc(() => {
        return { ...FAKE_DATA };
    });

    await mountWithCleanup(ProjectRightSidePanel, {
        props: {
            context: { active_id: 1 },
            domain: new Array(),
        },
    });

    expect(queryAll('div.o_rightpanel').length).toBe(1);
});
