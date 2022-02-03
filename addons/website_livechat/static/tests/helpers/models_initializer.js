/** @odoo-module **/

import { ModelsInitializer } from '@mail/../tests/helpers/models_initializer';
import { patch } from 'web.utils';

patch(ModelsInitializer, 'website_livechat/static/tests/helpers/models_initializer.js', {
    /**
     * @override
     */
    getRequiredModels() {
        const models = this._super(...arguments);
        models['website.visitor'] = ['country_id', 'is_connected', 'partner_id'];
        models['mail.channel'].push('livechat_visitor_id');
        return models;
    },
    /**
     * @override
     */
     getCustomFieldsByModel() {
         const customFieldsByModel = this._super(...arguments);
         Object.assign(customFieldsByModel['mail.channel'], {
            // Represent the browsing history of the visitor as a string.
            // To ease testing this allows tests to set it directly instead
            // of implementing the computation made on server.
            // This should normally not be a field.
            history: { string: "History", type: 'string'},
         });
         Object.assign(customFieldsByModel, {
             'website.visitor': {
                history: { string: "History", type: 'string'},
                lang_name: { string: "Language name", type: 'string'},
                website_name: { string: "Website name", type: 'string' },
             },
         });
         return customFieldsByModel;
     },
});
