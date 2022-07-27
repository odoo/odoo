/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { many2one, one2one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Dialog extends dependencies['mail.model'] {

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
        }
    }

    Dialog.fields = {
        attachmentViewer: one2one('mail.attachment_viewer', {
            isCausal: true,
            inverse: 'dialog',
            readonly: true,
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
    };
    Dialog.identifyingFields = ['manager', ['attachmentViewer', 'followerSubtypeList']];
    Dialog.modelName = 'mail.dialog';

    return Dialog;
}

registerNewModel('mail.dialog', factory);
