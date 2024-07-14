/* @odoo-module */

import {
    addModelNamesToFetch,
    insertModelFields,
    insertRecords,
} from "@bus/../tests/helpers/model_definitions_helpers";

addModelNamesToFetch(["ir.config_parameter", "voip.call"]);
insertModelFields("voip.call", {
    direction: { default: "outgoing" },
    state: { default: "calling" },
});
insertRecords("ir.config_parameter", [
    { key: "voip.mode", value: "demo" },
    { key: "voip.pbx_ip", value: "pbx.example.com" },
    { key: "voip.wsServer", value: "wss://example.com" },
]);
