/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("correspondence_details");

QUnit.test("Clicking on the “open record” button opens the corresponding record.", async () => {
    const pyEnv = await startServer();
    const [activityTypeId] = pyEnv["mail.activity.type"].search([["category", "=", "phonecall"]]);
    const leadId = pyEnv["crm.lead"].create({
        phone: "+1 246 203 6982",
        name: "Vincent's Birthday",
    });
    pyEnv["mail.activity"].create({
        activity_type_id: activityTypeId,
        date_deadline: "1998-08-13",
        res_id: leadId,
        res_model: "crm.lead",
        user_id: pyEnv.currentUserId,
    });
    await start({
        serverData: {
            views: {
                "crm.lead,false,form": "<form></form>",
            },
        },
    });
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-ActivitiesTab .list-group-item-action", { text: "Vincent's Birthday" });
    await contains(".o_form_view", { count: 0 });
    await click(".o-voip-CorrespondenceDetails button .fa-wpforms");
    await contains(".o_form_view");
});
