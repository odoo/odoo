import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

const { DateTime } = luxon;

export class LoyaltyCard extends Base {
    static pythonModel = "loyalty.card";
    static extraFields = {
        _temp_points: {
            model: "loyalty.card",
            name: "_temp_points",
            type: "float",
            local: true,
        },
        _barcode_base64: {
            model: "loyalty.card",
            name: "_barcode_base64",
            type: "string",
            local: true,
        },
    };
    isExpired() {
        // If no expiration date is set, the card is not expired
        if (!this.expiration_date) {
            return false;
        }

        return DateTime.fromISO(this.expiration_date).toMillis() < DateTime.now().toMillis();
    }
}

registry.category("pos_available_models").add(LoyaltyCard.pythonModel, LoyaltyCard);
