/** @odoo-module **/

import { TEST_GROUP_IDS, TEST_USER_IDS } from "@bus/../tests/helpers/test_constants";
import {
    addModelNamesToFetch,
    insertModelFields,
    insertRecords,
} from "@bus/../tests/helpers/model_definitions_helpers";

//--------------------------------------------------------------------------
// Models
//--------------------------------------------------------------------------

addModelNamesToFetch([
    "ir.attachment",
    "ir.model",
    "ir.model.fields",
    "res.company",
    "res.country",
    "res.groups",
    "res.partner",
    "res.users",
]);

//--------------------------------------------------------------------------
// Insertion of fields
//--------------------------------------------------------------------------

insertModelFields("res.partner", {
    description: { string: "description", type: "text" },
    is_company: { default: () => false },
});

//--------------------------------------------------------------------------
// Insertion of records
//--------------------------------------------------------------------------

insertRecords("res.company", [{ id: 1 }]);
insertRecords("res.groups", [{ id: TEST_GROUP_IDS.groupUserId, name: "Internal User" }]);
insertRecords("res.users", [
    {
        display_name: "Your Company, Mitchell Admin",
        id: TEST_USER_IDS.adminUserId,
        name: "Mitchell Admin",
        login: "admin",
        password: "admin",
        partner_id: TEST_USER_IDS.adminPartnerId,
    },
    {
        active: false,
        display_name: "Public user",
        login: "public",
        password: "public",
        id: TEST_USER_IDS.publicUserId,
        name: "Public user",
        partner_id: TEST_USER_IDS.publicPartnerId,
    },
]);
insertRecords("res.partner", [
    {
        active: false,
        display_name: "Public user",
        name: "Public user",
        id: TEST_USER_IDS.publicPartnerId,
        is_public: true,
    },
    {
        display_name: "Your Company, Mitchell Admin",
        id: TEST_USER_IDS.adminPartnerId,
        name: "Mitchell Admin",
    },
    {
        active: false,
        display_name: "Bot",
        id: TEST_USER_IDS.odoobotId,
        im_status: "bot",
        name: "Bot",
    },
]);
