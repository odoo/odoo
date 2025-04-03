import { fields, Record } from "@mail/core/common/record";
import { markRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

export class Failure extends Record {
    static nextId = markRaw({ value: 1 });
    static id = "id";

    notifications = fields.Many("mail.notification", {
        /** @this {import("models").Failure} */
        onUpdate() {
            if (this.notifications.length === 0) {
                this.delete();
            } else {
                this.store.failures.add(this);
            }
        },
    });
    get modelName() {
        return this.notifications?.[0]?.mail_message_id?.thread?.modelName;
    }
    get resModel() {
        return this.notifications?.[0]?.mail_message_id?.thread?.model;
    }
    get resIds() {
        return new Set([
            ...this.notifications
                .map((notif) => notif.mail_message_id?.thread?.id)
                .filter((id) => !!id),
        ]);
    }
    lastMessage = fields.One("mail.message", {
        /** @this {import("models").Failure} */
        compute() {
            let lastMsg = this.notifications[0]?.mail_message_id;
            for (const notification of this.notifications) {
                if (lastMsg?.id < notification.mail_message_id?.id) {
                    lastMsg = notification.mail_message_id;
                }
            }
            return lastMsg;
        },
    });
    /** @type {'sms' | 'email'} */
    get type() {
        return this.notifications?.[0]?.notification_type;
    }
    get status() {
        return this.notifications?.[0]?.notification_status;
    }

    get iconSrc() {
        return "/mail/static/src/img/smiley/mailfailure.svg";
    }

    get body() {
        if (this.notifications.length === 1 && this.lastMessage?.thread) {
            return _t("An error occurred when sending an email on “%(record_name)s”", {
                record_name: this.lastMessage.thread.display_name,
            });
        }
        return _t("An error occurred when sending an email");
    }

    get datetime() {
        return this.lastMessage?.datetime;
    }
}

Failure.register();
