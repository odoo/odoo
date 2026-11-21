import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, {
    get lineContainerClasses() {
        const mainLine = this.line.deposit_main_line_id;
        if (!mainLine) {
            return super.lineContainerClasses;
        }
        return {
            ...super.lineContainerClasses,
            "border-start orderline-combo fst-italic": true,
            [mainLine.combo_parent_id ? "ms-5" : "ms-4"]: true,
        };
    },
});
