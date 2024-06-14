import { CRMLead } from "@crm/../tests/mock_server/mock_models/crm_lead";
import { mailModels } from "@mail/../tests/mail_test_helpers";

export const crmModels = { ...mailModels, CRMLead };
