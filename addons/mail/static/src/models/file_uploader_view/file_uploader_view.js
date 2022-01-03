/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'FileUploaderView',
    identifyingFields: [['activityView', 'attachmentBoxView', 'composerView']],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            if (this.activityView) {
                return replace(this.activityView.activity.thread);
            }
            if (this.attachmentBoxView) {
                return replace(this.attachmentBoxView.chatter.thread);
            }
            if (this.composerView) {
                return replace(this.composerView.composer.activeThread);
            }
            return clear();
        },
    },
    fields: {
        activityView: one2one('ActivityView', {
            inverse: 'fileUploaderView',
            isCausal: true,
            readonly: true,
        }),
        attachmentBoxView: one2one('AttachmentBoxView', {
            inverse: 'fileUploaderView',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the OWL component of this file uploader view.
         */
        component: attr(),
        composerView: one2one('ComposerView', {
            inverse: 'fileUploaderView',
            isCausal: true,
            readonly: true,
        }),
        thread: many2one('Thread', {
            compute: '_computeThread',
            readonly: true,
            required: true,
        })
    },
});
