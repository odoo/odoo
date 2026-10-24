declare module "models" {
    import { Composer as ComposerClass } from "@mail/core/common/composer_model";
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface Composer extends Patch<ComposerClass, typeof import("@portal/chatter/portal/composer_model_patch").composerPatch> {
        portalComment: boolean;
    }
    export interface Message extends Patch<MessageClass, typeof import("@portal/chatter/portal/message_model_patch").messagePatch> {}
    export interface Thread extends Patch<ThreadClass, typeof import("@portal/chatter/portal/thread_model_patch").threadPatch> {}
}
