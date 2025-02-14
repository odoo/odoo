import { patch } from "@web/core/utils/patch";
import { QtyAtDatePopover } from "@sale_stock/widgets/qty_at_date_widget";
import { _t } from "@web/core/l10n/translation";

patch(QtyAtDatePopover.prototype, {
    get forecastedLabel() {
        if (this.props.record.data.use_expiration_date) {
            return _t('Fresh Forecasted Stock')
        }
        return super.forecastedLabel;
    },
    get availableLabel() {
        if (this.props.record.data.use_expiration_date) {
            return _t('Fresh Available')
        }
        return super.availableLabel;
    }
});
