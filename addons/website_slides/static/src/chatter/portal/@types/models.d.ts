declare module "models" {
    import { Message as MessageClass } from "@mail/core/common/message_model";

    export interface Message extends Patch<MessageClass, typeof import("@website_slides/chatter/portal/message_model_patch").messagePatch> {}
}
