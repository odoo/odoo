import {
    assertSteps,
    click,
    start,
    startServer,
    step,
    registerArchs,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { defineCRMEnterpriseModels } from "@crm_enterprise/../tests/crm_enterprise_test_helpers";
import { mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineCRMEnterpriseModels();

test("click on activity Lead/Opportunity clock should open crm.lead view", async () => {
    const pyEnv = await startServer();
    const leadId = pyEnv["crm.lead"].create({});
    pyEnv["mail.activity"].create({
        res_id: leadId,
        res_model: "crm.lead",
    });
    registerArchs({
        "crm.lead,false,pivot": `<pivot string="crm.lead"><field name="name" /></pivot>`,
        "crm.lead,false,cohort": `<cohort date_start="start" date_stop="stop"/>`,
        "crm.lead,false,map": `<map routing="1"><field name="name"/></map>`,
    });
    mockService("action", {
        loadAction(actionId) {
            step(actionId);
            return Promise.resolve({ domain: [] });
        },
        doAction(action, options) {
            step(JSON.stringify(action));
        },
        async loadState(state, options) {
            return true;
        },
    });
    await start();
    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".o-mail-ActivityGroup");
    await assertSteps([
        "crm.crm_lead_action_my_activities",
        JSON.stringify({ domain: [["active", "in", [true, false]]] }),
    ]);
});
