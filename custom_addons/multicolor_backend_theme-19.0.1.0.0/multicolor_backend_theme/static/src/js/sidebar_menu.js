/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.sidebarState = useState({
            isOpen: false
        });
    },

    onclickOpenSidebar() {
        this.sidebarState.isOpen = true;
    },

    onclickCloseSidebar() {
        this.sidebarState.isOpen = false;
    },

    get sidebarClasses() {
        return {
            'sidebar-open': this.sidebarState.isOpen
        };
    }
});