declare module "mock_models" {
    import { BusBus as BusBus2 } from "@bus/../tests/mock_server/mock_models/bus_bus";
    import { IrWebSocket as IrWebSocket2 } from "@bus/../tests/mock_server/mock_models/ir_websocket";

    export interface BusBus extends BusBus2 {}
    export interface IrWebSocket extends IrWebSocket2 {}

    export interface Models {
        "bus.bus": BusBus,
        "ir.websocket": IrWebSocket,
    }
}
