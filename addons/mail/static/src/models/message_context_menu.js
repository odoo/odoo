/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one, many, attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageContextMenu',
    recordMethods: {

        
        /**
         * Returns whether the given html element is inside this message context menu.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.firstChild.contains(element));
        },
    },
    fields: {
        messageContextMenuDialog: one('Dialog', {
            identifying: true,
            inverse: 'messageContextMenu',
        }),
        messageViewOwner: one('MessageView', {
            related: 'messageContextMenuDialog.messageViewOwnerAsContextMenu'
        }),
        messageContextReactionItems: many('MessageReactionGroupItem', {
            compute() {
                if (this.messageViewOwner.message.messageReactionGroups.length === 0) {
                    return clear();
                }
                return this.messageViewOwner.message.messageReactionGroups.map(messageReactionGroup => {
                     return { messageReactionGroup: messageReactionGroup };
                });
            },
            inverse: 'messageContextViewOwner',
        }),
        messageContextReactionPartners: many('MessageReactionGroupPartner',{
            compute() {
                if (this.messageViewOwner.message.messageReactionGroups.length === 0) {
                    return clear();
                }
                return this.messageViewOwner.message.messageReactionGroups.map(messageReactionGroup => {
                     return { messageReactionGroup: messageReactionGroup };
                });
            },
            inverse: 'messageContextViewOwner',
        }),
        defaultReactionGroup: one('MessageReactionGroup', {
            compute() {
                if (this.messageViewOwner.message.messageReactionGroups) {
                    return this.messageViewOwner.message.messageReactionGroups[0];
                }
                return clear();
            },
        }),
        messageContextState: one('MessageReactionGroup', {
            compute() {
                return this.defaultReactionGroup;
            },
        }),
        component: attr(),
    }
});

