/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'Dialog',
    identifyingFields: [[
        'attachmentListOwnerAsAttachmentView',
        'followerOwnerAsSubtypeList',
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
        _computeAttachmentViewer() {
            if (this.attachmentListOwnerAsAttachmentView) {
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
            if (this.followerSubtypeList) {
                return 'FollowerSubtypeList';
            }
            return clear();
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
            if (this.followerSubtypeList) {
                return replace(this.followerSubtypeList);
            }
        },
    },
    fields: {
        attachmentListOwnerAsAttachmentView: one('AttachmentList', {
            inverse: 'attachmentListViewDialog',
            readonly: true,
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
        followerOwnerAsSubtypeList: one('Follower', {
            inverse: 'followerSubtypeListDialog',
            readonly: true,
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
    },
});
