/** @odoo-module */

import { startWebClient } from "@web/start";
import { Chrome } from "@point_of_sale/js/Chrome";

// FIXME POSREF no we shouldn't but if we did nothing should react, if it does it shouldn't be loaded
// For consistency's sake, we should trigger"WEB_CLIENT_READY" on the bus when PosApp is mounted
// But we can't since mail and some other poll react on that cue, and we don't want those services started
// FIXME POSREF stop using startWebclient: this is not a web client.
startWebClient(Chrome);
