/** @odoo-module **/

import { ActivityMenuViewContainer } from '@mail/components/activity_menu_view_container/activity_menu_view_container';
import { MessagingMenuContainer } from '@mail/components/messaging_menu_container/messaging_menu_container';
import { CallSystrayMenuViewContainer } from '@mail/components/call_systray_menu_view_container/call_systray_menu_view_container';

import { registry } from '@web/core/registry';

const systrayRegistry = registry.category('systray');

export const systrayService = {
    dependencies: ['messaging'],
    start() {
        systrayRegistry.add('mail.ActivityMenu', { Component: ActivityMenuViewContainer }, { sequence: 20 });
        systrayRegistry.add('mail.MessagingMenuContainer', { Component: MessagingMenuContainer }, { sequence: 25 });
        systrayRegistry.add('mail.CallSystrayMenuViewContainer', { Component: CallSystrayMenuViewContainer }, { sequence: 100 });
    },
};
