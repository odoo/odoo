declare module "models" {
    import { Composer as ComposerClass } from "@mail/core/common/composer_model";
    import { Message as MessageClass } from "@mail/core/common/message_model";
    import { Store as StoreClass } from "@mail/core/common/store_plugin";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface Composer extends Patch<ComposerClass, typeof import("@portal_rating/chatter/portal/composer_model_patch").composerPatch> {}
    export interface Message extends Patch<MessageClass, typeof import("@portal_rating/chatter/portal/message_model_patch").messagePatch> {}
    export interface Store extends Patch<StoreClass, typeof import("@portal_rating/chatter/portal/store_service_patch").storePatch> {}
    export interface Thread extends Patch<ThreadClass, typeof import("@portal_rating/chatter/portal/thread_model_patch").threadPatch> {
        ratingChatter: boolean;
        reviewChatter: boolean;
        selectedRating: false|number;
    }
}
