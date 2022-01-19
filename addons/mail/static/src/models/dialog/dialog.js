/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'Dialog',
    identifyingFields: ['manager', ['attachmentViewer', 'followerSubtypeList']],
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
        _computeRecord() {
            if (this.attachmentViewer) {
                return replace(this.attachmentViewer);
            }
            if (this.followerSubtypeList) {
                return replace(this.followerSubtypeList);
            }
        },
        _computeComponentName() {
            if (this.attachmentViewer) {
                return 'AttachmentViewer';
            }
            if (this.followerSubtypeList) {
                return 'FollowerSubtypeList';
            }
            return clear();
        },
    },
    fields: {
        attachmentViewer: one('AttachmentViewer', {
            isCausal: true,
            inverse: 'dialog',
            readonly: true,
        }),
        componentName: attr({
            compute: '_computeComponentName',
            required: true,
        }),
        followerSubtypeList: one('FollowerSubtypeList', {
            isCausal: true,
            inverse: 'dialog',
            readonly: true,
        }),
        isCloseable: attr({
            compute: '_computeIsCloseable',
            default: true,
        }),
        manager: one('DialogManager', {
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
