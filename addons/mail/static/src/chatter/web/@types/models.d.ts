declare module "models" {
    import { ScheduledMessage as ScheduledMessageClass } from "@mail/chatter/web/scheduled_message_model";

    export interface ScheduledMessage extends ScheduledMessageClass {}

    export interface DiscussChannel {
        scheduledMessages: ScheduledMessage[];
    }
    export interface Store {
        "mail.scheduled.message": StaticMailRecord<ScheduledMessage, typeof ScheduledMessageClass>;
    }
    export interface Thread {
        scheduledMessages: ScheduledMessage[];
    }

    export interface Models {
        "mail.scheduled.message": ScheduledMessage;
    }
}
