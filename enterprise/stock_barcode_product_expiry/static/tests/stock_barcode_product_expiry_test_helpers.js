import { mailModels } from "@mail/../tests/mail_test_helpers";
import { StockPicking } from "./mock_models/stock_picking";
import { StockPickingType } from "./mock_models/stock_picking_type";
import { StockMoveLine } from "./mock_models/stock_move_line";
import { ProductProduct } from "./mock_models/product_product";
import { UoMCategory } from "./mock_models/uom_category";
import { UoM } from "./mock_models/uom";
import { StockLocation } from "./mock_models/stock_location";
import { BarcodeRule } from "./mock_models/barcode_rule";
import { BarcodeNomenclature } from "./mock_models/barcode_nomenclature";

export const stockBarcodeProductExpiryModels = {
    ...mailModels,
    StockPicking,
    StockPickingType,
    StockMoveLine,
    ProductProduct,
    UoMCategory,
    UoM,
    StockLocation,
    BarcodeRule,
    BarcodeNomenclature,
};
