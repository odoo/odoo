import { BusPlugin } from "@bus/services/bus_plugin";
import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export class StockWarehousePlugin extends Plugin {
    setup() {
        const action = usePlugin(ActionPlugin);
        const bus = usePlugin(BusPlugin);
        const unsubscribe = bus.subscribe("stock_group_sync", () => action.doAction("reload_context"));
        onWillDestroy(unsubscribe);
    }
}
services.add(StockWarehousePlugin);
