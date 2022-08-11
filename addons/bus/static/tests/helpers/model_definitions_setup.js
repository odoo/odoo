/** @odoo-module **/

import { TEST_USER_IDS } from '@bus/../tests/helpers/test_constants';
import {
    addModelNamesToFetch,
    insertModelFields,
    insertRecords
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
// Insertion of records
//--------------------------------------------------------------------------

insertRecords('res.company', [{ id: 1 }]);
insertRecords('res.users', [
    { display_name: "Your Company, Mitchell Admin", id: TEST_USER_IDS.currentUserId, name: "Mitchell Admin", partner_id: TEST_USER_IDS.currentPartnerId, },
    { active: false, display_name: "Public user", id: TEST_USER_IDS.publicUserId, name: "Public user", partner_id: TEST_USER_IDS.publicPartnerId, },
]);
insertRecords('res.partner', [
    { active: false, display_name: "Public user", id: TEST_USER_IDS.publicPartnerId, },
    { display_name: "Your Company, Mitchell Admin", id: TEST_USER_IDS.currentPartnerId, name: "Mitchell Admin", },
    { active: false, display_name: "OdooBot", id: TEST_USER_IDS.partnerRootId, },
]);
