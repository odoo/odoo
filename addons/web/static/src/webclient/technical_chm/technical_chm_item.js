/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class TechnicalItem extends Component {
    static template = "web.DebugMenu.TechnicalItem";
    static props = {};
    setup() {
        this.technical_chm = useState(useService("technical-chm"));
    }
    toggleMode() {
        this.technical_chm.active = !this.technical_chm.active;
    }
}
