import { ForecastedDetails } from '@stock/stock_forecasted/forecasted_details';
import { patch } from "@web/core/utils/patch";

patch(ForecastedDetails.prototype, {

    canReserveOperation(line){
        return super.canReserveOperation(line) || line.move_out?.raw_material_production_id;
    }
});
