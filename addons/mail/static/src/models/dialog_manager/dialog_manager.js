/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { one2many } from '@mail/model/model_field';

function factory(dependencies) {

    class DialogManager extends dependencies['mail.model'] {
    }

    DialogManager.fields = {
        // FIXME: dependent on implementation that uses insert order in relations!!
        dialogs: one2many('mail.dialog', {
            inverse: 'manager',
            isCausal: true,
        }),
    };
    DialogManager.identifyingFields = ['messaging'];
    DialogManager.modelName = 'mail.dialog_manager';

    return DialogManager;
}

registerNewModel('mail.dialog_manager', factory);
