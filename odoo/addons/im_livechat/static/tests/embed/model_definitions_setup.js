/* @odoo-module */

import {
    addModelNamesToFetch,
    insertModelFields,
} from "@bus/../tests/helpers/model_definitions_helpers";

addModelNamesToFetch(["im_livechat.channel"]);
insertModelFields("res.users", { im_status: { default: "online" } });
