import { defineModels } from "@web/../tests/web_test_helpers";
import { crmModels } from "@crm/../tests/crm_test_helpers";

export function defineCRMEnterpriseModels() {
    return defineModels(crmEnterpriseModels);
}

export const crmEnterpriseModels = { ...crmModels };
