/** @odoo-module **/

import { ModelsInitializer } from '@mail/../tests/helpers/models_initializer';
import { patch } from 'web.utils';

patch(ModelsInitializer, 'hr/static/tests/helpers/models_initializer.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    getRequiredModels() {
        const models = this._super(...arguments);
        models['hr.employee.public'] = ['user_id', 'user_partner_id'];
        return models;
    },

});
