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
                    fields: {},
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
