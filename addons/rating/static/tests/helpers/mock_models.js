/** @odoo-module **/

import MockModels from '@mail/../tests/helpers/mock_models';
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
        // Object.assign(data['mail.message'].fields, {
        //     rating_ids: { string: "Related ratings", type: 'one2many', relation:'rating.rating' },
        // });
        Object.assign(data, {
            'rating.rating': {
                fields: {
                    create_date: { string: "Submitted on", type: 'datetime' },
                    //res_model_id: { string: "Related Document Model", type: 'many2one', relation: 'ir.model' },
                    res_id: { string: "Document", type: 'integer' },
                    //parent_res_model_id: { string: "Parent Related Document Model", type: 'many2one', relation: 'ir.model' },
                    parent_res_id: { string: "Parent Document", type: 'integer' },
                    rated_partner_id: { string: "Rated Operator", type: 'many2one', relation: 'res.partner' },
                    partner_id: { string: "Customer", type: 'many2one', relation: 'res.partner' },
                    rating: { string: "Rating Value", type: 'float' },
                    feedback: { string: "Comment", type: 'char' },
                    message_id: { string: "Message", type: 'many2one', relation: 'mail.message' },
                    //access_token: { string: "Security Token", default() { return uuid.uuid4().hex } },
                    consumed: { string:"Filled Rating", type: 'boolean' },
                },
                records: [],
            }
        });
        return data;
    },

});
