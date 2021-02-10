odoo.define('mail/static/src/models/category/category.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');

function factory(dependencies) {
    class Category extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------
        
        async toggleIsOpen() {
            if(this.isOpen) {
                await this.close();
            } else {
                await this.open();
            }
        }

        async open() {
            this.update({ isPendingOpen: true });
            await this.env.models['mail.category'].performRpcSetCategoryOpenStates({
                categoryId: this.id,
                isOpen: true,
            });
        }

        async close() {
            this.update({ isPendingOpen: false });
            await this.env.models['mail.category'].performRpcSetCategoryOpenStates({
                categoryId: this.id,
                isOpen: false,
            });
        }

        static async performRpcSetCategoryOpenStates({ categoryId, isOpen }) {
            return this.env.services.rpc({
                model: 'res.users',
                method: 'set_category_open_states',
                args: [[this.env.session.uid]],
                kwargs: {
                    'category_id': categoryId,
                    'is_open': isOpen,
                }
            });
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        
        _computeIsOpen() {
            return this.isPendingOpen !== undefined ? this.isPendingOpen : this.isServerOpen;
        }

        _onIsServerOpenChanged() {
            if (this.isServerOpen === this.isPendingOpen) {
                this.update({ isPendingOpen: clear() });
            }
        }

    }

    Category.fields = {
        id: attr(),
        displayName: attr(),
        isOpen: attr({
            compute: '_computeIsOpen',
            dependencies: [
                'isPendingOpen',
                'isServerOpen',
            ]
        }),
        isPendingOpen: attr(),
        isServerOpen: attr(),
        onIsServerOpenChanged: attr({
            compute: '_onIsServerOpenChanged',
            dependencies: ['isServerOpen'],
        }),
    };

    Category.modelName = 'mail.category'

    return Category;
}

registerNewModel('mail.category', factory);

});
