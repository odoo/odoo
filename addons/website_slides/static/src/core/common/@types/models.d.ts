declare module "models" {
    import { Activity as ActivityClass } from "@mail/core/common/activity_model";
    import { Thread as ThreadClass } from "@mail/core/common/thread_model";

    export interface Activity extends Patch<ActivityClass, typeof import("@website_slides/core/common/activity_model_patch").activityPatch> {
        request_partner_id: ResPartner;
    }
    export interface Thread extends Patch<ThreadClass, typeof import("@website_slides/core/common/thread_model_patch").threadPatch> {
        comments_count: number|undefined;
    }
}
