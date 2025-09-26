import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { getSuggestToggleState, editSuggestContext, toggleFilters } from "./utils";
import { useBus } from "@web/core/utils/hooks";

/* Controller reacts to most UI events on product catalog view (eg. next page, filters, suggestion changes),
 * pass suggestion inputs to backend through context, and reorders kanban records based on backend computations.
 * Eg. Toggle suggest OFF -> loose suggest ctx -> product.suggested_qty set to 0 -> re-render normal catalog
 * Context passed to product.product AND purchase.order (see ./kaban_model.js) because record card is based on
 * both product.product (eg. monthly demand, forecast) and purchase.order (card highlighted, Add button) */
export class PurchaseSuggestCatalogKanbanController extends ProductCatalogKanbanController {
    setup() {
        super.setup();
        this.state = useState({
            numberOfDays: this.props.context.vendor_suggest_days,
            basedOn: this.props.context.vendor_suggest_based_on,
            percentFactor: this.props.context.vendor_suggest_percent,
            totalEstimatedPrice: 0.0,
            currencyId: this.props.context.product_catalog_currency_id,
            digits: this.props.context.product_catalog_digits,
            poState: this.props.context.po_state,
            recomputeTotalPriceFlag: true,
            vendorName: this.props.context.vendor_name,
            warehouse_id: this.props.context.warehouse_id,
            suggestToggle: getSuggestToggleState(this.props.context.po_state),
        });

        onWillStart(async () => {
            this._baseContext = { ...this.model.config.context }; // For resetting when suggest is off
            this._kanbanReload(); // Double rpc on first visit to give context to search model
        });

        // Recompute Kanban on filter changes (incl. sidebar category filters)
        useBus(this.env.searchModel, "update", () => {
            if (this.state.suggestToggle.isOn && this.state.recomputeTotalPriceFlag) {
                this._computeTotalEstimatedPrice(); // To do only recompute if necessary
            }
            this.state.recomputeTotalPriceFlag = true;
        });

        // Recompute Kanban on filter changes (incl. sidebar category filters)
        useBus(this.env.searchModel, "update", () => {
            this.env.searchModel.globalContext = this._editSuggestContext(); // Check with slow internet before removing
            this._kanbanReload();
        });

        useSubEnv({
            suggest: this.state,
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
        if (this.state.suggestToggle.isOn) {
            this._computeTotalEstimatedPrice();
            this.state.recomputeTotalPriceFlag = false;
        }
        this.env.searchModel.globalContext = this._editSuggestContext(this._baseContext);
        this.env.searchModel.searchPanelInfo.shouldReload = true; // Changing suggestion might change categories available
        this.env.searchModel._notify(); // Reload through searchModel with ctx (without double reload)
        this.env.searchModel.searchPanelInfo.shouldReload = false;
    }

    /** Method to add all suggestions to purchase order */
    async onAddAll() {
        const sm = this.env.searchModel;
        await this.model.orm.call(
            "purchase.order",
            "action_purchase_order_suggest",
            [this._baseContext["order_id"], sm.domain],
            { context: this._editSuggestContext() }
        );
        this._toggleSuggestFilters(true);
    }

    toggleSuggest() {
        this.state.suggestToggle.isOn = !this.state.suggestToggle.isOn;
        localStorage.setItem(
            "purchase_stock.suggest_toggle_state",
            JSON.stringify({ isOn: this.state.suggestToggle.isOn })
        );
        this._kanbanReload();
    }

    /** Calculate estimated price (might differ from actual PO price on purpose)
     *  if all suggestions where added to PO (ie. not only the ones displayed) */
    async _computeTotalEstimatedPrice() {
        const product_prices = await this.orm.searchRead(
            "product.product",
            this.env.searchModel.domain,
            ["suggest_estimated_price"],
            { context: this._editSuggestContext() }
        );
        this.state.totalEstimatedPrice = product_prices.reduce(
            (sum, p) => sum + Number(p.suggest_estimated_price || 0),
            0
        );
    }

    /**
     * Helper to toggle filters on Suggestion feature activation / deactivation
     * @param {boolean} toggleOn true to activate filters, false to deactivate
     * @return {none} Triggers a reload if filters didn't change
     */
    _toggleSuggestFilters(toggleOn) {
        const sm = this.env.searchModel;
        toggleFilters(sm, ["suggested", "products_in_purchase_order"], toggleOn);
        this._kanbanReload();
    }

    /**
     * Adds the suggest parameters to context if suggest feature is activated
     * @returns {Object} base context if suggest is OFF or base + suggest context
     */
    _editSuggestContext() {
        const suggestCtx = {
            suggest_domain: this.env.searchModel.domain,
            suggest_based_on: this.state.basedOn,
            suggest_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
            warehouse_id: this.state.warehouse_id,
        };
        return editSuggestContext(this._baseContext, this.state.suggestToggle.isOn, suggestCtx);
    }
}
