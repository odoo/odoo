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
            return Boolean(this.component && this.component.root.el && this.component.root.el !== element && this.component.root.el.contains(element));
        },
    },
    fields: {
        component: attr(),
        messageOwner: one('Message', {
            compute() {
                if (this.owner.messageViewOwnerAsContextMenu) {
                    return this.owner.messageViewOwnerAsContextMenu.message;
                }
                return clear();
            },
        }),
        defaultReactionSelection: one('MessageReactionGroup', {
            compute() {
                if (this.messageOwner.messageReactionGroups) {
                    return this.messageOwner.messageReactionGroups[0];
                }
                return clear();
            },
        }),
        items: many('MessageReactionGroupItem', { inverse: 'messageContextViewOwner',
            compute() {
                if (this.messageOwner.messageReactionGroups.length === 0) {
                    return clear();
                }
                return this.messageOwner.messageReactionGroups.map(messageReactionGroup => {
                     return { messageReactionGroup: messageReactionGroup };
                });
            },
        }),
        owner: one('Dialog', {
            identifying: true,
            inverse: 'messageContextMenu',
        }),
        personaListView: one('PersonaListView', { default: {}, inverse: 'messageContextMenuOwner' }),
        reactionSelection: one('MessageReactionGroup', {
            compute() {
                return this.defaultReactionSelection;
            },
        }),
    }
});
