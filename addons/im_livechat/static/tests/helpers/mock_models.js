/** @odoo-module **/

import { MockModels } from '@mail/../tests/helpers/mock_models';
import { patch } from 'web.utils';

patch(MockModels, 'im_livechat/static/tests/helpers/mock_models.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    generateData() {
        const data = this._super(...arguments);
        Object.assign(data, {
            'im_livechat.channel': {
                fields: {
                    user_ids: { string: "Operators", type: 'many2many', relation: 'res.users' }
                },
                records: [],
            }
        });
        Object.assign(data['mail.channel'].fields, {
            anonymous_name: { string: "Anonymous Name", type: 'char' },
            country_id: { string: "Country", type: 'many2one', relation: 'res.country' },
            livechat_active: { string: "Is livechat ongoing?", type: 'boolean', default: false },
            livechat_channel_id: { string: "Channel", type: 'many2one', relation: 'im_livechat.channel' },
            livechat_operator_id: { string: "Operator", type: 'many2one', relation: 'res.partner' },
        });
        Object.assign(data['res.users.settings'].fields, {
            is_discuss_sidebar_category_livechat_open: { string: "Is Discuss Sidebar Category Livechat Open?", type: 'boolean', default: true },
        });
        Object.assign(data['res.users'].fields, {
            livechat_username: { string: 'Livechat Username', type: 'string' },
        });
        return data;
    },

});
