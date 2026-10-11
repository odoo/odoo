declare module "models" {
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface Thread extends Patch<ThreadClass, typeof import("@portal/chatter/portal_project/thread_model_patch").threadPatch> {}
}
