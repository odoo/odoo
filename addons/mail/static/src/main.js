/** @odoo-module **/

import { ChatWindowService } from '@mail/services/chat_window_service/chat_window_service';
import { DialogService } from '@mail/services/dialog_service/dialog_service';
import { MessagingService } from '@mail/services/messaging/messaging';
import { DiscussWidget } from '@mail/widgets/discuss/discuss';
import { MessagingMenuWidget } from '@mail/widgets/messaging_menu/messaging_menu';

import { action_registry } from 'web.core';
import { serviceRegistry } from 'web.core';
import SystrayMenu from 'web.SystrayMenu';

serviceRegistry.add('chat_window', ChatWindowService);
serviceRegistry.add('dialog', DialogService);
serviceRegistry.add('messaging', MessagingService);

action_registry.add('mail.widgets.discuss', DiscussWidget);

// Systray menu items display order matches order in the list
// lower index comes first, and display is from right to left.
// For messagin menu, it should come before activity menu, if any
// otherwise, it is the next systray item.
const activityMenuIndex = SystrayMenu.Items.findIndex(SystrayMenuItem =>
    SystrayMenuItem.prototype.name === 'activity_menu');
if (activityMenuIndex > 0) {
    SystrayMenu.Items.splice(activityMenuIndex, 0, MessagingMenuWidget);
} else {
    SystrayMenu.Items.push(MessagingMenuWidget);
}
