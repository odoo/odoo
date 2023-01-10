/** @odoo-module **/

// ensure components are registered beforehand.
import '@mail/components/messaging_menu/messaging_menu';
import '@mail/components/rtc_activity_notice/rtc_activity_notice';
import { getMessagingComponent } from '@mail/utils/messaging_component';

import AbstractService from 'web.AbstractService';
import { registry } from '@web/core/registry';

const systrayRegistry = registry.category('systray');

export const SystrayService = AbstractService.extend({
    dependencies: ['messaging'],
    /**
     * @override {web.AbstractService}
     */
    async start() {
        await owl.Component.env.services.messaging.modelManager.messagingCreatedPromise;
        systrayRegistry.add('mail.MessagingMenu', {
            Component: getMessagingComponent('MessagingMenu'),
        });
        systrayRegistry.add('mail.RtcActivityNotice', {
            Component: getMessagingComponent('RtcActivityNotice'),
        });
    },
});
