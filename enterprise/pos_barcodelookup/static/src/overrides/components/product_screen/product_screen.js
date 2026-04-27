import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    async _barcodeProductAction(code) {
        const product = await this._getProductByBarcode(code);

        if (!product && (await this.pos.allowProductCreation())) {
            const response = await this.pos.data.call("product.template", "barcode_lookup", []);
            if (response?.authenticated) {
                this.pos.action.doAction("point_of_sale.product_product_action_add_pos", {
                    additionalContext: {
                        default_barcode: code.code,
                    },
                });
                this.pos.scanning = false;
                return;
            }
        }

        await super._barcodeProductAction(code);
    },
});
