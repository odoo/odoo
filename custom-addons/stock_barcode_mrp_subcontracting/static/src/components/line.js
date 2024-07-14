/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(LineComponent.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
    },

    async showSubcontractingDetails() {
        const action = await this.env.model._getActionSubcontractingDetails(this.line);
        await this.action.doAction(action);
    },
});
