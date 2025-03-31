/** @odoo-module */

import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogKanbanController.prototype, {
    async _defineButtonContent() {
        if (this.orderResModel === "repair.order") {
            this.buttonString = _t("Back to Repair");
        } else {
            super._defineButtonContent();
        }
    },
});
