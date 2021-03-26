/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { one2many } from '@mail/model/model_field';
import { link } from '@mail/model/model_field_command';

function factory(dependencies) {

    class DialogManager extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {string} modelName
         * @param {Object} [recordData]
         */
        open(modelName, recordData) {
            if (!modelName) {
                throw new Error("Dialog should have a link to a model");
            }
            const Model = this.env.models[modelName];
            if (!Model) {
                throw new Error(`No model exists with name ${modelName}`);
            }
            const record = Model.create(recordData);
            const dialog = this.env.models['mail.dialog'].create({
                manager: link(this),
                record: link(record),
            });
            return dialog;
        }

    }

    DialogManager.fields = {
        // FIXME: dependent on implementation that uses insert order in relations!!
        dialogs: one2many('mail.dialog', {
            inverse: 'manager',
            isCausal: true,
        }),
    };

    DialogManager.modelName = 'mail.dialog_manager';

    return DialogManager;
}

registerNewModel('mail.dialog_manager', factory);
