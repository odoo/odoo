import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { FleetActionHelper } from "@fleet/views/fleet_helper_view";

export class FleetVehicleKanbanRenderer extends KanbanRenderer {
    static template = "fleet.FleetVehicleKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        FleetActionHelper,
    };
};

export const FleetVehicleKanbanView = {
    ...kanbanView,
    Renderer: FleetVehicleKanbanRenderer,
};

registry.category("views").add("fleet_vehicle_kanban_view", FleetVehicleKanbanView);
