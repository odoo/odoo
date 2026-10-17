declare module "models" {
    import { Message as MessageClass } from "@mail/core/common/message_model";

    export interface Message extends Patch<MessageClass, typeof import("@portal/core/common/message_model_patch").messagePatch> {
        is_internal: boolean|undefined;
        is_message_subtype_note: boolean|undefined;
        published_date_str: string|undefined;
    }
}
