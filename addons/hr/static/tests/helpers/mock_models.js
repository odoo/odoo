/** @odoo-module **/

import { MockModels } from '@mail/../tests/helpers/mock_models';
import { patch } from 'web.utils';

patch(MockModels, 'hr/static/tests/helpers/mock_models.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    generateData() {
        const data = this._super(...arguments);
        Object.assign(data, {
            'hr.employee.public': {
                fields: {
                    display_name: { string: "Name", type: "char" },
                    user_id: { string: "User", type: "many2one", relation: 'res.users' },
                    user_partner_id: { string: "Partner", type: "many2one", relation: 'res.partner' },
                },
                records: [],
            },
        });
        return data;
    },

});
