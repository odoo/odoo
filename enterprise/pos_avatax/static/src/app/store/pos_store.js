import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async getAvataxTaxesRpc() {
        if (!this.config.module_pos_avatax) {
            return;
        }

        try {
            const order = this.get_order();
            if (this.env.services.ui.isBlocked || !order.partner_id) {
                return;
            } else {
                this.env.services.ui.block({ message: _t("Updating Avatax taxes...") });
            }

            const serialized = order.serialize({ orm: true });
            const data = await this.data.call("pos.order", "get_order_tax_details", [[serialized]]);
            const modelToAdd = {};
            for (const [model, records] of Object.entries(data)) {
                const modelKey = this.data.opts.databaseTable[model]?.key;

                if (!modelKey) {
                    modelToAdd[model] = records;
                    continue;
                }
            }

            this.models.loadData(modelToAdd);
        } catch {
            this.dialog.add(AlertDialog, {
                title: _t("Error while loading Avatax taxes"),
                body: _t(
                    "Enable to load Avatax taxes, please verify partner information and Avatax API configuration."
                ),
            });
        } finally {
            this.env.services.ui.unblock();
        }
    },
    async selectPartner() {
        const res = await super.selectPartner(...arguments);
        if (res) {
            await this.getAvataxTaxesRpc();
        }
        return res;
    },
});
