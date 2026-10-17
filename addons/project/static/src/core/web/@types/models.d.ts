declare module "models" {
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface Thread extends Patch<ThreadClass, typeof import("@project/core/web/thread_model_patch").threadPatch> {
        collaborator_ids: ResPartner[];
    }
}
