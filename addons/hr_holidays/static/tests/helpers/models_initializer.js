/** @odoo-module **/

import { ModelsInitializer } from '@mail/../tests/helpers/models_initializer';
import { patch } from 'web.utils';

patch(ModelsInitializer, 'hr_holidays/static/tests/helpers/models_initializer.js', {
    /**
     * @override
     */
    getCustomFieldsByModel() {
        const customFieldsByModel = this._super(...arguments);
        Object.assign(customFieldsByModel['res.partner'], {
            out_of_office_date_end: { type: 'date' },
        });
        return customFieldsByModel;
    },
});
