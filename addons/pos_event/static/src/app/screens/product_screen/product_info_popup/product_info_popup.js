/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";
import { formatDate,deserializeDateTime } from "@web/core/l10n/dates";

patch(ProductInfoPopup.prototype, {
    setup() {
        super.setup();
        if(this.props.product.event_id) {
            this.props.product["display_name"]=this.props.product.event_id[1];
        }
    },
    formatDate(date) {
        return formatDate(deserializeDateTime(date));
    },
    formatAddress(address) {
        return address.replaceAll(',', ' \n')
    },
});
