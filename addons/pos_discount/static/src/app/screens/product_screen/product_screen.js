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
    async addProductToOrder(product) {
        await super.addProductToOrder(product);
        const discountLine = this.currentOrder.getDiscountLine();
        if (discountLine) {
            const percentage = discountLine.extra_tax_data?.discount_percentage;
            if (percentage) {
                const selectLine = this.currentOrder?.getSelectedOrderline();
                await this.pos.applyDiscount(percentage, this.currentOrder);
                this.pos.selectOrderLine(this.currentOrder, selectLine);
            } else {
                discountLine.delete();
            }
        }
    },
});
