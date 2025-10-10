import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { useSubEnv, useEnv } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";

export class PurchaseStockProductCatalogKanbanController extends ProductCatalogKanbanController {
    setup() {
        super.setup();
        this.suggestState = useEnv().suggestState;
        this.computeTotalEstimatedPrice = useEnv().computeTotalEstimatedPrice;
        this.suggestParams = {
            currencyId: this.props.context.product_catalog_currency_id,
            digits: this.props.context.product_catalog_digits,
            poState: this.props.context.product_catalog_order_state,
            vendorName: this.props.context.vendor_name,
            warehouse_id: this.props.context.warehouse_id,
        };

        // Reload using a 300ms delay to avoid rendering entire kanban on each digit change
        const debouncedKanbanRecompute = useDebounced(async () => {
            this._kanbanReload(); // Reload the Kanban with ctx
        }, 300); // Enough to type eg. 110 in percent input without rendering 3 times

        /** Reloads catalog with suggestion using searchModel (SM) */
        this._kanbanReload = async () => {
            this.env.searchModel.searchPanelInfo.shouldReload = true; // Changing suggestion might change categories available
            this.env.searchModel._notify(); // Reload through searchModel with ctx (without double reload)
            this.computeTotalEstimatedPrice();
        };

        /** Method to add all suggestions to purchase order */
        const onAddAll = async () => {
            const sm = this.env.searchModel;
            const section_id = sm.selectedSection.sectionId;
            const lineCountChange = await this.model.orm.call(
                "purchase.order",
                "action_purchase_order_suggest",
                [this.props.context.order_id, sm.domain, section_id],
                { context: sm.globalContext }
            );
            sm.toggleFilters(["suggested", "products_in_purchase_order"], true);
            sm.trigger("section-line-count-change", {
                sectionId: section_id,
                lineCountChange: lineCountChange,
            });
        };

        const toggleSuggest = () => {
            this.suggestState.suggestToggle.isOn = !this.suggestState.suggestToggle.isOn;
            localStorage.setItem(
                "purchase_stock.suggest_toggle_state",
                JSON.stringify({ isOn: this.suggestState.suggestToggle.isOn })
            );
            this.env.searchModel.toggleFilters(
                ["suggested", "products_in_purchase_order"],
                this.suggestState.suggestToggle.isOn
            );
        };

        useSubEnv({
            suggestParams: this.suggestParams,
            addAllProducts: onAddAll,
            toggleSuggest: toggleSuggest,
            reloadKanban: debouncedKanbanRecompute,
        });
    }
}
