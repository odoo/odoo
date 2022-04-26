/** @odoo-module **/

import { MessagingMenuContainer } from '@mail/components/messaging_menu_container/messaging_menu_container';
import { RtcActivityNoticeContainer } from '@mail/components/rtc_activity_notice_container/rtc_activity_notice_container';

import { registry } from '@web/core/registry';

const systrayRegistry = registry.category('systray');

export const systrayService = {
    dependencies: ['messaging'],
    start() {
        systrayRegistry.add('mail.MessagingMenuContainer', { Component: MessagingMenuContainer });
        systrayRegistry.add('mail.RtcActivityNoticeContainer', { Component: RtcActivityNoticeContainer }, { sequence: 100 });
    },
};
