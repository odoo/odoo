declare module "services" {
    import { busParametersService } from "@bus/bus_parameters_plugin";
    import { BusMonitoringPlugin } from "@bus/services/bus_monitoring_plugin";
    import { busService } from "@bus/services/bus_plugin";
    import { busLogsService } from "@bus/services/debug/bus_logs_service";
    import { presenceService } from "@bus/services/presence_plugin";

    export interface Services {
        "bus.monitoring_service": BusMonitoringPlugin,
        "bus.parameters": typeof busParametersService,
        bus_service: typeof busService,
        "bus.logs_service": typeof busLogsService,
        presence: typeof presenceService,
    }
}
