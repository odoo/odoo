import { defineModels } from "@web/../tests/web_test_helpers";
import { CRMLead } from "@voip_crm/../tests/mock_server/mock_models/crm_lead";
import { voipModels } from "@voip/../tests/voip_test_helpers";

export function defineVoipCRMModels() {
    return defineModels(voipCRMModels);
}

export const voipCRMModels = { ...voipModels, CRMLead };
