/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

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
            this.message.messageActionList.onClickConfirmDelete();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessage() {
            return replace(this.dialogOwner.messageActionListOwnerAsDeleteConfirm.messageViewForDelete);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageViewForDelete() {
            return replace(this.dialogOwner.messageActionListOwnerAsDeleteConfirm.messageViewForDelete);
        },
        /**
         * @private
         * @returns {string}
         */
        _computeTitle() {
            return this.env._t("Confirmation");
        },
    },
    fields: {
        component: attr(),
        dialogOwner: one('Dialog', {
            readonly: true,
            required: true,
            inverse: 'deleteMessageConfirmView',
        }),
        message: one('Message', {
            compute: '_computeMessage',
        }),
        messageViewForDelete: one('MessageView', {
            compute: '_computeMessageViewForDelete',
        }),
        title: attr({
            compute: '_computeTitle',
        }),
    },
});
