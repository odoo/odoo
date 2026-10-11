declare module "models" {
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { Store as StoreClass } from "@mail/core/common/store_plugin";

    export interface Message extends Patch<MessageClass, typeof import("@crm_livechat/core/common/message_model_patch").messagePatch> {}
    export interface Store extends Patch<StoreClass, typeof import("@crm_livechat/core/common/store_service_patch").storePatch> {
        has_access_create_lead: boolean;
    }
}
