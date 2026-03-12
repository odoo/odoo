import { CartLine } from "@website_sale/js/cart_lines/cart_line/cart_line";
import { patch } from "@web/core/utils/patch";
import { formatDate } from "@web/core/l10n/dates";

patch(CartLine.prototype, {
    formatDate(date) {
        const formattedDate = luxon.DateTime.fromISO(date);
        return formatDate(formattedDate);
    },
});
