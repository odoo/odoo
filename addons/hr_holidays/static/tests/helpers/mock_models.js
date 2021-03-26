odoo.define('hr_holidays/static/tests/helpers/mock_models.js', function (require) {
'use strict';

const MockModels = require('@mail/../tests/helpers/mock_models')[Symbol.for("default")];
const { patch } = require('web.utils');

patch(MockModels, 'hr_holidays/static/tests/helpers/mock_models.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    generateData() {
        const data = this._super(...arguments);
        Object.assign(data['res.partner'].fields, {
            // Not a real field but ease the testing
            out_of_office_date_end: { type: 'datetime' },
        });
        return data;
    },

});

});
