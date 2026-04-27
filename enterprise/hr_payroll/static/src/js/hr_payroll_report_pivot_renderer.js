import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { useOpenViews } from "./hooks";

export class HrPayrollReportPivotRenderer extends PivotRenderer {
     /**
     * @override
     */
     setup() {
        super.setup();
        this.openView = useOpenViews();
    }
}
