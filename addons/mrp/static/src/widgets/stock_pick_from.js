import { patch } from "@web/core/utils/patch";
import { StockPickFrom } from "@stock/widgets/stock_pick_from";

patch(StockPickFrom.prototype, {
    get lotDisplayName() {
        return super.lotDisplayName || this.props.record.data.visual_lot_name;
    },
});
