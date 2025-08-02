/** @odoo-module **/

import { insertModelFields } from "@bus/../tests/helpers/model_definitions_helpers";

insertModelFields("res.partner", {
    out_of_office_date_end: { type: "date", default: () => false },
});
