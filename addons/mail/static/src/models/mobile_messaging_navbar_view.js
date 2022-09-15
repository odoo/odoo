/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MobileMessagingNavbarView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @param {string} tabId
         */
        onClick(tabId) {
            if (this.discuss) {
                if (this.discuss.activeMobileNavbarTabId === tabId) {
                    return;
                }
                this.discuss.update({ activeMobileNavbarTabId: tabId });
                if (
                    this.discuss.activeMobileNavbarTabId === 'mailbox' &&
                    (!this.discuss.activeThread || !this.discuss.activeThread.mailbox)
                ) {
                    this.discuss.update({ thread: this.messaging.inbox.thread });
                }
                if (this.discuss.activeMobileNavbarTabId !== 'mailbox') {
                    this.discuss.update({ thread: clear() });
                }
                if (this.discuss.activeMobileNavbarTabId !== 'chat') {
                    this.discuss.discussView.update({ isAddingChat: false });
                }
                if (this.discuss.activeMobileNavbarTabId !== 'channel') {
                    this.discuss.discussView.update({ isAddingChannel: false });
                }
            }
            if (this.messagingMenu) {
                this.messagingMenu.update({ activeTabId: tabId });
            }
        },
    },
    fields: {
        /**
         * Tab selected in this navbar.
         * Either 'all', 'mailbox', 'chat' or 'channel'.
         */
        activeTabId: attr({
            compute() {
                if (this.discuss) {
                    return this.discuss.activeMobileNavbarTabId;
                }
                if (this.messagingMenu) {
                    return this.messagingMenu.activeTabId;
                }
                return clear();
            },
        }),
        discuss: one('Discuss', {
            identifying: true,
            inverse: 'mobileMessagingNavbarView',
        }),
        messagingMenu: one('MessagingMenu', {
            identifying: true,
            inverse: 'mobileMessagingNavbarView',
        }),
        /**
         * Ordered list of tabs that this navbar has.
         * Format of tab:
         * {
         *   icon: <the classname for this tab>
         *   id: <the id for this tab>
         *   label: <the label/name of this tab>
         * }
         */
        tabs: attr({
            compute() {
                if (this.discuss) {
                    return [{
                        icon: 'fa fa-inbox',
                        id: 'mailbox',
                        label: this.env._t("Mailboxes"),
                    }, {
                        icon: 'fa fa-user',
                        id: 'chat',
                        label: this.env._t("Chat"),
                    }, {
                        icon: 'fa fa-users',
                        id: 'channel',
                        label: this.env._t("Channel"),
                    }];
                }
                if (this.messagingMenu) {
                    return [{
                        icon: 'fa fa-envelope',
                        id: 'all',
                        label: this.env._t("All"),
                    }, {
                        icon: 'fa fa-user',
                        id: 'chat',
                        label: this.env._t("Chat"),
                    }, {
                        icon: 'fa fa-users',
                        id: 'channel',
                        label: this.env._t("Channel"),
                    }];
                }
                return [];
            },
        }),
    },
});
