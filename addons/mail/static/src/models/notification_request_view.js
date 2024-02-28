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
                if (!this.messaging.partnerRoot) {
                    return clear();
                }
                return sprintf(
                    this.env._t("%(odoobotName)s has a request"),
                    { odoobotName: this.messaging.partnerRoot.nameOrDisplayName },
                );
            },
        }),
        notificationListViewOwner: one('NotificationListView', {
            identifying: true,
            inverse: 'notificationRequestView',
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute() {
                return this.messaging.partnerRoot && this.messaging.partnerRoot.isImStatusSet ? {} : clear();
            },
            inverse: 'notificationRequestViewOwner',
        }),
    },
});
