declare module "models" {
    import { CrmLead as CrmLeadClass } from "@crm/core/common/crm_lead_model";

    export interface CrmLead extends CrmLeadClass {}

    export interface Store {
        "crm.lead": StaticMailRecord<CrmLead, typeof CrmLeadClass>;
    }

    export interface Models {
        "crm.lead": CrmLead;
    }
}
