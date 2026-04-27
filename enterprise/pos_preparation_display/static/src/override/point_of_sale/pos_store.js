import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this["pos_preparation_display.display"] = [];
    },

    // @override - add preparation display categories to global order preparation categories
    get orderPreparationCategories() {
        let categoryIds = super.orderPreparationCategories;
        if (this.preparationDisplayCategoryIds.size > 0) {
            categoryIds = new Set([...categoryIds, ...this.preparationDisplayCategoryIds]);
        } else if (this.data.models["pos_preparation_display.display"].length > 0) {
            categoryIds = new Set([
                ...categoryIds,
                ...this.data.models["pos.category"].map((cat) => cat.id),
            ]);
        }
        return categoryIds;
    },

    get preparationDisplayCategoryIds() {
        return new Set(
            this.models["pos_preparation_display.display"].flatMap((preparationDisplay) =>
                preparationDisplay.category_ids.length > 0
                    ? preparationDisplay.category_ids.flatMap((cat) => cat.id)
                    : this.models["pos.category"].flatMap((cat) => cat.id)
            )
        );
    },
    async sendOrderInPreparation(o, cancelled = false) {
        const result = await super.sendOrderInPreparation(o, cancelled);
        if (this.models["pos_preparation_display.display"].length > 0) {
            for (const note of Object.values(o.uiState.noteHistory)) {
                for (const n of note) {
                    const line = o.get_orderline(n.lineId);
                    n.qty = line?.get_quantity();
                }
            }

            try {
                if (cancelled) {
                    await this.data.call("pos_preparation_display.order", "process_order", [
                        o.id,
                        cancelled,
                        o.general_note || "",
                        o.uiState.noteHistory,
                    ]);
                } else {
                    await this.syncAllOrders({
                        orders: [o],
                        context: {
                            preparation: {
                                process_order: [
                                    cancelled,
                                    o.general_note || "",
                                    o.uiState.noteHistory,
                                ],
                            },
                        },
                    });
                    o.updateSavedQuantity();
                }
            } catch (error) {
                console.warn(error);

                // Show error popup only if warningTriggered is false
                if (!this.data.network.warningTriggered) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Send failed"),
                        body: _t("Failed in sending the changes to preparation display"),
                    });
                }
            }

            o.uiState.noteHistory = {};
        }

        return result;
    },
});
