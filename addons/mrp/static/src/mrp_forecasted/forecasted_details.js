/** @odoo-module **/

import { ForecastedDetails } from '@stock/stock_forecasted/forecasted_details';
import { patch } from '@web/core/utils/patch';

patch(ForecastedDetails.prototype, 'mrp.ForecastedDetails',{

    canReserveOperation(line){
        return this._super(line) || line.move_out?.raw_material_production_id;
    }
});
