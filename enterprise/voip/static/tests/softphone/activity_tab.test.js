import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Today call activities are displayed in the “Next Activities” tab.", async () => {
    const pyEnv = await startServer();
    const [activityTypeId] = pyEnv["mail.activity.type"].search([["category", "=", "phonecall"]]);
    const [partnerId1, partnerId2] = pyEnv["res.partner"].create([
        {
            name: "Françoise Délire",
            mobile: "+1 246 203 6982",
            company_name: "Boulangerie Vortex",
        },
        {
            name: "Naomi Dag",
            phone: "777 2124",
            company_name: "Sanit’Hair",
        },
    ]);
    pyEnv["mail.activity"].create([
        {
            activity_type_id: activityTypeId,
            date_deadline: "1999-01-29",
            res_id: partnerId1,
            res_model: "res.partner",
            user_id: serverState.userId,
        },
        {
            activity_type_id: activityTypeId,
            date_deadline: "2016-08-06",
            res_id: partnerId2,
            res_model: "res.partner",
            user_id: serverState.userId,
        },
    ]);
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-ActivitiesTab .list-group-item-action", { count: 2 });
    await contains(".o-voip-ActivitiesTab .list-group-item-action", {
        text: "Boulangerie Vortex, Françoise Délire",
    });
    await contains(".o-voip-ActivitiesTab .list-group-item-action", {
        text: "Sanit’Hair, Naomi Dag",
    });
});

test("The name of the partner linked to an activity is displayed in the activity tab.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Gwendoline Zumba",
        mobile: "515-555-0104",
    });
    pyEnv["mail.activity"].create([
        {
            activity_type_id: pyEnv["mail.activity.type"].search([
                ["category", "=", "phonecall"],
            ])[0],
            date_deadline: "2017-08-13",
            res_id: partnerId,
            res_model: "res.partner",
            user_id: serverState.userId,
        },
    ]);
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-ActivitiesTab .list-group-item-action .fw-bold", {
        text: "Gwendoline Zumba",
    });
});

test("Clicking on an activity opens the correspondence details", async () => {
    mockDate("2024-05-23 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Yveline Colbert",
        phone: "456 284 9936",
    });
    pyEnv["mail.activity"].create([
        {
            activity_type_id: pyEnv["mail.activity.type"].search([
                ["category", "=", "phonecall"],
            ])[0],
            date_deadline: "2022-11-16",
            res_id: partnerId,
            res_model: "res.partner",
            user_id: serverState.userId,
        },
    ]);
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-ActivitiesTab .list-group-item-action", { text: "Yveline Colbert" });
    await contains(".o-voip-CorrespondenceDetails");
});
