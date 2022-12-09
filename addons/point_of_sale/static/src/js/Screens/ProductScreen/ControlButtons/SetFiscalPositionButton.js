/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";
import Registries from "@point_of_sale/js/Registries";

class SetFiscalPositionButton extends PosComponent {
    setup() {
        super.setup();
        useListener("click", this.onClick);
    }
    get currentOrder() {
        return this.env.pos.get_order();
    }
    get currentFiscalPositionName() {
        return this.currentOrder && this.currentOrder.fiscal_position
            ? this.currentOrder.fiscal_position.display_name
            : this.env._t("Tax");
    }
    async onClick() {
        const currentFiscalPosition = this.currentOrder.fiscal_position;
        const fiscalPosList = [
            {
                id: -1,
                label: this.env._t("None"),
                isSelected: !currentFiscalPosition,
            },
        ];
        for (const fiscalPos of this.env.pos.fiscal_positions) {
            fiscalPosList.push({
                id: fiscalPos.id,
                label: fiscalPos.name,
                isSelected: currentFiscalPosition
                    ? fiscalPos.id === currentFiscalPosition.id
                    : false,
                item: fiscalPos,
            });
        }
        const { confirmed, payload: selectedFiscalPosition } = await this.showPopup(
            "SelectionPopup",
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
SetFiscalPositionButton.template = "SetFiscalPositionButton";

ProductScreen.addControlButton({
    component: SetFiscalPositionButton,
    condition: function () {
        return this.env.pos.fiscal_positions.length > 0;
    },
    position: ["before", "SetPricelistButton"],
});

Registries.Component.add(SetFiscalPositionButton);

export default SetFiscalPositionButton;
