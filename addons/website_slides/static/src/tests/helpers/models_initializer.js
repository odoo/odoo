/** @odoo-module **/

import { ModelsInitializer } from '@mail/../tests/helpers/models_initializer';
import { patch } from 'web.utils';

patch(ModelsInitializer, 'website_slides/static/tests/helpers/models_initializer.js', {
    /**
     * @override
     */
    getRequiredModels() {
        const models = this._super(...arguments);
        models['slide.channel'] = ['activity_ids'];
        models['note.note'] = [];
        return models;
    },
});
