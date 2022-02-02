/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'DeleteMessageConfirmView',
    identifyingFields: ['dialogOwner'],
    recordMethods: {
        /**
         * Returns whether the given html element is inside this delete message confirm view.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        onClickCancel() {
            this.dialogOwner.delete();
        },
        onClickDelete() {
            this.message.updateContent({
                attachment_ids: [],
                body: '',
            });
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessage() {
            return replace(this.dialogOwner.messageActionListOwnerAsDeleteConfirm.message);
        },
        /**
         * @private
         * @returns {MessageView}
         */
        _computeMessageView() {
            return this.message ? insertAndReplace({ message: replace(this.message) }) : clear();
        },
    },
    fields: {
        component: attr(),
        dialogOwner: one('Dialog', {
            inverse: 'deleteMessageConfirmView',
            readonly: true,
            required: true,
        }),
        message: one('Message', {
            compute: '_computeMessage',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the message view that this delete message confirm view
         * will use to display this message.
         */
        messageView: one('MessageView', {
            compute: '_computeMessageView',
            inverse: 'deleteMessageConfirmViewOwner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
