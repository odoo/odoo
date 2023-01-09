/** @odoo-module */

import { startWebClient } from "@web/start";

import { Chrome } from "@point_of_sale/js/Chrome";
import Registries from "@point_of_sale/js/Registries";

function startPosApp() {
    Registries.Component.freeze();
    Registries.Model.freeze();
    // For consistency's sake, we should trigger"WEB_CLIENT_READY" on the bus when PosApp is mounted
    // But we can't since mail and some other poll react on that cue, and we don't want those services started
    startWebClient(Registries.Component.get(Chrome));
}

startPosApp();
