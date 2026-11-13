import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, {
    get lineContainerClasses() {
        const classes = super.lineContainerClasses;

        if (this.line.deposit_main_line_id) {
            Object.assign(classes, {
                "border-start": true,
                "orderline-combo": true,
                "fst-italic": true,
                "ms-4": true,
            });

            if (this.line.deposit_main_line_id.combo_parent_id) {
                classes["ms-5"] = true;
                delete classes["ms-4"];
            }
        }

        return classes;
    },
});
