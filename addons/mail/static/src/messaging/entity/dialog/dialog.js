odoo.define('mail.messaging.entity.Dialog', function (require) {
'use strict';

const {
    fields: {
        many2one,
        one2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function DialogFactory({ Entity }) {

    class Dialog extends Entity {

        /**
         * @override
         */
        delete() {
            if (this.manager) {
                this.manager.unregister(this);
            }
            super.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        close() {
            this.delete();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _update(data) {
            const {
                entityName,
                entityData,
                manager,
            } = data;

            const prevManager = this.manager;

            // manager
            if (manager && this.manager !== manager) {
                manager.register(this);
                if (prevManager) {
                    prevManager.unregister(this);
                }
            }

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
        }

    }

    Object.assign(Dialog, {
        fields: Object.assign({}, Entity.fields, {
            /**
             * Content of dialog that is directly linked to an entity that models
             * a UI component, such as AttachmentViewer. These entities must be
             * created from @see `mail.messaging.entity.DialogManager.open()`.
             */
            entity: one2one('Entity', {
                inverse: 'dialog',
                isCausal: true,
            }),
            manager: many2one('DialogManager', {
                inverse: 'dialogs',
            }),
        }),
    });

    return Dialog;
}

registerNewEntity('Dialog', DialogFactory);

});
