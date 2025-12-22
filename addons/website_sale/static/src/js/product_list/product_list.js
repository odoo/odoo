/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { _t } from "@web/core/l10n/translation";
import { ProductList } from '@sale/js/product_list/product_list';

patch(ProductList.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.env.isFrontend) {
            this.optionalProductsTitle = _t("Available options");
        }
    },

    get totalMessage() {
        if (this.env.isFrontend) {
            return _t("Total: %s", this.getFormattedTotal());
        }
        return super.totalMessage(...arguments);
    },
});
