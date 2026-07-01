declare module "models" {
    export interface DiscussChannel {
        allowCreateLead: Readonly<boolean>;
    }
    export interface Store {
        channel_types_with_create_lead: Array<DiscussChannel["channel_type"]>;
    }
}
