/* @odoo-module */

import {
    addModelNamesToFetch,
    insertModelFields,
} from "@bus/../tests/helpers/model_definitions_helpers";

const { DateTime } = luxon;

addModelNamesToFetch(["whatsapp.composer", "whatsapp.message", "whatsapp.template"]);
insertModelFields("res.users.settings", {
    is_discuss_sidebar_category_whatsapp_open: { default: true },
});
insertModelFields("discuss.channel", {
    whatsapp_channel_valid_until: {
        default: () => DateTime.utc().plus({days: 1}).toSQL(),
    },
});
