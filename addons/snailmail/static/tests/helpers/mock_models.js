/** @odoo-module **/

import { MockModels } from '@mail/../tests/helpers/mock_models';
import { patch } from 'web.utils';

patch(MockModels, 'snailmail/static/tests/helpers/mock_models.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    generateData() {
        const data = this._super(...arguments);
        Object.assign(data, {
            'snailmail.letter': {
                fields: {
                    message_id: { string: 'Snailmail Status Message', type: 'many2one', relation: 'mail.message' },
                },
                records: [],
            },
        });
        return data;
    },

});
