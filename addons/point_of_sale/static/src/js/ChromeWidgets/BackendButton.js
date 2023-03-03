/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class BackendButton extends Component {
    static template = "BackendButton";

    setup() {
        super.setup(...arguments);
        this.pos = useService("pos");
    }

    async onClick() {
        this.pos.closePos();
    }
}
