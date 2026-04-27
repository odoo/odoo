import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Domain } from "@web/core/domain";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    // @override
    loadProductFromDBDomain(searchProductWord) {
        const res = super.loadProductFromDBDomain(searchProductWord);
        if (this.pos.config.l10n_br_is_nfce) {
            // The same domain override as in _get_available_product_domain() in pos_config.py
            return Domain.and([
                res,
                [
                    [
                        "taxes_id",
                        "not any",
                        [
                            ["company_id", "in", [false, this.pos.company.id]],
                            ["price_include", "=", false],
                        ],
                    ],
                ],
            ]).toList();
        }
        return res;
    },
});
