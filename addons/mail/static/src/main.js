/** @odoo-module **/

import { ChatWindowManagerContainer } from '@mail/components/chat_window_manager_container/chat_window_manager_container';
import { DialogManagerContainer } from '@mail/components/dialog_manager_container/dialog_manager_container';
import { MessagingService } from '@mail/services/messaging/messaging';
import { SystrayService } from '@mail/services/systray_service/systray_service';
import { DiscussWidget } from '@mail/widgets/discuss/discuss';

import { serviceRegistry, action_registry } from 'web.core';
import { registry } from '@web/core/registry';

serviceRegistry.add('messaging', MessagingService);
serviceRegistry.add('systray_service', SystrayService);

action_registry.add('mail.widgets.discuss', DiscussWidget);

registry.category('main_components').add('DialogManagerContainer', { Component: DialogManagerContainer });
registry.category('main_components').add('ChatWindowManagerContainer', { Component: ChatWindowManagerContainer });
