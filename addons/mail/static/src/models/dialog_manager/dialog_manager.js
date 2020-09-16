odoo.define('mail/static/src/models/dialog_manager/dialog_manager.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { one2many } = require('mail/static/src/model/model_field_utils.js');

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
                __mfield_manager: [['link', this]],
                __mfield_record: [['link', record]],
            });
            return dialog;
        }

    }

    DialogManager.fields = {
        // FIXME: dependent on implementation that uses insert order in relations!!
        __mfield_dialogs: one2many('mail.dialog', {
            inverse: '__mfield_manager',
            isCausal: true,
        }),
    };

    DialogManager.modelName = 'mail.dialog_manager';

    return DialogManager;
}

registerNewModel('mail.dialog_manager', factory);

});
