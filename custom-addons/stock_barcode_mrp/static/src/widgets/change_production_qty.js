/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class ChangeProductionQty extends Component {
    setup() {
        this.actionService = useService("action");
        const user = useService('user');

        onWillStart(async () => {
            this.displayUOM = await user.hasGroup('uom.group_uom');
        });

    }

    get uom() {
        const [id, name] = this.props.record.data.product_uom_id || [];
        return { id, name };
    }

    openChangeQtyWizard() {
        this.actionService.doAction('mrp.action_change_production_qty', {
            additionalContext: {
                default_product_qty: this.props.value,
                default_mo_id: this.props.record.resId,
            },
            onClose: async () => await this.env.model.load(),
        });
    }
}

ChangeProductionQty.template = 'stock_barcode_mrp.ChangeProductionQty';
export const ChangeProductionQtyButton = {
    component: ChangeProductionQty,
};
registry.category('fields').add('change_production_qty', ChangeProductionQtyButton);
