import { defineModels } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PosPackOperationLot } from "@pos_stock/../tests/unit/data/pos_pack_operation_lot.data";
import { StockWarehouse } from "@pos_stock/../tests/unit/data/stock_warehouse.data";
import { StockRoute } from "@pos_stock/../tests/unit/data/stock_route.data";
import { StockPickingType } from "@pos_stock/../tests/unit/data/stock_picking_type.data";

export const stockModels = [PosPackOperationLot, StockWarehouse, StockRoute, StockPickingType];
export const definePosStockModels = () => {
    const hootPosStockModels = [...hootPosModels, ...stockModels];
    const posModelNames = hootPosStockModels.map(
        (modelClass) => modelClass.prototype.constructor._name
    );
    const modelsFromMail = Object.values(mailModels).filter(
        (modelClass) => !posModelNames.includes(modelClass.prototype.constructor._name)
    );
    defineModels([...modelsFromMail, ...hootPosStockModels]);
};
