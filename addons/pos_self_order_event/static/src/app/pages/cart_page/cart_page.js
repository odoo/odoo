import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(CartPage.prototype, {
    async setup() {
        super.setup();
        this.notification = useService("notification");
    },
    changeQuantity(line, increase) {
        if (!line.event_ticket_id) {
            return super.changeQuantity(line, increase);
        }
        return this.notification.add(
            _t("You cannot change quantity for a line linked with an event registration"),
            { type: "warning" }
        );
    },
});
