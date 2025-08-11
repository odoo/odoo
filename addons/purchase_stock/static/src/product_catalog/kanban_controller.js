import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv, useEffect } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useDebounced } from "@web/core/utils/timing";
import { useBus } from "@web/core/utils/hooks";

/* Controller reacts to most UI events on product catalog view (eg. next page, filters, suggestion changes),
 * pass suggestion inputs to backend through context, and reorders kanban records based on backend computations.
 * Eg. Toggle suggest OFF -> loose suggest ctx -> product.suggested_qty set to 0 -> re-render normal catalog
 * Context passed to product.product AND purchase.order because record card is based both on
 * product.product (eg. monthly demand, forecast) and purchase.order (card highlighted, Add button) */
export class PurchaseSuggestCatalogKanbanController extends ProductCatalogKanbanController {
    setup() {
        super.setup();
        this.state = useState({
            numberOfDays: this.props.context.vendor_suggest_days,
            basedOn: this.props.context.vendor_suggest_based_on,
            percentFactor: this.props.context.vendo_suggest_percent,
            poState: this.props.context.po_state,
            estimatedPrice: 0.0,
            currencyId: this.props.context.product_catalog_currency_id,
            digits: this.props.context.product_catalog_digits,
            vendorName: this.props.context.vendor_name,
            suggestToggle: this._loadSuggestToggleState(),
        });

        onWillStart(async () => {
            this._baseContext = { ...this.model.config.context }; // For resetting when suggest is off
        });

        /* Pass context to backend and reload front-end with computed values
         * using a 300ms delay to avoid rendering entire kanban on each digit change */
        this._debouncedKanbanRecompute = useDebounced(async () => {
            this.model.config.context = this._getCatalogContext();
            await this.model.root.load({}); // Reload the Kanban with ctx

            if (this.state.suggestToggle.isOn) {
                this.state.estimatedPrice = await rpc("/purchase_stock/update_purchase_suggest", {
                    po_id: this.orderId,
                    domain: this.model.config.domain,
                    suggest_ctx: this._getCatalogContext(),
                });
                await this._reorderKanbanGrid();
            }
        }, 300); // Enough to type eg. 110 in percent input without rendering 3 times

        useEffect(
            () => {
                this._debouncedKanbanRecompute();
            },
            () => [
                this.state.basedOn,
                this.state.numberOfDays,
                this.state.percentFactor,
                this.state.suggestToggle.isOn,
            ]
        );

        /* Recompute Kanban on filter changes (incl. sidebar category filters)
         * The "update" triggers a refresh, which can happen before debounce on slow
         * internet --> pass suggest context to searchModel in case it refreshes first */
        useBus(this.env.searchModel, "update", () => {
            this.env.searchModel.globalContext = this._getCatalogContext(); // Check with slow internet before removing
            this._debouncedKanbanRecompute();
        });

        // FIX me: Bug if Add all, then remove one by one product, then add all again
        const onAddAll = async () => {
            await this.model.orm.call("purchase.order", "action_purchase_order_suggest", [
                this.model.config.domain,
                this._getCatalogContext(),
            ]);
            this._filterInTheOrder(); // Apply filter to show what was added
        };

        useSubEnv({
            suggest: this.state,
            addAllProducts: onAddAll,
        });
    }

    /* Moves records with suggested_qty > 0 to the front, keeping original order.
     * Doesn't work with paging (because suggested_qty is computed on backed) */
    async _reorderKanbanGrid() {
        const sortBySuggested = (list) => {
            const suggest_products = list.filter((record) => record.data.suggested_qty > 0);
            const not_suggested_products = list.filter((record) => record.data.suggested_qty == 0);
            return [...suggest_products, ...not_suggested_products];
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
        if (
            inTheOrderFilter &&
            sm.query.findIndex((el) => el.searchItemId === inTheOrderFilter.id) === -1
        ) {
            sm.toggleSearchItem(inTheOrderFilter.id);
        } else {
            this.model.load();
        }
    }

    /**
     * Packs the suggest parameters in a object to pass to backend
     * (product & purchase_order models). Returns base context if suggest is OFF.
     * @returns {Object} base context or base + suggest context
     */
    _getCatalogContext() {
        const ctx = { ...this._baseContext };
        if (this.state.suggestToggle.isOn === false) {
            return ctx; // removes suggest context
        }
        return {
            ...ctx,
            warehouse_id: this.props.context.warehouse_id,
            suggest_based_on: this.state.basedOn,
            suggest_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
        };
    }

    /**  Loads last suggest toggle state from local storage (defaults to true) */
    _loadSuggestToggleState() {
        if (this.props.context.po_state !== "draft") {
            return { isOn: false };
        }
        const local_state = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle_state"));
        if (local_state?.isOn !== undefined) {
            return local_state;
        }
        return { isOn: true };
    }
}
