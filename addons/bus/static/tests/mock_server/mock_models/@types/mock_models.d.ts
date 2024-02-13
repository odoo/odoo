declare module "mock_models" {
    import { BusBus as BusBus2 } from "@bus/../tests/mock_server/mock_models/bus_bus";

    export interface BusBus extends BusBus2 {}

    export interface Models {
        "bus.bus": BusBus2,
    }
}