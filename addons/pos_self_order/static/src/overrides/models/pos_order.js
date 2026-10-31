import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    getSelfOrderNotificationMessage() {
        const table = this.self_ordering_table_id;
        if (table?.floor_id) {
            return _t(
                "New order received from %s - Table %s",
                table.floor_id.name,
                table.table_number
            );
        }
        if (this.preset_id?.name) {
            return _t("New %s order received: %s", this.preset_id.name, this.tracking_number);
        }
        return _t("New self order received: %s", this.tracking_number);
    },
});
