/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'mail.dialog',
    identifyingFields: ['manager', ['attachmentViewer', 'followerSubtypeList']],
    recordMethods: {
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
        attachmentViewer: one2one('mail.attachment_viewer', {
            isCausal: true,
            inverse: 'dialog',
            readonly: true,
        }),
        componentName: attr({
            compute: '_computeComponentName',
            required: true,
        }),
        followerSubtypeList: one2one('mail.follower_subtype_list', {
            isCausal: true,
            inverse: 'dialog',
            readonly: true,
        }),
        manager: many2one('mail.dialog_manager', {
            inverse: 'dialogs',
            readonly: true,
        }),
        /**
         * Content of dialog that is directly linked to a record that models
         * a UI component, such as AttachmentViewer. These records must be
         * created from @see `mail.dialog_manager:open()`.
         */
        record: one2one('mail.model', {
            compute: '_computeRecord',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
