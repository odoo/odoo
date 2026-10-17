declare module "models" {
    import { Failure as FailureClass } from "@mail/core/common/failure_model";
    import { Notification as NotificationClass } from "@mail/core/common/notification_model";

    export interface Failure extends Patch<FailureClass, typeof import("@snailmail/core/failure_model_patch").failurePatch, "iconSrc"> {}
    export interface Notification extends Patch<NotificationClass, typeof import("@snailmail/core/notification_model_patch").notificationPatch> {}
}
