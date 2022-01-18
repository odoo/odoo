/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'Dialog',
    identifyingFields: [[
        'attachmentCardOwnerAsAttachmentDeleteConfirm',
        'attachmentCardOwnerAsAttachmentView',
        'attachmentImageOwnerAsAttachmentDeleteConfirm',
        'attachmentImageOwnerAsAttachmentView',
        'followerOwnerAsSubtypeList',
        'messageActionListOwnerAsDeleteConfirm',
    ]],
    recordMethods: {
        /**
         * @param {Element} element
         * @returns {boolean}
         */
        hasElementInContent(element) {
            return Boolean(this.record && this.record.containsElement(element));
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachmentDeleteConfirmView() {
            if (this.attachmentCardOwnerAsAttachmentDeleteConfirm) {
                return insertAndReplace();
            }
            if (this.attachmentImageOwnerAsAttachmentDeleteConfirm) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachmentViewer() {
            if (this.attachmentCardOwnerAsAttachmentView) {
                return insertAndReplace();
            }
            if (this.attachmentImageOwnerAsAttachmentView) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeComponentName() {
            if (this.attachmentViewer) {
                return 'AttachmentViewer';
            }
            if (this.attachmentDeleteConfirmView) {
                return 'AttachmentDeleteConfirm';
            }
            if (this.deleteMessageConfirmView) {
                return 'DeleteMessageConfirm';
            }
            if (this.followerSubtypeList) {
                return 'FollowerSubtypeList';
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeDeleteMessageConfirmView() {
            if (this.messageActionListOwnerAsDeleteConfirm) {
                return insertAndReplace();
            }
            clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFollowerSubtypeList() {
            if (this.followerOwnerAsSubtypeList) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCloseable() {
            if (this.attachmentViewer) {
                /**
                 * Prevent closing the dialog when clicking on the mask when the user is
                 * currently dragging the image.
                 */
                return !this.attachmentViewer.isDragging;
            }
            return true;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeManager() {
            if (this.messaging.dialogManager) {
                return replace(this.messaging.dialogManager);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeRecord() {
            if (this.attachmentViewer) {
                return replace(this.attachmentViewer);
            }
            if (this.attachmentDeleteConfirmView) {
                return replace(this.attachmentDeleteConfirmView);
            }
            if (this.deleteMessageConfirmView) {
                return replace(this.deleteMessageConfirmView);
            }
            if (this.followerSubtypeList) {
                return replace(this.followerSubtypeList);
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSize() {
            return 'medium';
        },
    },
    fields: {
        attachmentCardOwnerAsAttachmentDeleteConfirm: one('AttachmentCard', {
            readonly: true,
            inverse: 'attachmentDeleteConfirmDialog',
        }),
        attachmentCardOwnerAsAttachmentView: one('AttachmentCard', {
            readonly: true,
            inverse: 'attachmentViewDialog',
        }),
        attachmentDeleteConfirmView: one('AttachmentDeleteConfirmView', {
            compute: '_computeAttachmentDeleteConfirmView',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        attachmentImageOwnerAsAttachmentDeleteConfirm: one('AttachmentImage', {
            readonly: true,
            inverse: 'attachmentDeleteConfirmDialog',
        }),
        attachmentImageOwnerAsAttachmentView: one('AttachmentImage', {
            readonly: true,
            inverse: 'attachmentViewDialog',
        }),
        attachmentViewer: one('AttachmentViewer', {
            compute: '_computeAttachmentViewer',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        componentName: attr({
            compute: '_computeComponentName',
            required: true,
        }),
        deleteMessageConfirmView: one('DeleteMessageConfirmView', {
            compute: '_computeDeleteMessageConfirmView',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        followerOwnerAsSubtypeList: one('Follower', {
            readonly: true,
            inverse: 'followerSubtypeListDialog',
        }),
        followerSubtypeList: one('FollowerSubtypeList', {
            compute: '_computeFollowerSubtypeList',
            inverse: 'dialogOwner',
            isCausal: true,
        }),
        isCloseable: attr({
            compute: '_computeIsCloseable',
            default: true,
        }),
        manager: one('DialogManager', {
            compute: '_computeManager',
            inverse: 'dialogs',
            readonly: true,
        }),
        messageActionListOwnerAsDeleteConfirm: one('MessageActionList', {
            readonly: true,
            inverse: 'deleteConfirmDialog',
        }),
        /**
         * Content of dialog that is directly linked to a record that models
         * a UI component, such as AttachmentViewer. These records must be
         * created from @see `DialogManager:open()`.
         */
        record: one('Model', {
            compute: '_computeRecord',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        size: attr({
            compute: '_computeSize',
            default: 'medium',
        }),
    },
});
