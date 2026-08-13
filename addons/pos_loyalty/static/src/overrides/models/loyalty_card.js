import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

const { DateTime } = luxon;

export class LoyaltyCard extends Base {
    static pythonModel = "loyalty.card";

    isExpired() {
        // If no expiration date is set, the card is not expired
        if (!this.expiration_date) {
            return false;
        }

        return DateTime.fromISO(this.expiration_date).toMillis() < DateTime.now().toMillis();
    }
}

registry.category("pos_available_models").add(LoyaltyCard.pythonModel, LoyaltyCard);
