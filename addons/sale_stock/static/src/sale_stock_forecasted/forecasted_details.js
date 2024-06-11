/** @odoo-module **/
import { formatMonetary } from "@web/views/fields/formatters";
import { patch } from "@web/core/utils/patch";

import { ForecastedDetails } from "@stock/stock_forecasted/forecasted_details";

patch(ForecastedDetails.prototype, {
    _formatMonetary(num, currencyId){
        return formatMonetary(num,{ currencyId: currencyId});
    }
});
