/** @odoo-module **/
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { patch } from "@web/core/utils/patch";

patch(ProductProduct.prototype, {
    setup(product, showPriceTaxIncluded) {
        super.setup(...arguments);
        this.checkEtimsFields = this.checkProductFields;
    },
    checkProductFields() {
        return (
            this.l10n_ke_packaging_unit_id &&
            this.l10n_ke_packaging_quantity &&
            this.l10n_ke_origin_country_id &&
            this.l10n_ke_product_type_code &&
            this.unspsc_code_id &&
            this.taxes_id.length > 0 &&
            this.standard_price > 0
        );
    },
});
