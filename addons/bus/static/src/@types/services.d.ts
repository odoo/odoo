declare module "services" {
    import { multiTabService } from "@bus/multi_tab_service";
    import { busMonitoringservice } from "@bus/services/bus_monitoring_service";
    import { busService } from "@bus/services/bus_service";
    import { presenceService } from "@bus/services/presence_service";

    export interface Services {
        bus_service: typeof busService,
        multi_tab: typeof multiTabService,
        presence_service: typeof presenceService,
        "bus.monitoring_service": typeof busMonitoringservice,
    }
}
