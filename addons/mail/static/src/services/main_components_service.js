/** @odoo-module **/

import { ChatWindowManagerContainer } from '@mail/components/chat_window_manager_container/chat_window_manager_container';
import { DialogManagerContainer } from '@mail/components/dialog_manager_container/dialog_manager_container';
import { PopoverManagerContainer } from '@mail/components/popover_manager_container/popover_manager_container';

import { registry } from '@web/core/registry';

const mainComponentsRegistry = registry.category('main_components');

export const mainComponentsService = {
    dependencies: ['messaging'],
    start() {
        mainComponentsRegistry.add('DialogManagerContainer', { Component: DialogManagerContainer });
        mainComponentsRegistry.add('ChatWindowManagerContainer', { Component: ChatWindowManagerContainer });
        mainComponentsRegistry.add('PopoverManagerContainer', { Component: PopoverManagerContainer });
    },
};
