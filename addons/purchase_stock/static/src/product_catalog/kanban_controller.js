import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv, useEffect } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useDebounced } from "@web/core/utils/timing";

/* Controller reacts to most UI events on product catalog view (eg. next page, filters, suggestion changes),
 * pass suggestion inputs to backend through context, and reorders kanban records based on backend computations.
 * Eg. Toggle suggest OFF -> loose suggest ctx -> product.suggested_qty set to 0 -> re-render normal catalog
 * Context passed to product.product AND purchase.order because record card is based both on
 * product.product (eg. monthly demand, forecast) and purchase.order (card highlighted, Add button) */
export class PurchaseSuggestCatalogKanbanController extends ProductCatalogKanbanController {
    setup() {
        super.setup();
        this.state = useState({
            basedOn: "",
            percentFactor: 0,
            estimatedPrice: 0.0,
            multiplier: 0,
            numberOfDays: 0,
            // bundling next constants in reactive state for code simplification (no need for reactivity)
            wizardId: null,
            warehouseId: null,
            basedOnOptions: [],
            currencySymbol: null,
            suggestToggle: this._loadSuggestToggleState(),
        });

        /* Pass context to backend and reload front-end with computed values
         * using a 300ms delay to avoid rendering entire kanban on each digit change */
        const debouncedSync = useDebounced(async () => {
            const resp = await rpc("/purchase_stock/update_purchase_suggest", {
                wizard_id: this.state.wizardId,
                vals: {
                    based_on: this.state.basedOn,
                    number_of_days: this.state.numberOfDays,
                    percent_factor: this.state.percentFactor,
                },
            });
            Object.assign(this.state, resp);
            await this._reload_grid();
        }, 300); // Enough to type eg. 110 in percent input without rendering 3 times

        onWillStart(async () => {
            this._baseContext = { ...this.model.config.context }; // For resetting when suggest is off
            const init = await rpc("/purchase_stock/init_purchase_suggest", {
                po_id: this.orderId,
                domain: this.model.config.domain,
            });
            Object.assign(this.state, init);
        });

        useEffect(
            () => {
                debouncedSync();
            },
            () => [
                this.state.basedOn,
                this.state.numberOfDays,
                this.state.percentFactor,
                this.state.suggestToggle.isOn,
            ]
        );

        const onAddAll = async () => {
            if (!this.state.wizardId) {
                throw new Error("Error on server, please retry"); // Should never happen
            }
            await this.model.orm.call("purchase.order.suggest", "action_purchase_order_suggest", [
                [this.state.wizardId],
            ]);
            this.model.root.load(); // No other way for JS to know that product.product suggest values changed
        };

        useSubEnv({
            purchaseSuggestWizard: this.state,
            addAllProducts: onAddAll,
        });
    }

    /* Reload the Kanban view to display values based on Suggest component state */
    async _reload_grid() {
        this.model.config.context = this._getCatalogContext();
        await this.model.root.load({}); // No other way for JS to know that product.product suggest values changed

        if (this.state.suggestToggle.isOn) {
            const cards = [...this.model.root.records];
            cards.sort((a, b) => (b.data.suggested_qty || 0) - (a.data.suggested_qty || 0));
            this.model.root.records = cards;
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
            warehouse_id: this.state.warehouseId,
            suggest_based_on: this.state.basedOn,
            suggest_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
            suggest_multiplier: this.state.multiplier,
        };
    }

    /**  Loads last suggest toggle state from local storage (defaults to true) */
    _loadSuggestToggleState() {
        const local_state = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle_state"));
        if (local_state?.isOn !== undefined) {
            return local_state;
        }
        return { isOn: true };
    }
}
