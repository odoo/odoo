/** @odoo-module **/

import {
    addModelNamesToFetch,
    addRefsToFetch,
    insertModelFields,
} from '@bus/../tests/helpers/model_definitions_helpers';

//--------------------------------------------------------------------------
// Models
//--------------------------------------------------------------------------

addModelNamesToFetch([
    'ir.attachment', 'ir.model', 'ir.model.fields', 'res.company', 'res.country',
    'res.groups', 'res.partner', 'res.users'
]);

//--------------------------------------------------------------------------
// Insertion of fields
//--------------------------------------------------------------------------

insertModelFields('res.partner', {
    description: { string: 'description', type: 'text' },
});

//--------------------------------------------------------------------------
// Records to fetch
//--------------------------------------------------------------------------

addRefsToFetch([
    'base.group_public', 'base.group_user', 'base.main_company',
    'base.partner_root', 'base.public_partner', 'base.public_user',
]);
