import { ActivityMenu } from "@mail/core/web/activity_menu";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    makeMockEnv,
    mockService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

// hr.leave declares no _systray_view, so the server hands the activity systray
// a group asking for the list view (mail/models/res_users.py). On a phone that
// list needs sideways scrolling before the approve/refuse buttons are reachable.
const LEAVE_GROUP = {
    id: 1,
    model: "hr.leave",
    name: "Time Off",
    activity_ids: [1],
    view_type: "list",
};

async function openGroupWith({ isSmall, group }) {
    const env = await makeMockEnv();
    Object.defineProperty(env, "isSmall", { get: () => isSmall });

    let openedWith;
    mockService("action", {
        doAction(action, options) {
            openedWith = options;
        },
    });

    const menu = await mountWithCleanup(ActivityMenu, { env });
    menu.openActivityGroup({ ...group });
    return openedWith;
}

test("time off opens as a kanban on a small screen", async () => {
    const options = await openGroupWith({ isSmall: true, group: LEAVE_GROUP });
    expect(options.viewType).toBe("kanban");
});

test("time off still opens as a list on a desktop", async () => {
    const options = await openGroupWith({ isSmall: false, group: LEAVE_GROUP });
    expect(options.viewType).toBe("list");
});

test("other models are left alone on a small screen", async () => {
    const options = await openGroupWith({
        isSmall: true,
        group: { ...LEAVE_GROUP, model: "res.partner" },
    });
    expect(options.viewType).toBe("list");
});
