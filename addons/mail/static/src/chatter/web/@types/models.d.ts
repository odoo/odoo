declare module "models" {
    import { ScheduledMessage as ScheduledMessageClass } from "@mail/chatter/web/scheduled_message_model";

    export interface ScheduledMessage extends ScheduledMessageClass{}

    export interface Models {
        "ScheduledMessage": ScheduledMessage,
    }
