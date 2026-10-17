import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, {
    get lineContainerClasses() {
        const classes = super.lineContainerClasses;
        if (this.line._mainLine?.combo_parent_id) {
            classes["border-start"] = true;
            classes["orderline-combo fst-italic ms-4"] = true;
        }
        return classes;
    },
});
