/** @odoo-module **/

import { ActivityMenuContainer } from '@mail/components/activity_menu_container/activity_menu_container';
import { CallSystrayMenuContainer } from '@mail/components/call_systray_menu_container/call_systray_menu_container';
import { ChatWindowManagerContainer } from '@mail/components/chat_window_manager_container/chat_window_manager_container';
import { DialogManagerContainer } from '@mail/components/dialog_manager_container/dialog_manager_container';
import { DiscussContainer } from '@mail/components/discuss_container/discuss_container';
import { MessagingMenuContainer } from '@mail/components/messaging_menu_container/messaging_menu_container';
import { PopoverManagerContainer } from '@mail/components/popover_manager_container/popover_manager_container';
import { setupCoreMessaging } from '@mail/setup/core/setup_core_helpers';

import { registry } from '@web/core/registry';

export function setupBackendMessaging(messagingValues) {
    setupCoreMessaging(messagingValues);
    registry.category('systray')
        .add('mail.ActivityMenu', { Component: ActivityMenuContainer }, { sequence: 20 })
        .add('mail.MessagingMenuContainer', { Component: MessagingMenuContainer }, { sequence: 25 })
        .add('mail.CallSystrayMenuContainer', { Component: CallSystrayMenuContainer }, { sequence: 100 });
    registry.category('actions')
        .add('mail.action_discuss', DiscussContainer);
    registry.category('main_components')
        .add('DialogManagerContainer', { Component: DialogManagerContainer })
        .add('ChatWindowManagerContainer', { Component: ChatWindowManagerContainer })
        .add('PopoverManagerContainer', { Component: PopoverManagerContainer });
}
