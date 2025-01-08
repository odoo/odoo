import { patch } from "@web/core/utils/patch";
import { ForecastedHeader } from "@stock/stock_forecasted/forecasted_header";
import { _t } from "@web/core/l10n/translation";

patch(ForecastedHeader.prototype, {
    get onHandLabel() {
        if (this.props.docs.use_expiration_date) {
            return _t('Fresh On Hand')
        }
        return super.onHandLabel;
    }
});
