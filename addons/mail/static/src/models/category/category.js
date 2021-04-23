/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

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
            await this.env.models['mail.category'].performRpcSetCategoryStates({
                categoryId: this.id,
                isOpen: true,
            });
        }

        async close() {
            this.update({ isPendingOpen: false });
            await this.env.models['mail.category'].performRpcSetCategoryStates({
                categoryId: this.id,
                isOpen: false,
            });
        }

        static async performRpcSetCategoryStates({ categoryId, isOpen }) {
            return this.env.services.rpc(
                {
                    model: 'mail.category.states',
                    method: 'set_category_states',
                    kwargs: {
                        'category': categoryId,
                        'is_open': isOpen,
                    },
                },
                { shadow: true },
            );
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
