/** @odoo-module **/

import { MockModels } from '@mail/../tests/helpers/mock_models';
import { patch } from 'web.utils';

patch(MockModels, 'rating/static/tests/helpers/mock_models.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    generateData() {
        const data = this._super(...arguments);
        Object.assign(data, {
            'rating.rating': {
                fields: {
                    consumed: { string:"Filled Rating", type: 'boolean' },
                    create_date: { string: "Submitted on", type: 'datetime' },
                    feedback: { string: "Comment", type: 'char' },
                    message_id: { string: "Message", type: 'many2one', relation: 'mail.message' },
                    parent_res_id: { string: "Parent Document", type: 'integer' },
                    partner_id: { string: "Customer", type: 'many2one', relation: 'res.partner' },
                    rated_partner_id: { string: "Rated Operator", type: 'many2one', relation: 'res.partner' },
                    rating: { string: "Rating Value", type: 'float' },
                    res_id: { string: "Document", type: 'integer' },
                },
                records: [],
            }
        });
        return data;
    },

});
