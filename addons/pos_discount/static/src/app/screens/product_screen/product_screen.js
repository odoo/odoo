import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons();
        if (!this.currentOrder?.getSelectedOrderline()?.isDiscountLine) {
            return buttons;
        }
        const toDisable = new Set(["quantity", "discount"]);
        return buttons.map((button) => {
            if (toDisable.has(button.value)) {
                return { ...button, disabled: true };
            }
            return button;
        });
    },
});
