/** @odoo-module **/

import { MockModels } from '@mail/../tests/helpers/mock_models';
import { patch } from 'web.utils';

patch(MockModels, 'test_mail/static/tests/helpers/mock_models.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    generateData() {
        const data = this._super(...arguments);
        Object.assign(data, {
            'mail.test.tracking.value': {
                fields: {
                    boolean_field: { string: 'Boolean', tracking: true, type: 'boolean' },
                    char_field: { string: 'Char', tracking: true, type: 'char' },
                    date_field: { string: 'Date', tracking: true, type: 'date' },
                    datetime_field: { string: 'Datetime', tracking: true, type: 'datetime' },
                    float_field: { string: 'Float', tracking: true, type: 'float' },
                    integer_field: { string: 'Integer', tracking: true, type: 'integer' },
                    monetary_field: { string: 'Monetary', tracking: true, type: 'monetary' },
                    partner_id: { relation: 'res.partner', string: 'Partner', tracking: true, type: 'many2one' },
                    selection_field: { string: 'Selection', tracking: true, type: 'selection', selection: [['first', 'FIRST']] },
                    text_field: { string: 'Text', tracking: true, type: 'text' },
                    message_ids: { string: 'Messages', type: 'one2many', relation: 'mail.message' },
                },
                records: [],
            },
        });
        return data;
    },

});
