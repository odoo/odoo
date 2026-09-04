import { fields, Record } from "@mail/model/export";

import { computed, markRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

export class Failure extends Record {
    static nextId = markRaw({ value: 1 });

    /** @type {number} */
    id;
    setup() {
        super.setup();
        const hasNotifications = computed(() => this.notifications.length > 0);
        this.onChange(
            () => [hasNotifications()],
            function onChangeNotifications(hasNotifications) {
                if (hasNotifications) {
                    this.store.failures.add(this);
                } else {
                    this.delete();
                }
            },
            { immediate: true, initialRun: false }
        );
    }
    notifications = fields.Many("mail.notification");
    get modelName() {
        return this.notifications?.[0]?.mail_message_id?.thread?.modelName;
    }
    get resModel() {
        return this.notifications?.[0]?.mail_message_id?.thread?.model;
    }
    resIds = this.computed(
        () =>
            new Set([
                ...this.notifications
                    .map((notif) => notif.mail_message_id?.thread?.id)
                    .filter((id) => !!id),
            ])
    );
    lastMessage = this.computed(() => {
        let lastMsg = this.notifications[0]?.mail_message_id;
        for (const notification of this.notifications) {
            if (lastMsg?.id < notification.mail_message_id?.id) {
                lastMsg = notification.mail_message_id;
            }
        }
        return lastMsg;
    });
    /** @type {'sms' | 'email'} */
    get type() {
        return this.notifications?.[0]?.notification_type;
    }
    get status() {
        return this.notifications?.[0]?.notification_status;
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
