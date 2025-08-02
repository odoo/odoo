import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv, useEffect } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useDebounced } from "@web/core/utils/timing";

const { DateTime } = luxon; // Using luxon to freeze DT on client during tours

/* Transform client DT (which includes tz ... to server format) */
function toServerDt(dt) {
    return dt.toUTC().toFormat("yyyy-LL-dd HH:mm:ss");
}

export class PurchaseSuggestCatalogKanbanController extends ProductCatalogKanbanController {
    setup() {
        super.setup();
        this.state = useState({
            basedOn: "one_month",
            numberOfDays: 7,
            currencySymbol: null, //TODO
            percentFactor: 100,
            estimatedPrice: 0.0,
            suggestToggle: this._loadSuggestToggleState(), // defaults to isOn = true
        });

        onWillStart(async () => {
            this._baseContext = { ...this.model.config.context }; // For resetting when suggest is off
        });

        const debouncedSync = useDebounced(async () => {
            this.state.estimatedPrice = await rpc("/purchase_stock/update_purchase_suggest", {
                po_id: this.orderId,
                domain: this.model.config.domain,
                suggest_ctx: this._getCatalogContext(),
            });
            await this._reload_grid();
        }, 300);

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
            await this.model.orm.call("purchase.order", "action_purchase_order_suggest", [
                this.model.config.domain,
                this._getCatalogContext(),
            ]);
            this.model.root.load();
        };

        useSubEnv({
            suggest: this.state,
            addAllProducts: onAddAll,
        });
    }

    /* Reload the Kanban view to display values based on suggest component state
     and order the records with suggested quantities first if suggest is On */
    async _reload_grid() {
        this.model.config.context = this._getCatalogContext(this.state.suggestToggle.isOn);
        await this.model.root.load({}); // No other way for JS to know that product.product suggest values changed
        if (this.state.suggestToggle.isOn) {
            const cards = [...this.model.root.records];
            cards.sort((a, b) => (b.data.suggested_qty || 0) - (a.data.suggested_qty || 0));
            this.model.root.records = cards;
        }
    }

    /**
     * Packs the suggest parameters and calculated values in a context object
     * that can be used to calculate product.suggested_qty, purchase_order.suggest_estimated_price ...
     * @param {boolean} suggestIsOn is the suggest feature active
     * @returns {Object} context to compute Catalog Kanban (removes suggest params if suggestIsOff)
     */
    _getCatalogContext(suggestIsOn = true) {
        const context = { ...this._baseContext };
        if (suggestIsOn === false) {
            return context;
        }
        if (this.state.basedOn !== "actual_demand") {
            const [startDate, limitDate] = this._getPeriodOfTime();
            context["monthly_demand_start_date"] = startDate;
            context["monthly_demand_limit_date"] = limitDate;
        }
        return {
            ...context,
            warehouse_id: this.props.context.warehouse_id,
            suggest_based_on: this.state.basedOn,
            suggest_number_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
        };
    }

    /* Computes start and end datetime for the selected based_on option */
    _getPeriodOfTime() {
        const now = DateTime.now();
        const basedOn = this.state.basedOn;
        const toNowOptions = {
            one_week: { weeks: 1 },
            one_month: { months: 1 },
            three_months: { months: 3 },
            one_year: { years: 1 },
        };
        if (basedOn in toNowOptions) {
            const start = now.minus(toNowOptions[basedOn]);
            return [toServerDt(start), toServerDt(now)];
        }
        const spanMonths = basedOn === "last_year_quarter" ? 3 : 1;
        const offsetMonths = basedOn === "last_year_2" ? 1 : basedOn === "last_year_3" ? 2 : 0;
        const start = now.minus({ years: 1 }).startOf("month").plus({ months: offsetMonths });
        const end = start.plus({ months: spanMonths });
        return [toServerDt(start), toServerDt(end)];
    }

    _loadSuggestToggleState(default_state = true) {
        const local_state = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle_state"));
        if (local_state?.isOn !== undefined) {
            return local_state;
        }
        return { isOn: default_state };
    }
}
