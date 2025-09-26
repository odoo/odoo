import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { useBus } from "@web/core/utils/hooks";
import { getSuggestToggleState, editSuggestContext } from "./utils";

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
            vendorName: this.props.context.vendor_name,
            warehouse_id: this.props.context.warehouse_id,
            suggestToggle: getSuggestToggleState(this.props.context.po_state),
        });

        onWillStart(async () => {
            this._baseContext = { ...this.model.config.context }; // For resetting when suggest is off
            if (this.state.suggestToggle.isOn) {
                this._kanbanReload();
            }
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
        this.model.config.context = this._editSuggestContext();
        await this.model.root.load({}); // Reload the Kanban with ctx

        if (this.state.suggestToggle.isOn) {
            this._computeTotalEstimatedPrice();
            await this._reorderKanbanGrid();
        }
    }

    async onAddAll() {
        const ctx = this._filter_add_all_ctx(this._editSuggestContext()); // IMPROVE: Quickfix
        await this.model.orm.call(
            "purchase.order",
            "action_purchase_order_suggest",
            [ctx["order_id"], ctx["domain"]],
            { context: ctx }
        );
        this._filterInTheOrder(); // Apply filter to show what was added
    }

    toggleSuggest() {
        this.state.suggestToggle.isOn = !this.state.suggestToggle.isOn;
        localStorage.setItem(
            "purchase_stock.suggest_toggle_state",
            JSON.stringify({ isOn: this.state.suggestToggle.isOn })
        );
        this._kanbanReload();
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
        this._kanbanReload();
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
        this._kanbanReload();
    }

    /**
     * Adds the suggest parameters to context if suggest feature is activated
     * @returns {Object} base context if suggest is OFF or base + suggest context
     */
    _editSuggestContext() {
        const suggestCtx = {
            domain: this.env.searchModel.domain,
            suggest_based_on: this.state.basedOn,
            suggest_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
            warehouse_id: this.state.warehouse_id,
        };
        return editSuggestContext(this._baseContext, this.state.suggestToggle.isOn, suggestCtx);
    }
}
