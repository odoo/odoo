/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.preparationDisplays = [];
    },

    _initializePreparationDisplay() {
        const preparationDisplayCategories = this.preparationDisplays.flatMap(
            (preparationDisplay) => preparationDisplay.pdis_category_ids
        );
        this.preparationDisplayCategoryIds = new Set(preparationDisplayCategories);
    },

    // @override - add preparation display categories to global order preparation categories
    get orderPreparationCategories() {
        let categoryIds = super.orderPreparationCategories;
        if (this.preparationDisplayCategoryIds) {
            categoryIds = new Set([...categoryIds, ...this.preparationDisplayCategoryIds]);
        }
        return categoryIds;
    },

    // @override
    async _processData(loadedData) {
        await super._processData(loadedData);
        this.preparationDisplays = loadedData["pos_preparation_display.display"];
    },

    // @override
    async after_load_server_data() {
        await super.after_load_server_data(...arguments);
        this._initializePreparationDisplay();
    },

    // @override
    async updateModelsData(models_data) {
        await super.updateModelsData(...arguments);
        if ("pos_preparation_display.display" in models_data) {
            this.preparationDisplays = models_data["pos_preparation_display.display"];
            this._initializePreparationDisplay();
        }
    },

    async sendOrderInPreparation(order, cancelled = false) {
        let result = super.sendOrderInPreparation(order, cancelled);
        let sendChangesResult = true;

        if (this.preparationDisplayCategoryIds.size) {
            sendChangesResult = await order.sendChanges(cancelled);
        }

        // We display this error popup only if the PoS is connected,
        // otherwise the user has already received a popup telling him
        // that this functionality will be limited.
        if (!sendChangesResult && this.synch.status === "connected") {
            await this.popup.add(ErrorPopup, {
                title: _t("Send failed"),
                body: _t("Failed in sending the changes to preparation display"),
                sound: false,
            });
        }

        return result;
    },
    // @override
    _getCreateOrderContext(orders, options) {
        const context = super._getCreateOrderContext(...arguments);
        if (options.originalSplittedOrderId) {
            context.is_splited_order = true;
        }
        return context;
    }
});
