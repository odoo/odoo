/* @odoo-module */

import { assetsWatchdogService } from "@bus/services/assets_watchdog_service";
import { busParametersService } from "@bus/bus_parameters_service";
import { multiTabService } from "@bus/multi_tab_service";
import { busService } from "@bus/services/bus_service";
import { presenceService } from "@bus/services/presence_service";

import { registry } from "@web/core/registry";

export function addBusServicesToRegistry() {
    registry
        .category("services")
        .add("assetsWatchdog", assetsWatchdogService)
        .add("bus.parameters", busParametersService)
        .add("bus_service", busService)
        .add("presence", presenceService)
        .add("multi_tab", multiTabService);
}
