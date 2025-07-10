import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv, useEffect } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useDebounced } from "@web/core/utils/timing";

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
            showSuggest: 0,
            warehouse_id: null,
            suggestToggle: this._loadSuggestToggle(),
        });

        const debouncedSync = useDebounced(async () => {
            if (!this.state.wizardId) {
                return;
            }
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
                this.state.id,
                this.state.basedOn,
                this.state.numberOfDays,
                this.state.percentFactor,
                this.state.suggestToggle.isOn,
            ]
        );

        const onAddAll = async () => {
            if (!this.state.wizardId) {
                return;
            }
            await this.model.orm.call("purchase.order.suggest", "action_purchase_order_suggest", [
                [this.state.wizardId],
            ]);
            this.model.root.load(); // Shows the new product in PO on Catalog
        };

        useSubEnv({
            purchaseSuggestWizard: this.state,
            addAllProducts: onAddAll,
        });
    }

    async _reload_grid() {
        Object.assign(this.model.config.context, this._getSuggestedProductsContext());
        await this.model.root.load({
            keepSelection: true,
            reload: true,
            context: this._getSuggestedProductsContext(),
        });
        if (this.state.suggestToggle.isOn) {
            // TODO Finish undoing suggest if not on
            const recs = [...this.model.root.records];
            recs.sort((a, b) => (b.data.suggest_quantity || 0) - (a.data.suggest_quantity || 0));
            this.model.root.records = recs;
        }
        this.render(true);
    }

    _getSuggestedProductsContext() {
        let context = {};
        if (this.state.basedOn === "actual_demand") {
            const now = new Date();
            const toDate = new Date(now.getTime() + this.state.numberOfDays * 24 * 60 * 60 * 1000);
            context = {
                from_date: now.toISOString(),
                to_date: toDate.toISOString(),
            };
        } else {
            const [startDate, limitDate] = this._getPeriodOfTime();
            context = {
                monthly_demand_start_date: startDate,
                monthly_demand_limit_date: limitDate,
            };
        }

        if (this.state.warehouse_id && !this.state.hide_warehouse) {
            context.warehouse_id = this.state.warehouse_id.id;
        }

        return {
            ...context,
            suggest_based_on: this.state.basedOn,
            suggest_percent: this.state.percentFactor,
            suggest_multiplier: this.state.multiplier,
        };
    }

    _getPeriodOfTime() {
        const now = new Date();
        const start = new Date(now);
        const end = new Date(now);

        const offsets = {
            one_week: (d) => d.setDate(d.getDate() - 7),
            one_month: (d) => d.setMonth(d.getMonth() - 1),
            three_months: (d) => d.setMonth(d.getMonth() - 3),
            one_year: (d) => d.setFullYear(d.getFullYear() - 1),
        };

        if (offsets[this.state.basedOn]) {
            offsets[this.state.basedOn](start);
        } else {
            start.setFullYear(now.getFullYear() - 1, now.getMonth(), 1);
            if (this.state.basedOn === "last_year_2") {
                start.setMonth(start.getMonth() + 1); // Last year, next month
            }
            if (this.state.basedOn === "last_year_3") {
                start.setMonth(start.getMonth() + 2); // Last year, after next month
            }
            const span = this.state.basedOn === "last_year_quarter" ? 3 : 1;
            end.setTime(start.getTime());
            end.setMonth(end.getMonth() + span);
        }

        return [start.toISOString().slice(0, 19), end.toISOString().slice(0, 19)];
    }

    _loadSuggestToggle() {
        try {
            const raw = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle"));
            if (raw && typeof raw === "object" && "isOn" in raw) {
                return raw;
            }
            return { isOn: Boolean(raw) };
        } catch {
            return { isOn: true };
        }
    }
}
