declare module "models" {
    import { CrmLead as CrmLeadClass } from "@crm/core/common/crm_lead_model";

    export interface CrmLead extends CrmLeadClass {}

    export interface DiscussChannel {
        allowCreateLead: Readonly<boolean>;
    }

    export interface Store {
        has_access_create_lead: boolean;
        channel_types_with_lead_command: Array<DiscussChannel["channel_type"]>;
        "crm.lead": StaticMailRecord<CrmLead, typeof CrmLeadClass>;
    }

    export interface Models {
        "crm.lead": CrmLead;
    }
}
