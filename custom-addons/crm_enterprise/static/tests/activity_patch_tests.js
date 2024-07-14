/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { registry } from "@web/core/registry";

import { start } from "@mail/../tests/helpers/test_utils";

import { click } from "@web/../tests/utils";

const serviceRegistry = registry.category("services");

QUnit.module("activity (patch)");

QUnit.test("click on activity Lead/Opportunity clock should open crm.lead view", async (assert) => {
    const pyEnv = await startServer();
    const leadId = pyEnv["crm.lead"].create({});
    pyEnv["mail.activity"].create({
        res_id: leadId,
        res_model: "crm.lead",
    });
    const views = {
        "crm.lead,false,pivot": ` <pivot string="crm.lead"><field name="name" /></pivot>`,
        "crm.lead,false,cohort": `<cohort date_start="start" date_stop="stop"/>`,
        "crm.lead,false,map": `<map routing="1"><field name="name"/></map>`,
    };
    const mockedActionService = {
        start() {
            return {
                doAction(params) {
                    assert.step(params);
                },
                loadState(state, options) {
                    return Promise.resolve(true);
                },
            };
        },
    };
    serviceRegistry.add("action", mockedActionService, { force: true });
    await start({ serverData: { views } });
    await click(".o_menu_systray i[aria-label='Activities']");
    await click(".o-mail-ActivityGroup");
    assert.verifySteps(['crm.crm_lead_action_my_activities']);
});
