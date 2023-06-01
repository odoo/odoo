/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useService } from "@web/core/utils/hooks";
import { SelectionPopup } from "@point_of_sale/js/Popups/SelectionPopup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class SetFiscalPositionButton extends Component {
    static template = "SetFiscalPositionButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    get currentOrder() {
        return this.pos.globalState.get_order();
    }
    get currentFiscalPositionName() {
        return this.currentOrder && this.currentOrder.fiscal_position
            ? this.currentOrder.fiscal_position.display_name
            : this.env._t("Tax");
    }
    async click() {
        const currentFiscalPosition = this.currentOrder.fiscal_position;
        const fiscalPosList = [
            {
                id: -1,
                label: this.env._t("None"),
                isSelected: !currentFiscalPosition,
            },
        ];
        for (const fiscalPos of this.pos.globalState.fiscal_positions) {
            fiscalPosList.push({
                id: fiscalPos.id,
                label: fiscalPos.name,
                isSelected: currentFiscalPosition
                    ? fiscalPos.id === currentFiscalPosition.id
                    : false,
                item: fiscalPos,
            });
        }
        const { confirmed, payload: selectedFiscalPosition } = await this.popup.add(
            SelectionPopup,
            {
                title: this.env._t("Select Fiscal Position"),
                list: fiscalPosList,
            }
        );
        if (confirmed) {
            this.currentOrder.set_fiscal_position(selectedFiscalPosition);
            // IMPROVEMENT: The following is the old implementation and I believe
            // there could be a better way of doing it.
            for (const line of this.currentOrder.orderlines) {
                line.set_quantity(line.quantity);
            }
        }
    }
}

ProductScreen.addControlButton({
    component: SetFiscalPositionButton,
    condition: function () {
        return this.pos.globalState.fiscal_positions.length > 0;
    },
    position: ["before", "SetPricelistButton"],
});
