/** @odoo-module **/

import { ActivityMenuContainer } from '@mail/components/activity_menu_container/activity_menu_container';
import { MessagingMenuContainer } from '@mail/components/messaging_menu_container/messaging_menu_container';
import { CallSystrayMenuContainer } from '@mail/components/call_systray_menu_container/call_systray_menu_container';

import { registry } from '@web/core/registry';

const systrayRegistry = registry.category('systray');

export const systrayService = {
    dependencies: ['messaging'],
    start() {
        systrayRegistry.add('mail.ActivityMenu', { Component: ActivityMenuContainer }, { sequence: 20 });
        systrayRegistry.add('mail.MessagingMenuContainer', { Component: MessagingMenuContainer }, { sequence: 25 });
        systrayRegistry.add('mail.CallSystrayMenuContainer', { Component: CallSystrayMenuContainer }, { sequence: 100 });
    },
};
