import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { FleetActionHelper } from "@fleet/views/fleet_helper_view";

export class FleetVehicleListRenderer extends ListRenderer {
    static template = "fleet.FleetVehicleListRenderer";
    static components = {
        ...ListRenderer.components,
        FleetActionHelper,
    };
};

export const FleetVehicleListView = {
    ...listView,
    Renderer: FleetVehicleListRenderer,
};

registry.category("views").add("fleet_vehicle_list_view", FleetVehicleListView);
