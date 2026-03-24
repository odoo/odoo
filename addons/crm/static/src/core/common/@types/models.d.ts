declare module "models" {
    export interface DiscussChannel {
        allowCreateLead: Readonly<boolean>;
    }
    export interface Store {
        has_access_create_lead: boolean;
        channel_types_with_create_lead: Array<DiscussChannel["channel_type"]>;
    }
}
