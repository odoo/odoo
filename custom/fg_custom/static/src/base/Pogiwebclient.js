/** @odoo-module alias=web.custom.title **/

import { WebClient } from "@web/webclient/webclient";
import {patch} from "@web/core/utils/patch";

patch(WebClient.prototype, "Web Custom Title", {
    setup() {
        this._super();
        this.title.setParts({ zopenerp: 'POGI' });
    }
});