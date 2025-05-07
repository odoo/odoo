declare module "services" {
    import { busParametersService } from "@bus/bus_parameters_service";
    import { multiTabService } from "@bus/multi_tab_service";
    import { outdatedPageWatcherService } from "@bus/outdated_page_watcher_service";
    import { busMonitoringservice } from "@bus/services/bus_monitoring_service";
    import { busService } from "@bus/services/bus_service";
    import { busLogsService } from "@bus/services/debug/bus_logs_service";
    import { presenceService } from "@bus/services/presence_service";

    export interface Services {
        "bus.monitoring_service": typeof busMonitoringservice,
        "bus.outdated_page_watcher": typeof outdatedPageWatcherService,
        "bus.parameters": typeof busParametersService,
        bus_service: typeof busService,
        "bus.logs_service": typeof busLogsService,
        multi_tab: typeof multiTabService,
        presence: typeof presenceService,
    }
}
