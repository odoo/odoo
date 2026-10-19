// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    canBeMergedWith(orderline) {
        return (
            this.event_ticket_id?.id === orderline.event_ticket_id?.id &&
            super.canBeMergedWith(...arguments)
        );
    },
    setQuantity(quantity, keep_price) {
        if (this.event_ticket_id && quantity !== "") {
            return {
                title: _t("Ticket error"),
                body: _t("You cannot change quantity for a line linked with an event registration"),
            };
        } else if (this.event_ticket_id) {
            for (const registration of this.event_registration_ids) {
                registration.delete({ silent: true });
            }
        }

        return super.setQuantity(quantity, keep_price);
    },
});
