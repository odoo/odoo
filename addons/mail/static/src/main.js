/** @odoo-module **/

import { ChatWindowService } from '@mail/services/chat_window_service/chat_window_service';
import { DialogService } from '@mail/services/dialog_service/dialog_service';
import { MessagingService } from '@mail/services/messaging/messaging';
import { SystrayService } from '@mail/services/systray_service/systray_service';
import { DiscussWidget } from '@mail/widgets/discuss/discuss';

import { action_registry } from 'web.core';
import { serviceRegistry } from 'web.core';

serviceRegistry.add('chat_window', ChatWindowService);
serviceRegistry.add('dialog', DialogService);
serviceRegistry.add('messaging', MessagingService);
serviceRegistry.add('systray_service', SystrayService);

action_registry.add('mail.widgets.discuss', DiscussWidget);
