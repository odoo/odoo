/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

import { sprintf } from "@web/core/utils/strings";

Model({
    name: "NotificationRequestView",
    template: "mail.NotificationRequestView",
    recordMethods: {
        onClick() {
            this.messaging.requestNotificationPermission();
            if (!this.messaging.device.isSmall) {
                this.messaging.messagingMenu.close();
            }
        },
    },
    fields: {
        headerText: attr({
            compute() {
                if (!this.messaging.partnerRoot) {
                    return clear();
                }
                return sprintf(this.env._t("%(odoobotName)s has a request"), {
                    odoobotName: this.messaging.partnerRoot.nameOrDisplayName,
                });
            },
        }),
        notificationListViewOwner: one("NotificationListView", {
            identifying: true,
            inverse: "notificationRequestView",
        }),
        personaImStatusIconView: one("PersonaImStatusIconView", {
            inverse: "notificationRequestViewOwner",
            compute() {
                return this.messaging.partnerRoot && this.messaging.partnerRoot.isImStatusSet
                    ? {}
                    : clear();
            },
        }),
    },
});
