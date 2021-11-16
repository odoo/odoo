/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class FileUploaderView extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

    }

    FileUploaderView.fields = {
        thread: one2one('mail.thread', {
            inverse: 'fileUploaderView',
            required: true,
            readonly: true,
        }),
        component: attr(),
        fileUploaderRef: attr(),
    };
    FileUploaderView.identifyingFields = ['thread'];
    FileUploaderView.modelName = 'mail.file_uploader_view';

    return FileUploaderView;
}

registerNewModel('mail.file_uploader_view', factory);
