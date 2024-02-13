declare module "mock_server" {
    import { MailNotification as MailNotificationClass } from "../mail_notification";

    export interface MailNotification extends MailNotificationClass {}

    export interface Models {
        "mail.notification": MailNotification,
    }
}