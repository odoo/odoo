odoo.define('hr_holidays/static/tests/helpers/mock_models.js', function (require) {
'use strict';

const MockModels = require('mail/static/tests/helpers/mock_models.js');

MockModels.patch('hr_holidays/static/tests/helpers/mock_models.js', T =>
    class extends T {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static generateData() {
            const data = super.generateData(...arguments);
            Object.assign(data['res.partner'].fields, {
                // Not a real field but ease the testing
                out_of_office_date_end: { type: 'datetime' },
            });
            return data;
        }

    }
);

});
