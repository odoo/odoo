odoo.define('mail.messaging.entity.Dialog', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function DialogFactory({ Entity }) {

    class Dialog extends Entity {

        /**
         * @override
         */
        static create(data) {
            const dialog = super.create(data);
            this.register(dialog);
            return dialog;
        }

        /**
         * @override
         */
        delete() {
            this.constructor.unregister(this);
            super.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @returns {mail.messaging.entity.Dialog}
         */
        static get allOrdered() {
            return this._ordered.map(_dialog => this.get(_dialog));
        }

        /**
         * @static
         * @param {string} entityName
         * @param {Object} [entityData]
         */
        static open(entityName, entityData) {
            const dialog = this.create({ entityName, entityData });
            return dialog;
        }

        /**
         * @param {mail.messaging.entity.Dialog} dialog
         */
        static register(dialog) {
            if (this.allOrdered.includes(dialog)) {
                return;
            }
            this.update({
                _ordered: this._ordered.concat([dialog.localId]),
            });
        }

        /**
         * @static
         * @param {mail.messaging.entity.Dialog} dialog
         */
        static unregister(dialog) {
            if (!this.allOrdered.includes(dialog)) {
                return;
            }
            this.update({
                _ordered: this._ordered.filter(
                    _dialog => _dialog === dialog.localId
                ),
            });
        }

        close() {
            this.delete();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _getListOfClassAttributeNames() {
            return super._getListOfClassAttributeNames().concat([
                '_ordered',
            ]);
        }

        /**
         * @override
         */
        static _update(data) {
            const {
                /**
                 * List of ordered dialogs (list of local ids)
                 */
                _ordered = this._ordered || [],
            } = data;

            this._write({ _ordered });
        }

        /**
         * @override
         */
        _update(data) {
            const {
                entityName,
                entityData,
            } = data;

            if (!this.entity) {
                if (!entityName) {
                    throw new Error("Dialog should have a link to entity");
                }
                const Entity = this.env.entities[entityName];
                if (!Entity) {
                    throw new Error(`No entity exists with name ${entityName}`);
                }
                Entity.create(Object.assign({ dialog: this }, entityData));
            }

            this._write({});
        }

    }

    Object.assign(Dialog, {
        relations: Object.assign({}, Entity.relations, {
            /**
             * Content of dialog that is directly linked to an entity that models
             * a UI component, such as AttachmentViewer. These entities must be
             * created from @see `Dialog.open()`.
             */
            entity: {
                inverse: 'dialog',
                isCausal: true,
                to: 'Entity',
                type: 'one2one',
            },
        }),
    });

    return Dialog;
}

registerNewEntity('Dialog', DialogFactory);

});
