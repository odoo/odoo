/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import { patch } from "@web/core/utils/patch";
import { parseDateTime } from "@web/core/l10n/dates";

patch(LineComponent.prototype, {
    get isUseExpirationDate() {
        return this.line.product_id.use_expiration_date;
    },

    get expirationDate() {
        const dateTimeStrUTC = (this.line.lot_id && this.line.lot_id.expiration_date) || this.line.expiration_date;
        if (!dateTimeStrUTC) {
            return '';
        }
        const dateTimeLocal = parseDateTime(dateTimeStrUTC).toJSDate();
        return dateTimeLocal.toLocaleDateString();
    },
});
