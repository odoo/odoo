import { StockForecasted } from "@stock/stock_forecasted/stock_forecasted";
import { patch } from "@web/core/utils/patch";

patch(StockForecasted.prototype, {
    getForecastedButtonsProps() {
        return {
            ...super.getForecastedButtonsProps(),
            bomIds: this.docs.bom_ids,
        };
    }
});
