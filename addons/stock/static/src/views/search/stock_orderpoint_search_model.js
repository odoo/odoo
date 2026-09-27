import { useService } from "@web/core/utils/hooks";
import { SearchModel } from "@web/search/search_model";
import { debounce } from "@web/core/utils/timing";


export class StockOrderpointSearchModel extends SearchModel {
    static DEBOUNCE_DELAY = 500;

    setup(services) {
        super.setup(services);
        this.ui = useService("ui");
        this.applyGlobalHorizonDays = debounce(
            this.applyGlobalHorizonDays.bind(this),
            StockOrderpointSearchModel.DEBOUNCE_DELAY
        );
    }

    async applyGlobalHorizonDays(globalHorizonDays) {
        this.ui.block();
        this.globalContext = {
            ...this.globalContext,
            global_horizon_days: globalHorizonDays,
        };
        this._context = false; // Force rebuild of this.context to take into account the updated this.globalContext
        await this.orm.call("stock.warehouse.orderpoint", "action_open_orderpoints", [], {
            context: {
                ...this.context,
                force_orderpoint_recompute: true,
            }
        });
        await this._fetchSections(this.categories, this.filters);
        this._notify();
        this.ui.unblock();
    }
}
