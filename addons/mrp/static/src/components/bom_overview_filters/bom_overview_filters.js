/** @odoo-module native */
import { AccountReportFilters } from "@report_formula/components/account_report/filters/filters";
import { patch } from "@web/core/utils/patch";

patch(AccountReportFilters.prototype, {
    get bomOverviewVariants() {
        return this.controller.cachedFilterOptions.bom_overview_variants || [];
    },

    get bomOverviewWarehouses() {
        return this.controller.cachedFilterOptions.bom_overview_warehouses || [];
    },

    bomOverviewVariantName(variantId) {
        const variant = this.bomOverviewVariants.find(
            (candidate) => candidate.id === variantId,
        );
        return variant ? variant.name : "";
    },

    bomOverviewWarehouseName(warehouseId) {
        const warehouse = this.bomOverviewWarehouses.find(
            (candidate) => candidate.id === warehouseId,
        );
        return warehouse ? warehouse.name : "";
    },

    async setBomOverviewQuantity(ev) {
        const quantity = Number.parseFloat(ev.target.value);
        await this.controller.updateOption(
            "bom_overview_quantity",
            Number.isNaN(quantity) || quantity <= 0 ? 1 : quantity,
            true,
        );
    },

    async setBomOverviewVariant(variantId) {
        await this.controller.updateOption("bom_overview_variant_id", variantId, true);
    },

    async setBomOverviewWarehouse(warehouseId) {
        await this.controller.updateOption(
            "bom_overview_warehouse_id",
            warehouseId,
            true,
        );
    },
});
