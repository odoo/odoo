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
            wizardId: null,
            basedOnOptions: [],
            basedOn: "",
            numberOfDays: 0,
            currencySymbol: null,
            percentFactor: 0,
            multiplier: 0,
            estimatedPrice: 0.0,
            warehouseId: null,
            suggestToggle: this._loadSuggestToggleState(), // defaults to isOn = true
        });

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
        }, 300);

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
        this.model.config.context = this._getCatalogContext(this.state.suggestToggle.isOn);
        await this.model.root.load({}); // No other way for JS to know that product.product suggest values changed

        if (this.state.suggestToggle.isOn) {
            const cards = [...this.model.root.records];
            cards.sort((a, b) => (b.data.suggested_qty || 0) - (a.data.suggested_qty || 0));
            this.model.root.records = cards;
        }
    }

    _getCatalogContext(suggestIsOn = true) {
        const context = { ...this._baseContext };
        if (suggestIsOn === false) {
            return context;
        }
        if (this.state.basedOn === "actual_demand") {
            context["actual_from_date"] = toServerDt(DateTime.now());
            context["actual_to_date"] = toServerDt(
                DateTime.now().plus({ days: this.state.numberOfDays })
            );
        } else {
            const [startDate, limitDate] = this._getPeriodOfTime();
            context["monthly_demand_start_date"] = startDate;
            context["monthly_demand_limit_date"] = limitDate;
        }

        return {
            ...context,
            warehouse_id: this.state.warehouseId,
            suggest_based_on: this.state.basedOn,
            suggest_number_days: this.state.numberOfDays,
            suggest_percent: this.state.percentFactor,
            suggest_multiplier: this.state.multiplier,
        };
    }

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
