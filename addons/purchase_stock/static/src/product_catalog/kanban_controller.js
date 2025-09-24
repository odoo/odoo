import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
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
            poState: this.props.context.po_state,
            totalEstimatedPrice: 0.0,
            currencyId: this.props.context.product_catalog_currency_id,
            digits: this.props.context.product_catalog_digits,
            vendorName: this.props.context.vendor_name,
            suggestToggle: this._loadSuggestToggleState(),
        });

        onWillStart(async () => {
            this._baseContext = { ...this.model.config.context }; // For resetting when suggest is off
            if (this.state.suggestToggle.isOn) {
                this._debouncedKanbanRecompute();
            }
        });

        /* Pass context to backend and reload front-end with computed values
         * using a 300ms delay to avoid rendering entire kanban on each digit change */
        this._debouncedKanbanRecompute = useDebounced(async () => {
            this.model.config.context = this._getCatalogContext();
            await this.model.root.load({}); // Reload the Kanban with ctx

            if (this.state.suggestToggle.isOn) {
                const product_prices = await this.orm.searchRead(
                    "product.product",
                    this.model.config.domain,
                    ["suggest_estimated_price"],
                    { context: this._getCatalogContext() }
                );
                this.state.totalEstimatedPrice = product_prices.reduce(
                    (sum, p) => sum + Number(p.suggest_estimated_price || 0),
                    0
                );
                await this._reorderKanbanGrid();
            }
        }, 300); // Enough to type eg. 110 in percent input without rendering 3 times

        /* Recompute Kanban on filter changes (incl. sidebar category filters)
         * The "update" triggers a refresh, which can happen before debounce on slow
         * internet --> pass suggest context to searchModel in case it refreshes first */
        useBus(this.env.searchModel, "update", () => {
            this.env.searchModel.globalContext = this._getCatalogContext(); // Check with slow internet before removing
            this._debouncedKanbanRecompute();
        });

        const onAddAll = async () => {
            const ctx = this._filter_add_all_ctx(this._getCatalogContext()); // IMPROVE: Quickfix
            await this.model.orm.call(
                "purchase.order",
                "action_purchase_order_suggest",
                [ctx["order_id"]],
                { context: ctx }
            );
            this._filterInTheOrder(); // Apply filter to show what was added
        };

        useSubEnv({
            suggest: this.state,
            addAllProducts: onAddAll,
            debouncedKanbanRecompute: this._debouncedKanbanRecompute,
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

    /** Add "In the Order" filter, returning products in PO, if it wasn't already there. */
    _filterInTheOrder() {
        const sm = this.env.searchModel;
        const inTheOrderFilter = Object.values(sm.searchItems).find(
            (searchItem) => searchItem.name === "products_in_purchase_order"
        );
        const isActive = sm.query.some((f) => f.searchItemId === inTheOrderFilter.id);
        sm.toggleSearchItem(inTheOrderFilter.id);
        if (isActive) {
            sm.toggleSearchItem(inTheOrderFilter.id); // Reapply with new updated values
        }
    }

    /**
     * Packs the suggest parameters in a object to pass to backend
     * (product & purchase_order models). Returns base context if suggest is OFF.
     * @returns {Object} base context or base + suggest context
     */
    _getCatalogContext() {
        if (this.state.suggestToggle.isOn === false) {
            return this._baseContext; // removes suggest context
        }
        return {
            ...this._baseContext,
            domain: this.model.config.domain,
            warehouse_id: this.props.context.warehouse_id,
            suggest_based_on: this.state.basedOn,
            suggest_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
        };
    }

    /** Loads last suggest toggle state from local storage (defaults to false) */
    _loadSuggestToggleState() {
        if (this.props.context.po_state !== "draft") {
            return { isOn: false };
        }
        const local_state = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle_state"));
        if (local_state?.isOn !== undefined) {
            return local_state;
        }
        return { isOn: false };
    }
}
