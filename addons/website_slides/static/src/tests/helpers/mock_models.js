/** @odoo-module **/

import { MockModels } from '@mail/../tests/helpers/mock_models';
import { patch } from 'web.utils';

patch(MockModels, 'website_slides/static/tests/helpers/mock_models.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    generateData() {
        const data = this._super(...arguments);
        Object.assign(data, {
            'slide.channel': {
                fields: {
                    activity_ids: { string: "Activities", type: 'one2many', relation: 'mail.activity' },
                },
                records: [],
            },
        });
        return data;
    },

});
