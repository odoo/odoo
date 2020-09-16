odoo.define('website_livechat/static/tests/helpers/mock_models.js', function (require) {
'use strict';

const MockModels = require('mail/static/tests/helpers/mock_models.js');

MockModels.patch('website_livechat/static/tests/helpers/mock_models.js', T =>
    class extends T {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static generateData() {
            const data = super.generateData(...arguments);
            Object.assign(data, {
                'website.visitor': {
                    fields: {
                        country_id: { string: "Country", type: 'many2one', relation: 'res.country' },
                        display_name: { string: "Display name", type: 'string' },
                        // Represent the browsing history of the visitor as a string.
                        // To ease testing this allows tests to set it directly instead
                        // of implementing the computation made on server.
                        // This should normally not be a field.
                        history: { string: "History", type: 'string'},
                        is_connected: { string: "Is connected", type: 'boolean' },
                        lang: { string: "Language", type: 'string'},
                        partner_id: {string: "partner", type: "many2one", relation: 'res.partner'},
                        website: { string: "Website", type: 'string' },
                    },
                    records: [],
                },
            });
            Object.assign(data['mail.channel'].fields, {
                livechat_visitor_id: { string: "Visitor", type: 'many2one', relation: 'website.visitor' },
            });
            return data;
        }

    }
);

});
