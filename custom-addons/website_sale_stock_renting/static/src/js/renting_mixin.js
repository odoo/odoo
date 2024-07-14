/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { RentingMixin } from '@website_sale_renting/js/renting_mixin';

const oldGetInvalidMessage = RentingMixin._getInvalidMessage;
/**
 * Override to take the stock renting availabilities into account.
 *
 * @override
 */
RentingMixin._getInvalidMessage = function (startDate, endDate, productId) {
    let message = oldGetInvalidMessage.apply(this, arguments);
    if (message || !startDate || !endDate || !this.rentingAvailabilities || this.preparationTime === undefined) {
        return message;
    }
    if (startDate < luxon.DateTime.now().plus({hours: this.preparationTime})) {
        return _t("Your rental product cannot be prepared as fast, please rent later.");
    }
    if (!this.rentingAvailabilities[productId]) {
        return message;
    }
    let end = luxon.DateTime.now();
    for (const interval of this.rentingAvailabilities[productId]) {
        if (interval.start < endDate) {
            end = interval.end;
            if (this._isDurationWithHours()) {
                end = end.plus({hours: this.preparationTime});
            }
            if (end > startDate) {
                if (interval.quantity_available <= 0) {
                    if (!message) {
                        message = _t("The product is not available for the following time period(s):\n");
                    }
                    message +=
                        " " +
                        _t(
                            "- From %s to %s.\n",
                            this._isDurationWithHours()
                                ? formatDateTime(interval.start)
                                : formatDate(interval.start),
                            this._isDurationWithHours() ? formatDateTime(end) : formatDate(end)
                        );
                }
            }
            end -= interval.end;
        } else {
            break;
        }
    }
    return message;
};
