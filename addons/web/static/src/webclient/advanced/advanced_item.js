/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class TechnicalItem extends Component {
    static template = "web.DebugMenu.TechnicalItem";
    static props = {};
    setup() {
        this.advanced = useState(useService("advanced"));
    }
    toggleMode() {
        this.advanced.active = !this.advanced.active;
    }
}
