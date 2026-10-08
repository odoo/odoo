declare module "models" {
    import { Activity as ActivityClass } from "@mail/core/common/activity_model";
    import { MessagingMenu as MessagingMenuClass } from "@mail/core/public_web/messaging_menu/messaging_menu_model";
    import { Store as StoreClass } from "@mail/core/common/store_plugin";

    export interface Activity extends Patch<ActivityClass, typeof import("@calendar/core/web/activity_model_patch").activityPatch> {
        calendar_event_id: CalendarEvent;
    }
    export interface MessagingMenu extends Patch<MessagingMenuClass, typeof import("@calendar/core/web/messaging_menu_model_patch").messagingMenuModelPatch> {}
    export interface Store extends Patch<StoreClass, typeof import("@calendar/core/web/store_service_patch").StorePatch, "onUpdateActivityGroups"> {}
}
