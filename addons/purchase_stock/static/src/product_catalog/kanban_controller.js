import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv, onRendered } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { loadSuggestToggleState, editSuggestContext, toggleFilters } from "./utils";
import { useBus } from "@web/core/utils/hooks";

/* Controller reacts to most UI events on product catalog view (eg. next page, filters, suggestion changes),
 * pass suggestion inputs to backend through context, and reorders kanban records based on backend computations.
 * Eg. Toggle suggest OFF -> loose suggest ctx -> product.suggested_qty set to 0 -> re-render normal catalog
 * Context passed to product.product AND purchase.order (see ./kaban_model.js) because record card is based on
 * both product.product (eg. monthly demand, forecast) and purchase.order (card highlighted, Add button) */
export class PurchaseSuggestCatalogKanbanController extends ProductCatalogKanbanController {
    setup() {
        super.setup();
        this.suggestParams = {
            currencyId: this.props.context.product_catalog_currency_id,
            digits: this.props.context.product_catalog_digits,
            poState: this.props.context.po_state,
            vendorName: this.props.context.vendor_name,
            warehouse_id: this.props.context.warehouse_id,
        };
        this.state = useState({
            numberOfDays: this.props.context.vendor_suggest_days,
            basedOn: this.props.context.vendor_suggest_based_on,
            percentFactor: this.props.context.vendor_suggest_percent,
            totalEstimatedPrice: 0.0,
            suggestToggle: loadSuggestToggleState(this.suggestParams.poState),
            recomputeTotalPriceFlag: true,
        });

        onWillStart(async () => {
            this._baseContext = { ...this.model.config.context }; // For resetting when suggest is off
            this._kanbanReload();
        });

        // On every UI change reorder grid if it is not ordered
        onRendered(async () => {
            if (this.state.suggestToggle.isOn) {
                await this._reorderKanbanGrid();
            }
        });

        // Reload using a 300ms delay to avoid rendering entire kanban on each digit change
        const debouncedKanbanRecompute = useDebounced(async () => {
            this._kanbanReload(); // Reload the Kanban with ctx
        }, 300); // Enough to type eg. 110 in percent input without rendering 3 times

        /** Reloads catalog with suggestion using searchModel (SM) reload
         * (to use SM domain, SM logic to compute available categories, prevent double reload ...) */
        this._kanbanReload = async () => {
            if (this.state.suggestToggle.isOn) {
                this._computeTotalEstimatedPrice();
                this.state.recomputeTotalPriceFlag = false;
            }
            this.env.searchModel.globalContext = this._getSuggestContext(this._baseContext);
            this.env.searchModel.searchPanelInfo.shouldReload = true; // Changing suggestion might change categories available
            this.env.searchModel._notify(); // Reload through searchModel with ctx (without double reload)
            this.env.searchModel.searchPanelInfo.shouldReload = false;
        };

        /** Method to add all suggestions to purchase order */
        const onAddAll = async () => {
            const sm = this.env.searchModel;
            await this.model.orm.call(
                "purchase.order",
                "action_purchase_order_suggest",
                [this._baseContext["order_id"], sm.domain],
                { context: this._getSuggestContext() }
            );
            this._toggleSuggestFilters(true);
        };

        /** When user toggles suggestion switch, we reload && toggle filters */
        const toggleSuggest = () => {
            this.state.suggestToggle.isOn = !this.state.suggestToggle.isOn;
            localStorage.setItem(
                "purchase_stock.suggest_toggle_state",
                JSON.stringify({ isOn: this.state.suggestToggle.isOn })
            );
            this._toggleSuggestFilters(this.state.suggestToggle.isOn);
        };

        /* Recompute total price on filter changes (eg. sidebar category filters) */
        useBus(this.env.searchModel, "update", () => {
            if (this.state.suggestToggle.isOn && this.state.recomputeTotalPriceFlag) {
                this._computeTotalEstimatedPrice(); // To do only recompute if necessary
            }
            this.state.recomputeTotalPriceFlag = true;
        });

        useSubEnv({
            suggestState: this.state,
            suggestParams: this.suggestParams,
            addAllProducts: onAddAll,
            toggleSuggest: toggleSuggest,
            reloadKanban: debouncedKanbanRecompute,
        });
    }

    /** Calculate estimated price (might differ from actual PO price on purpose)
     *  if all suggestions where added to PO (ie. not only the ones displayed) */
    async _computeTotalEstimatedPrice() {
        const product_prices = await this.orm.searchRead(
            "product.product",
            this.env.searchModel.domain,
            ["suggest_estimated_price"],
            { context: this._getSuggestContext() }
        );
        this.state.totalEstimatedPrice = product_prices.reduce(
            (sum, p) => sum + Number(p.suggest_estimated_price || 0),
            0
        );
    }

    /**
     * Moves records with suggested_qty > 0 to the front, keeping original order.
     * Works with normal and group filters but not accross pagination (eg if 41st
     * record has suggested qty > 0 it won't show).
     * @returns {null} Forces a refresh (only if changed order) by not sorting in place.
     */
    async _reorderKanbanGrid() {
        const sortBySuggested = (list) => {
            const suggestProducts = list.filter((record) => record.data.suggested_qty > 0);
            const notSuggestedProducts = list.filter((record) => record.data.suggested_qty == 0);
            return [...suggestProducts, ...notSuggestedProducts];
        };

        const isGroupFilterOff = this.model.config.groupBy.length === 0;
        if (isGroupFilterOff) {
            if (!this._isKanbanOrdered(this.model.root.records)) {
                this.model.root.records = sortBySuggested(this.model.root.records);
            }
        } else {
            for (const group of this.model.root.groups || []) {
                if (!this._isKanbanOrdered(group.list.records)) {
                    group.list.records = sortBySuggested(group.list.records);
                }
            }
        }
    }

    /** Returns true if all suggested products are before not suggested */
    _isKanbanOrdered(records) {
        let lastSuggested = false;
        for (const record of records) {
            const isProductSuggested = (record.data.suggested_qty || 0) > 0;
            if (!isProductSuggested) {
                lastSuggested = true;
            } else if (lastSuggested) {
                return false; // If we see again suggested after 1st non suggested
            }
        }
        return true;
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
    _getSuggestContext() {
        const suggestCtx = {
            suggest_domain: this.env.searchModel.domain,
            suggest_based_on: this.state.basedOn,
            suggest_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
            warehouse_id: this.suggestParams.warehouse_id,
        };
        return editSuggestContext(this._baseContext, this.state.suggestToggle.isOn, suggestCtx);
    }
}
