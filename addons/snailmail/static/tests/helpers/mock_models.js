odoo.define('snailmail/static/tests/helpers/mock_models.js', function (require) {
'use strict';

const MockModels = require('mail/static/tests/helpers/mock_models.js');

MockModels.patch('snailmail/static/tests/helpers/mock_models.js', T =>
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
                'snailmail.letter': {
                    fields: {
                        message_id: { string: 'Snailmail Status Message', type: 'many2one', relation: 'mail.message' },
                    },
                    records: [],
                },
            });
            return data;
        }

    }
);

});
