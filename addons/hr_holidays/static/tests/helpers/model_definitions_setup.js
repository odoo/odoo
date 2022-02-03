/** @odoo-module **/

import { insertModelFields } from '@mail/../tests/helpers/model_definitions_helpers';

insertModelFields('res.partner', {
    out_of_office_date_end: { type: 'date' },
});
