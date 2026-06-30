declare module "services" {
    import { iotLongpollingService } from "@iot_base/network_utils/longpolling";

    export interface Services {
        iot_longpolling: typeof iotLongpollingService
    }
}
