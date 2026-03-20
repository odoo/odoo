import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { useSubEnv, useEnv } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";

export class PurchaseSuggestCatalogKanbanController extends ProductCatalogKanbanController {
    setup() {
        super.setup();
        this.suggest = useEnv().suggest;
        this._computeTotalEstimatedPrice = useEnv()._computeTotalEstimatedPrice;
        Object.assign(this.suggest, {
            currencyId: this.props.context.product_catalog_currency_id,
            digits: this.props.context.product_catalog_digits,
            poState: this.props.context.product_catalog_order_state,
            vendorName: this.props.context.vendor_name,
            warehouse_id: this.props.context.warehouse_id,
        });

        useSubEnv({
            addAllProducts: () => this.onAddAll(),
            toggleSuggest: () => this.toggleSuggest(),
            reloadKanban: () => this._kanbanReload(),
            debouncedReloadKanban: useDebounced(async () => {
                this._kanbanReload();
            }, 500), // Enough to type eg. 110 in percent input without rendering 3 times
        });
    }

    // Reloads catalog with suggestions
    async _kanbanReload() {
        this.env.searchModel.searchPanelInfo.shouldReload = true; // Changing suggestion might change categories available
        await this.env.searchModel._notify(); // Reload through searchModel with ctx (without double reload)
        await this._computeTotalEstimatedPrice();
    }

    /** Add all suggested products to the purchase order */
    async onAddAll() {
        const { searchModel } = this.env;
        const { sectionId } = searchModel.selectedSection;
        const lineCountChange = await this.model.orm.call(
            "purchase.order",
            "action_purchase_order_suggest",
            [this.props.context.product_catalog_order_id],
            { context: searchModel.globalContext }
        );
        searchModel.toggleFilters(["suggested", "products_in_purchase_order"], true);
        searchModel.trigger("section-line-count-change", {
            sectionId,
            lineCountChange,
        });
    }

    toggleSuggest() {
        this.suggest.suggestToggle.isOn = !this.suggest.suggestToggle.isOn;
        localStorage.setItem(
            "purchase_stock.suggest_toggle_state",
            JSON.stringify({ isOn: this.suggest.suggestToggle.isOn })
        );
        this.env.searchModel.toggleFilters(
            ["suggested", "products_in_purchase_order"],
            this.suggest.suggestToggle.isOn
        );
    }
}
