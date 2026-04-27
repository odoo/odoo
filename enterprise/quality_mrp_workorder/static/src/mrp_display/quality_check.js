import { patch } from "@web/core/utils/patch";
import { QualityCheck } from "@mrp_workorder/mrp_display/mrp_record_line/quality_check";

patch(QualityCheck.prototype, {

    get icon() {
        if (this.props.record.data.test_type === "spreadsheet") {
            return "fa fa-th";
        }
        return super.icon;
    },

});
