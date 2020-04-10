odoo.define('mail.messaging.entity.DialogManager', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function DialogManagerFactory({ Entity }) {

    class DialogManager extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @returns {mail.messaging.entity.Dialog}
         */
        get allOrdered() {
            return this._ordered.map(_dialog => this.env.entities.Dialog.get(_dialog));
        }

        /**
         * @param {string} entityName
         * @param {Object} [entityData]
         */
        open(entityName, entityData) {
            const dialog = this.env.entities.Dialog.create({
                entityName,
                entityData,
                manager: this,
            });
            return dialog;
        }

        /**
         * @param {mail.messaging.entity.Dialog} dialog
         */
        register(dialog) {
            if (this.allOrdered.includes(dialog)) {
                return;
            }
            this.update({
                _ordered: this._ordered.concat([dialog.localId]),
            });
        }

        /**
         * @param {mail.messaging.entity.Dialog} dialog
         */
        unregister(dialog) {
            if (!this.allOrdered.includes(dialog)) {
                return;
            }
            this.update({
                _ordered: this._ordered.filter(
                    _dialog => _dialog === dialog.localId
                ),
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _update(data) {
            const {
                /**
                 * List of ordered dialogs (list of local ids)
                 */
                _ordered = this._ordered || [],
            } = data;

            Object.assign(this, { _ordered });
        }

    }

    Object.assign(DialogManager, {
        relations: Object.assign({}, Entity.relations, {
            dialogs: {
                inverse: 'manager',
                isCausal: true,
                to: 'Dialog',
                type: 'one2many',
            },
            messaging: {
                inverse: 'dialogManager',
                to: 'Messaging',
                type: 'one2one',
            },
        }),
    });

    return DialogManager;
}

registerNewEntity('DialogManager', DialogManagerFactory);

});
