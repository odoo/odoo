import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";
import { describe, test } from "@odoo/hoot";
import { defineVoipCRMModels } from "@voip_crm/../tests/voip_crm_test_helpers";

describe.current.tags("desktop");
defineVoipCRMModels();

test("Clicking on the “open record” button opens the corresponding record.", async () => {
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
        user_id: serverState.userId,
    });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-ActivitiesTab .list-group-item-action", { text: "Vincent's Birthday" });
    await contains(".o_form_view", { count: 0 });
    await click(".o-voip-CorrespondenceDetails button .fa-wpforms");
    await contains(".o_form_view");
});
