/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class FileUploaderView extends dependencies['mail.model'] {

        _created() {
            this.onChangeAttachment = this.onChangeAttachment.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Called when there are changes in the file input.
         *
         * @param {Event} ev
         * @param {EventTarget} ev.target
         * @param {FileList|Array} ev.target.files
         */
        async onChangeAttachment(ev) {
            await this.fileUploader.performUpload(ev.target.files);
            this.fileUploaderRef.el.value = '';
            this.component.trigger('o-attachment-created');
        }

    }

    FileUploaderView.fields = {
        fileUploader: one2one('mail.file_uploader', {
            inverse: 'fileUploaderView',
            required: true,
            readonly: true,
        }),
        component: attr(),
        fileUploaderRef: attr(),
    };
    FileUploaderView.identifyingFields = ['fileUploader'];
    FileUploaderView.modelName = 'mail.file_uploader_view';

    return FileUploaderView;
}

registerNewModel('mail.file_uploader_view', factory);
