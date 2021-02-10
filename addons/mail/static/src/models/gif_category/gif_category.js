/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { many2one } from '../../model/model_field';

function factory(dependencies) {

    class GifCategory extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        openCategory() {
            this.gifManager.search(this.searchTerm);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------
        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.title}`;
        }
    }

    GifCategory.fields = {
        gifManager: many2one('mail.gif_manager', {
            inverse: 'categories',
        }),
        title: attr({
            required: true,
        }),
        url: attr(),
        image: attr(),
        type: attr(),
        searchTerm: attr(),
    };

    GifCategory.modelName = 'mail.gif_category';

    return GifCategory;
}

registerNewModel('mail.gif_category', factory);
