odoo.define('mail/static/src/models/dialog_manager/dialog_manager.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class DialogManager extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {mail.dialog} dialog
         */
        close(dialog) {
            this.unregister(dialog);
            dialog.delete();
        }

        /**
         * @param {string} modelName
         * @param {Object} [recordData]
         */
        open(modelName, recordData) {
            const dialog = this.env.models['mail.dialog'].create({
                manager: [['link', this]],
            });
            if (!modelName) {
                throw new Error("Dialog should have a link to a model");
            }
            const Model = this.env.models[modelName];
            if (!Model) {
                throw new Error(`No model exists with name ${modelName}`);
            }
            const record = Model.create(recordData);
            dialog.update({ record: [['link', record]] });
            this.update({ _ordered: this._ordered.concat([dialog.localId]) });
            return dialog;
        }

        /**
         * @param {mail.dialog} dialog
         */
        unregister(dialog) {
            if (!this.allOrdered.includes(dialog)) {
                return;
            }
            this.update({
                _ordered: this._ordered.filter(
                    dialogLocalId => dialogLocalId !== dialog.localId
                ),
                dialogs: [['unlink', dialog]],
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * FIXME: dependent on implementation that uses arbitrary order in relations!!
         *
         * @private
         * @returns {mail.dialog}
         */
        _computeAllOrdered() {
            return [['replace', this._ordered.map(dialogLocalId =>
                this.env.models['mail.dialog'].get(dialogLocalId)
            )]];
        }
    }

    DialogManager.fields = {
        _ordered: attr({ default: [] }),
        // FIXME: dependent on implementation that uses arbitrary order in relations!!
        allOrdered: one2many('mail.dialog', {
            compute: '_computeAllOrdered',
            dependencies: [
                '_ordered',
                'dialogs',
            ],
        }),
        dialogs: one2many('mail.dialog', {
            inverse: 'manager',
            isCausal: true,
        }),
    };

    DialogManager.modelName = 'mail.dialog_manager';

    return DialogManager;
}

registerNewModel('mail.dialog_manager', factory);

});
