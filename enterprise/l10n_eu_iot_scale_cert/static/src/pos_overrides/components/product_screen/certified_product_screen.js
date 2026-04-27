import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    onNumpadClick(buttonValue) {
        // Fordbid manual quantity changes for products that need to be weighed
        // Still allow to delete the line altogether
        if (
            this.pos.isScaleIconVisible &&
            this.pos.selectedOrder.get_selected_orderline().product_id.to_weight &&
            this.pos.numpadMode === "quantity" &&
            !["quantity", "discount", "price", "Backspace", "0"].includes(buttonValue)
        ) {
            this.numberBuffer.reset();
            this.numpadMode = "";
            return this.dialog.add(
                AlertDialog,
                {
                    title: _t("Certified Scale error"),
                    body: _t("You cannot change quantity of a product which needs to be weighed"),
                },
                { onClose: this.props.close }
            );
        }
        super.onNumpadClick(buttonValue);
    },
});
