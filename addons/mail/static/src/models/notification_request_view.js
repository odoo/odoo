/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'NotificationRequestView',
    fields: {
        headerText: attr({
            compute() {
                if (!this.global.Messaging.partnerRoot) {
                    return clear();
                }
                return sprintf(
                    this.env._t("%(odoobotName)s has a request"),
                    { odoobotName: this.global.Messaging.partnerRoot.nameOrDisplayName },
                );
            },
        }),
        notificationListViewOwner: one('NotificationListView', {
            identifying: true,
            inverse: 'notificationRequestView',
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute() {
                return this.global.Messaging.partnerRoot && this.global.Messaging.partnerRoot.isImStatusSet ? {} : clear();
            },
            inverse: 'notificationRequestViewOwner',
        }),
    },
});
