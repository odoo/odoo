/** @odoo-module **/

import { ModelsInitializer } from '@mail/../tests/helpers/models_initializer';
import { patch } from 'web.utils';

patch(ModelsInitializer, 'snailmail/static/tests/helpers/models_initializer.js', {
    /**
     * @override
     */
    getRequiredModels() {
        const models = this._super(...arguments);
        models['snailmail.letter'] = ['message_id'];
        return models;
    },
});
