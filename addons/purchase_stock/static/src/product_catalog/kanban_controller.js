import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { useBus } from "@web/core/utils/hooks";
import { loadSuggestToggleState, editSuggestContext, filterInTheOrder } from "./utils";

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
        });

        onWillStart(async () => {
            this._baseContext = { ...this.model.config.context }; // For resetting when suggest is off
        });

        /* Pass context to backend and reload front-end with computed values
         * using a 300ms delay to avoid rendering entire kanban on each digit change */
        const debouncedKanbanRecompute = useDebounced(async () => {
            this.model.config.context = this._getSuggestContext();
            await this.model.root.load({}); // Reload the Kanban with ctx

            if (this.state.suggestToggle.isOn) {
                this._computeTotalEstimatedPrice();
                await this._reorderKanbanGrid();
            }
        });

        // Recompute Kanban on filter changes (incl. sidebar category filters)
        useBus(this.env.searchModel, "update", () => {
            this.env.searchModel.globalContext = this._getSuggestContext(); // Check with slow internet before removing
            debouncedKanbanRecompute();
        });

        const onAddAll = async () => {
            const ctx = this._filter_add_all_ctx(this._getSuggestContext()); // IMPROVE: Quickfix
            await this.model.orm.call(
                "purchase.order",
                "action_purchase_order_suggest",
                [ctx["order_id"]],
                { context: ctx }
            );
            filterInTheOrder(); // Apply filter to show what was added
        };

        /** When user toggles suggestion switch, we reload && toggle filters */
        const toggleSuggest = () => {
            this.state.suggestToggle.isOn = !this.state.suggestToggle.isOn;
            localStorage.setItem(
                "purchase_stock.suggest_toggle_state",
                JSON.stringify({ isOn: this.state.suggestToggle.isOn })
            );
            debouncedKanbanRecompute();
        };

        useSubEnv({
            suggestState: this.state,
            suggestParams: this.suggestParams,
            addAllProducts: onAddAll,
            toggleSuggest: toggleSuggest,
            reloadKanban: debouncedKanbanRecompute,
        });
    }

    /**
     * Removes inOrderFilter from domain key in passed context, preventing circular domain issues
     * (ie. AddAll impacts what goes in order but shouldn't be impacted by what is in order)
     * Improve: Assumes filters are always added as & in domains. (OR Domain.all would alter logic)
     * Simply removing inOrderFilter before "Add All" doesn't work due to SearchModel update trigger
     */
    _filter_add_all_ctx(ctx) {
        const domain_all = ["id", "!=", 0];
        ctx.domain = Array.from(ctx.domain, (el) =>
            el[0] === "is_in_purchase_order" && el[1] === "=" && el[2] === true ? domain_all : el
        );
        return ctx;
    }

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
            this.model.root.records = sortBySuggested(this.model.root.records);
        } else {
            for (const group of this.model.root.groups || []) {
                group.list.records = sortBySuggested(group.list.records);
            }
        }
    }

    /** On pagination change (eg. left and right arrow) */
    async onUpdatedPager() {
        this._debouncedKanbanRecompute();
    }

    /**
     * Adds the suggest parameters to context if suggest feature is activated
     * @returns {Object} base context if suggest is OFF or base + suggest context
     */
    _getSuggestContext() {
        const suggestCtx = {
            suggest_based_on: this.state.basedOn,
            suggest_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
            warehouse_id: this.suggestParams.warehouse_id,
        };
        return editSuggestContext(this._baseContext, this.state.suggestToggle.isOn, suggestCtx);
    }
}
