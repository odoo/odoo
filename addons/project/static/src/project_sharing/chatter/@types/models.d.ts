declare module "models" {
    import { Message as MessageClass } from "@mail/core/common/message_model";

    export interface Message extends Patch<MessageClass, typeof import("@project/project_sharing/chatter/message_model_patch").messagePatch> {}
}
