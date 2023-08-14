odoo.define('mail/static/src/models/dialog/dialog.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { many2one, one2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class Dialog extends dependencies['mail.model'] {}

    Dialog.fields = {
        manager: many2one('mail.dialog_manager', {
            inverse: 'dialogs',
        }),
        /**
         * Content of dialog that is directly linked to a record that models
         * a UI component, such as AttachmentViewer. These records must be
         * created from @see `mail.dialog_manager:open()`.
         */
        record: one2one('mail.model', {
            isCausal: true,
        }),
    };

    Dialog.modelName = 'mail.dialog';

    return Dialog;
}

registerNewModel('mail.dialog', factory);

});
