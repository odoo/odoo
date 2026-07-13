/** @odoo-module **/

import {
    addModelNamesToFetch,
    insertModelFields,
} from "@bus/../tests/helpers/model_definitions_helpers";

addModelNamesToFetch([
    "mail.test.track.all",
    "mail.test.activity",
    "mail.test.multi.company",
    "mail.test.multi.company.read",
    "mail.test.properties",
    "mail.test.simple.main.attachment",
    "res.currency",
]);

insertModelFields("mail.test.track.all", {
    float_field_with_digits: { digits: [10, 8] },
});

