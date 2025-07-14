import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons();
        this.pos.isDiscountLineSelected &&
            buttons.forEach((button) => {
                ["quantity", "discount"].includes(button.value) && (button.disabled = true);
            });
        return buttons;
    },
});
