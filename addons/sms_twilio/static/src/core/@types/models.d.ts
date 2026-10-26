declare module "models" {
    import { Notification as NotificationClass } from "@mail/core/common/notification_model";

    export interface Notification extends Patch<NotificationClass, typeof import("@sms_twilio/core/notification_model").notificationPatch> {}
}
