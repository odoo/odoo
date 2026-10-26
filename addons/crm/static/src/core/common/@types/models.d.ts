declare module "models" {
    import { CrmLead as CrmLeadClass } from "@crm/core/common/crm_lead_model";
    import { ResPartner as ResPartnerClass } from "@mail/core/common/res_partner_model";

    export interface CrmLead extends CrmLeadClass {}

    export interface ResPartner extends Patch<ResPartnerClass, typeof import("@crm/core/common/res_partner_model_patch").resPartnerPatch> {}
    export interface Store {
        "crm.lead": StaticMailRecord<CrmLead, typeof CrmLeadClass>;
    }
    export interface Models {
        "crm.lead": CrmLead;
    }
}
