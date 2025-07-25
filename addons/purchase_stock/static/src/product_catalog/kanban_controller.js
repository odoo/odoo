import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { onWillStart, useState, useSubEnv, useEffect } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";

export class PurchaseSuggestCatalogKanbanController extends ProductCatalogKanbanController {
    setup() {
        super.setup();
        const state = useState({
            basedOn: "",
            percentFactor: 0,
            estimatedPrice: 0.0,
            numberOfDays: 0,
            // bundling next constants in reactive state for code simplification (no need for reactivity)
            wizardId: null,
            basedOnOptions: [],
            currencySymbol: null,
            suggestToggle: this._loadSuggestToggleState(), // defaults to isOn = true
        });

        let debouncedSync = () => {}; // Placeholder to sync JS <> Backend

        onWillStart(async () => {
            const init = await rpc("/purchase_stock/init_purchase_suggest", {
                po_id: this.orderId,
                domain: this.model.config.domain,
            });
            Object.assign(state, init);

            debouncedSync = debounce(async () => {
                await rpc("/purchase_stock/update_purchase_suggest", {
                    wizard_id: state.wizardId,
                    vals: {
                        based_on: state.basedOn,
                        number_of_days: state.numberOfDays,
                        percent_factor: state.percentFactor,
                    },
                }).then((resp) => {
                    Object.assign(state, resp);
                });
            }, 300);
        });

        useEffect(
            () => {
                if (state.wizardId) {
                    debouncedSync(); // (Write + Read computes on Backend, then write on subEnv)
                }
            },
            () => [state.wizardId, state.basedOn, state.numberOfDays, state.percentFactor]
        );

        const onAddAll = async () => {
            if (!state.wizardId) {
                return;
            }
            await this.model.orm.call("purchase.order.suggest", "action_purchase_order_suggest", [
                [state.wizardId],
            ]);
            this.model.root.load(); // Shows the new product in PO on Catalog
        };

        useSubEnv({
            purchaseSuggestWizard: state,
            addAllProducts: onAddAll,
        }); //Expose hook state + methods to all childrens
    }

    _loadSuggestToggleState() {
        const local_state = JSON.parse(localStorage.getItem("purchase_stock.suggest_toggle_state"));
        if (local_state?.isOn !== undefined) {
            return local_state;
        }
        return { isOn: true };
    }
}
