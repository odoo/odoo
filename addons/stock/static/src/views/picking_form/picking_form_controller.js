/** @odoo-module **/

import { sortBy } from "@web/core/utils/arrays";
import { FormController } from "@web/views/form/form_controller";
import { useBus, useService } from "@web/core/utils/hooks";

export class StockPickingFormController extends FormController {
    setup() {
        super.setup();
        this.action = useService("action");
        useBus(this.env.bus, "STOCK_MOVE:UPDATED", (ev) => this._qtyUpdated(ev));
        useBus(this.env.bus, "STOCK_MOVE:SAVED", (ev) => this._actionOpenShowDetails(ev));
    }

    // TRIGGER
    async _actionOpenShowDetails(ev) {
        let id = ev.detail.id;
        if (!id) {
            const moveByIdsDesc = sortBy(
                this.model.root.data.move_ids_without_package.records,
                "id",
                "desc"
            );
            const newRecord = moveByIdsDesc.find(
                (e) => e.data.product_id[0] == ev.detail.product_id[0]
            );
            id = newRecord.data.id;
        }
        const action = await this.model.orm.call("stock.move", "action_show_details", [id]);
        this.action.doAction(action, { onClose: () => this._load_and_render()});
    }

    async _load_and_render() {
        await this.model.root.load();
        this.render(true);
    }

    async _qtyUpdated(ev) {
        await this.model.root.save();
        ev.detail.resolve();
    }
}
