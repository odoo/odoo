declare module "services" {
    import { busParametersService } from "@bus/bus_parameters_plugin";
    import { BusMonitoringPlugin } from "@bus/services/bus_monitoring_plugin";
    import { busService } from "@bus/services/bus_plugin";
    import { BusLogsPlugin } from "@bus/debug/bus_logs_plugin";
    import { presenceService } from "@bus/services/presence_plugin";

    export interface Services {
        "bus.monitoring_service": BusMonitoringPlugin,
        "bus.parameters": typeof busParametersService,
        bus_service: typeof busService,
        "bus.logs_service": BusLogsPlugin,
        presence: typeof presenceService,
    }
}
