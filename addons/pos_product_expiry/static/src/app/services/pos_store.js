import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

const { DateTime } = luxon;

patch(PosStore.prototype, {
    showNotificationIfLotExpired(lotName, lotExpDate = null) {
        if (!lotExpDate) {
            return;
        }
        const lotExpDateTime = deserializeDateTime(lotExpDate);
        if (lotExpDateTime?.isValid && lotExpDateTime.ts <= DateTime.now().ts) {
            this.notification.add(_t("Lot/Serial %s is expired", lotName));
        }
    },

    async editLots(product, packLotLinesToEdit) {
        const result = await super.editLots(product, packLotLinesToEdit);
        if (!result) {
            return result;
        }

        if (result?.newPackLotLines && result.newPackLotLines[0]?.lot) {
            const existingLot = result.newPackLotLines[0].lot;
            this.showNotificationIfLotExpired(existingLot.name, existingLot?.expiration_date);
        } else if (result?.modifiedPackLotLines && result?.newPackLotLines && result?.payload) {
            for (const item of result.payload) {
                if (!item.item.expiration_date) {
                    continue;
                }
                this.showNotificationIfLotExpired(item.text, item.item.expiration_date);
            }
        }

        return result;
    },
});
