/** @odoo-module **/
/* Copyright 2023 Onestein - Anjeel Haria
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {ChatterTopbar} from "@mail/components/chatter_topbar/chatter_topbar";
import {deviceContext} from "@web_responsive/components/ui_context.esm";
import {patch} from "web.utils";

// Patch chatter topbar to add ui device context
patch(ChatterTopbar.prototype, "web_responsive.ChatterTopbar", {
    setup() {
        this._super();
        this.ui = deviceContext;
    },
});
