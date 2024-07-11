/** @odoo-module **/

import {
    addModelNamesToFetch,
    insertModelFields,
} from "@bus/../tests/helpers/model_definitions_helpers";

addModelNamesToFetch(["website.visitor"]);
insertModelFields("discuss.channel", {
    history: { string: "History", type: "string" },
});
insertModelFields("website.visitor", {
    history: { string: "History", type: "string" },
    lang_name: { string: "Language name", type: "string" },
    website_name: { string: "Website name", type: "string" },
});
