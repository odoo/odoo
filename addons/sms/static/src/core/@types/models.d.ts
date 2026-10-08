declare module "models" {
    import { Failure as FailureClass } from "@mail/core/common/failure_model";
    import { Notification as NotificationClass } from "@mail/core/common/notification_model";

    export interface Failure extends Patch<FailureClass, typeof import("@sms/core/failure_model_patch").failurePatch> {}
    export interface Notification extends Patch<NotificationClass, typeof import("@sms/core/notification_model_patch").notificationPatch> {}
}
