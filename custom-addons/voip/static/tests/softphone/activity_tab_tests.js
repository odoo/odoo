/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("activity_tab");

QUnit.test("Today call activities are displayed in the “Next Activities” tab.", async () => {
    const pyEnv = await startServer();
    const [activityTypeId] = pyEnv["mail.activity.type"].search([["category", "=", "phonecall"]]);
    const [partnerId1, partnerId2] = pyEnv["res.partner"].create([
        {
            name: "Françoise Délire",
            display_name: "Boulangerie Vortex, Françoise Délire",
            mobile: "+1 246 203 6982",
        },
        {
            name: "Naomi Dag",
            display_name: "Sanit’Hair, Naomi Dag",
            phone: "777 2124",
        },
    ]);
    pyEnv["mail.activity"].create([
        {
            activity_type_id: activityTypeId,
            date_deadline: "1999-01-29",
            res_id: partnerId1,
            res_model: "res.partner",
            user_id: pyEnv.currentUserId,
        },
        {
            activity_type_id: activityTypeId,
            date_deadline: "2016-08-06",
            res_id: partnerId2,
            res_model: "res.partner",
            user_id: pyEnv.currentUserId,
        },
    ]);
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-ActivitiesTab .list-group-item-action", { count: 2 });
    await contains(".o-voip-ActivitiesTab .list-group-item-action", {
        text: "Boulangerie Vortex, Françoise Délire",
    });
    await contains(".o-voip-ActivitiesTab .list-group-item-action", {
        text: "Sanit’Hair, Naomi Dag",
    });
});

QUnit.test(
    "The name of the partner linked to an activity is displayed in the activity tab.",
    async () => {
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
                user_id: pyEnv.currentUserId,
            },
        ]);
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await contains(".o-voip-ActivitiesTab .list-group-item-action .fw-bold", {
            text: "Gwendoline Zumba",
        });
    }
);

QUnit.test("Clicking on an activity opens the correspondence details", async () => {
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
            user_id: pyEnv.currentUserId,
        },
    ]);
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-ActivitiesTab .list-group-item-action", { text: "Yveline Colbert" });
    await contains(".o-voip-CorrespondenceDetails");
});
