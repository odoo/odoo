import { patch } from "@web/core/utils/patch";
import { ForecastedDetails } from "@stock/stock_forecasted/forecasted_details";
import { _t } from "@web/core/l10n/translation";

patch(ForecastedDetails.prototype, {
    get freeStockLabel() {
        if (this.props.docs.use_expiration_date) {
            return _t('Fresh Free Stock');
        }
        return super.freeStockLabel;
    }
});
