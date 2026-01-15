import { CrmLead } from "@crm/../tests/mock_server/mock_models/crm_lead";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const crmModels = {
    ...mailModels,
    CrmLead
};

export function defineCrmModels() {
    defineModels(crmModels);
}
