import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    getTaxedlstUnitPrice() {
        const company = this.company;
        const product = this.getProduct();
        const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            this,
            this.prepareBaseLineForTaxesComputationExtraValues({
                price_unit: this.product_id.getPrice(
                    this.config.pricelist_id,
                    1,
                    this.price_extra,
                    false,
                    this.product_id
                ),
                quantity: 1,
                tax_ids: product.taxes_id,
            })
        );
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, company);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], company);
        const taxDetails = baseLine.tax_details;

        if (this.config.iface_tax_included === "total") {
            return taxDetails.total_included_currency;
        } else {
            return taxDetails.total_excluded_currency;
        }
    },
});
