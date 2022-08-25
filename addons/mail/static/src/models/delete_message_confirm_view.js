/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'DeleteMessageConfirmView',
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
            return this.dialogOwner.messageActionViewOwnerAsDeleteConfirm.messageAction.messageActionListOwner.message;
        },
        /**
         * @private
         * @returns {MessageView}
         */
        _computeMessageView() {
            return this.message ? { message: this.message } : clear();
        },
    },
    fields: {
        component: attr(),
        dialogOwner: one('Dialog', {
            identifying: true,
            inverse: 'deleteMessageConfirmView',
        }),
        message: one('Message', {
            compute: '_computeMessage',
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
            required: true,
        }),
    },
});
