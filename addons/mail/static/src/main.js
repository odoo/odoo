/** @odoo-module **/

import { manageMessages } from "@mail/js/tools/debug_manager";
import { messagingService } from '@mail/services/messaging_service/messaging_service';
import { newMessageService } from "@mail/services/new_message_service/new_message_service";
import { getMessagingComponent } from '@mail/utils/messaging_component';

import { registry } from '@web/core/registry';

registry.category('services').add('messaging', messagingService);
registry.category("services").add("new_message", newMessageService);
registry.category('systray').add('mail.messaging_menu', {
    Component: getMessagingComponent('MessagingMenu'),
    props: {},
}, { sequence: 5 });
registry.category("actions").add("mail.widgets.discuss", getMessagingComponent('Discuss'));
registry.category('main_components').add('mail.chat_window_manager', {
    Component: getMessagingComponent('ChatWindowManager'),
    props: {},
});
registry.category('main_components').add('mail.dialog', {
    Component: getMessagingComponent('DialogManager'),
    props: {},
});
registry.category("debug").category("form").add("mail.manageMessages", manageMessages);
