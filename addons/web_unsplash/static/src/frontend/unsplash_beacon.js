/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.UnsplashBeacon = publicWidget.Widget.extend({
    // /!\ To adapt the day the beacon makes sense for backend customizations
    selector: '#wrapwrap',

});
